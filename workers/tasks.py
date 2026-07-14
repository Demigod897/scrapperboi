import asyncio
from datetime import datetime

import structlog
import yaml

from workers.celery_app import app

logger = structlog.get_logger(__name__)


def _load_regulator_config(regulator_code: str) -> dict:
    """Load regulator config from sources.yaml."""
    with open("config/sources.yaml") as f:
        config = yaml.safe_load(f)
    regulators = config.get("regulators", {})
    reg_config = regulators.get(regulator_code.lower())
    if not reg_config:
        raise ValueError(f"Unknown regulator: {regulator_code}")
    return reg_config


def _get_scraper(regulator_code: str, config: dict):
    """Instantiate the correct scraper for a regulator."""
    scrapers = {
        "rbi": "scrapers.rbi.RBIPenaltyOrderScraper",
        # "sebi": "scrapers.sebi.SEBIScraper",  # Phase 2
    }

    scraper_path = scrapers.get(regulator_code.lower())
    if not scraper_path:
        raise ValueError(f"No scraper implemented for: {regulator_code}")

    module_path, class_name = scraper_path.rsplit(".", 1)
    import importlib

    module = importlib.import_module(module_path)
    scraper_class = getattr(module, class_name)
    return scraper_class(config)


@app.task(bind=True, max_retries=2, default_retry_delay=300)
def run_scraper(self, regulator_code: str):
    """Run the full scrape + process pipeline for a regulator.

    Steps:
        1. Scrape documents from regulator website
        2. Deduplicate against existing documents (by content hash)
        3. Store raw documents in MinIO
        4. Process through NLP pipeline
        5. Write results to PostgreSQL
        6. Index in Meilisearch
    """
    logger.info("scraper_task_started", regulator=regulator_code, task_id=self.request.id)

    try:
        config = _load_regulator_config(regulator_code)
        if not config.get("enabled", False):
            logger.info("scraper_disabled", regulator=regulator_code)
            return {"status": "skipped", "reason": "disabled"}

        # Run async scraper in sync Celery context
        result = asyncio.run(
            _scrape_and_process(regulator_code, config)
        )

        logger.info("scraper_task_complete", regulator=regulator_code, **result)
        return result

    except Exception as e:
        logger.error("scraper_task_failed", regulator=regulator_code, error=str(e))
        raise self.retry(exc=e)


async def _scrape_and_process(regulator_code: str, config: dict) -> dict:
    """Async scrape and process pipeline."""
    from storage.db import (
        Document,
        Entity,
        Penalty,
        Regulator,
        ScrapeRun,
        SyncSessionLocal,
        Violation,
    )
    from storage.raw_store import store_raw_document
    from storage.search import index_violation
    from processors.pdf_processor import PDFProcessor
    from nlp.pipeline import process_document

    scraper = _get_scraper(regulator_code, config)
    pdf_processor = PDFProcessor()

    # Track scrape run
    session = SyncSessionLocal()
    try:
        # Get or create regulator record
        regulator = session.query(Regulator).filter_by(code=regulator_code.upper()).first()
        if not regulator:
            regulator = Regulator(
                code=regulator_code.upper(),
                full_name=config.get("full_name", regulator_code),
                website_url=config.get("base_url", ""),
            )
            session.add(regulator)
            session.commit()

        scrape_run = ScrapeRun(
            regulator_id=regulator.id,
            started_at=datetime.utcnow(),
            status="running",
        )
        session.add(scrape_run)
        session.commit()

        # Scrape
        scraped_docs = await scraper.scrape()
        scrape_run.documents_found = len(scraped_docs)

        documents_new = 0
        documents_failed = 0

        for scraped_doc in scraped_docs:
            try:
                # Check for duplicate
                existing = (
                    session.query(Document)
                    .filter_by(content_hash=scraped_doc.content_hash)
                    .first()
                )
                if existing:
                    continue

                # Store raw document
                content_type = (
                    "application/pdf"
                    if scraped_doc.document_type.value == "pdf"
                    else "text/html"
                )
                storage_key = store_raw_document(
                    scraped_doc.content_hash,
                    scraped_doc.raw_content,
                    content_type,
                )

                # Extract text
                if scraped_doc.document_type.value == "pdf":
                    extraction = pdf_processor.process(scraped_doc.raw_content)
                else:
                    extraction = pdf_processor.process_html(
                        scraped_doc.raw_content.decode("utf-8", errors="replace")
                    )

                # Create document record
                doc = Document(
                    source_url=scraped_doc.source_url,
                    content_hash=scraped_doc.content_hash,
                    regulator_id=regulator.id,
                    document_type=scraped_doc.document_type.value.upper(),
                    title=scraped_doc.title,
                    raw_storage_key=storage_key,
                    extracted_text=extraction["full_text"],
                    extraction_method=extraction["extraction_method"],
                    page_count=extraction["page_count"],
                    scraped_at=scraped_doc.scraped_at,
                    processed_at=datetime.utcnow(),
                    processing_status="processing",
                )
                session.add(doc)
                session.flush()  # Get doc.id

                # Run NLP pipeline
                pipeline_result = process_document(
                    extraction["full_text"],
                    regulator_code=regulator_code.upper(),
                )

                # Create or find entity
                entity = None
                if pipeline_result.entities.companies:
                    company_name = pipeline_result.entities.companies[0]["name"]
                    cin = None
                    if pipeline_result.resolved_entity:
                        cin = pipeline_result.resolved_entity["cin"]
                    elif pipeline_result.entities.cin_numbers:
                        cin = pipeline_result.entities.cin_numbers[0]

                    # Try to find existing entity
                    if cin:
                        entity = session.query(Entity).filter_by(cin=cin).first()
                    if not entity:
                        entity = (
                            session.query(Entity)
                            .filter(Entity.entity_name.ilike(company_name))
                            .first()
                        )
                    if not entity:
                        entity = Entity(
                            entity_type="NBFC" if regulator_code.upper() == "RBI" else "COMPANY",
                            entity_name=company_name,
                            cin=cin,
                        )
                        session.add(entity)
                        session.flush()

                # Create violation
                violation = Violation(
                    document_id=doc.id,
                    regulator_id=regulator.id,
                    entity_id=entity.id if entity else None,
                    order_date=pipeline_result.order_date,
                    violation_date=pipeline_result.violation_date,
                    summary=pipeline_result.summary,
                    raw_excerpt=extraction["full_text"][:1000],
                    violation_category=pipeline_result.violation_category,
                    violation_subtype=pipeline_result.violation_subtype,
                    severity=pipeline_result.severity,
                    extraction_confidence=pipeline_result.overall_confidence,
                    review_status=pipeline_result.review_status,
                )
                session.add(violation)
                session.flush()

                # Create penalties
                for pen in pipeline_result.penalties:
                    penalty = Penalty(
                        violation_id=violation.id,
                        penalty_type="MONETARY",
                        amount_inr=pen["amount_inr"],
                        amount_raw_text=pen["raw_text"],
                    )
                    session.add(penalty)

                # Update document status
                doc.processing_status = "completed"

                # Index in Meilisearch
                try:
                    index_violation({
                        "id": violation.id,
                        "entity_name": entity.entity_name if entity else "",
                        "cin": entity.cin if entity else None,
                        "regulator_code": regulator_code.upper(),
                        "violation_category": pipeline_result.violation_category,
                        "violation_subtype": pipeline_result.violation_subtype,
                        "severity": pipeline_result.severity,
                        "summary": pipeline_result.summary,
                        "raw_excerpt": extraction["full_text"][:500],
                        "order_date": pipeline_result.order_date,
                        "penalty_amount_inr": pipeline_result.primary_penalty_inr or 0,
                        "entity_type": entity.entity_type if entity else None,
                        "review_status": pipeline_result.review_status,
                        "created_at": datetime.utcnow().isoformat(),
                    })
                except Exception as e:
                    logger.warning("search_index_failed", violation_id=violation.id, error=str(e))

                documents_new += 1
                session.commit()

            except Exception as e:
                logger.error(
                    "document_processing_failed",
                    url=scraped_doc.source_url,
                    error=str(e),
                )
                documents_failed += 1
                session.rollback()

        # Update scrape run
        scrape_run.completed_at = datetime.utcnow()
        scrape_run.status = "completed"
        scrape_run.documents_new = documents_new
        scrape_run.documents_failed = documents_failed
        session.commit()

        return {
            "status": "completed",
            "documents_found": len(scraped_docs),
            "documents_new": documents_new,
            "documents_failed": documents_failed,
        }

    except Exception as e:
        scrape_run.status = "failed"
        scrape_run.error_message = str(e)
        scrape_run.completed_at = datetime.utcnow()
        session.commit()
        raise
    finally:
        session.close()


@app.task
def process_single_document(document_id: int):
    """Re-process a single document through the NLP pipeline.

    Useful for reprocessing after NLP improvements.
    """
    from storage.db import Document, SyncSessionLocal
    from processors.pdf_processor import PDFProcessor
    from storage.raw_store import get_raw_document
    from nlp.pipeline import process_document

    session = SyncSessionLocal()
    try:
        doc = session.query(Document).get(document_id)
        if not doc:
            logger.error("document_not_found", document_id=document_id)
            return

        # Re-extract text from raw document
        raw_content = get_raw_document(doc.raw_storage_key)
        pdf_processor = PDFProcessor()

        if doc.document_type == "PDF":
            extraction = pdf_processor.process(raw_content)
        else:
            extraction = pdf_processor.process_html(raw_content.decode("utf-8", errors="replace"))

        # Re-run NLP pipeline
        result = process_document(extraction["full_text"])

        # Update document
        doc.extracted_text = extraction["full_text"]
        doc.extraction_method = extraction["extraction_method"]
        doc.processed_at = datetime.utcnow()
        doc.processing_status = "completed"

        session.commit()
        logger.info("document_reprocessed", document_id=document_id)

    finally:
        session.close()
