from dataclasses import dataclass, field

import structlog

from nlp.date_normalizer import classify_dates, extract_dates
from nlp.entity_extractor import ExtractedEntities, extract_entities
from nlp.entity_resolver import EntityResolver
from nlp.penalty_extractor import extract_penalties
from nlp.validators import (
    compute_overall_confidence,
    route_extraction,
    validate_extraction,
)
from nlp.violation_classifier import (
    classify_violation,
    determine_severity,
    get_domain_and_subtype,
)
from processors.language_detector import detect_language

logger = structlog.get_logger(__name__)

# Lazy-loaded resolver (expensive to initialize)
_resolver: EntityResolver | None = None


def _get_resolver() -> EntityResolver:
    global _resolver
    if _resolver is None:
        _resolver = EntityResolver()
    return _resolver


@dataclass
class PipelineResult:
    """Full result of NLP pipeline processing."""

    # Language
    language: str = "en"
    language_confidence: float = 0.0

    # Entities
    entities: ExtractedEntities = field(default_factory=ExtractedEntities)
    resolved_entity: dict | None = None  # CIN resolution result

    # Penalties
    penalties: list[dict] = field(default_factory=list)
    primary_penalty_inr: float | None = None

    # Dates
    dates: list[dict] = field(default_factory=list)
    order_date: str | None = None
    violation_date: str | None = None

    # Classification
    violation_predictions: list[dict] = field(default_factory=list)
    violation_category: str | None = None
    violation_subtype: str | None = None
    severity: str = "LOW"

    # Summary
    summary: str = ""

    # Confidence
    overall_confidence: float = 0.0
    review_status: str = "pending_review"

    # Raw data for validation
    validation_results: list = field(default_factory=list)


def process_document(text: str, regulator_code: str = "RBI") -> PipelineResult:
    """Run the full NLP pipeline on extracted document text.

    Pipeline stages:
        1. Language detection
        2. Entity extraction (regex + NER)
        3. Penalty amount extraction
        4. Date extraction and classification
        5. Violation type classification
        6. Entity resolution (fuzzy match against MCA)
        7. Confidence scoring
        8. Validation and routing

    Args:
        text: Extracted text from PDF/HTML document
        regulator_code: Source regulator code for context

    Returns:
        PipelineResult with all extractions and confidence scores
    """
    result = PipelineResult()

    if not text or len(text.strip()) < 50:
        logger.warning("text_too_short", length=len(text) if text else 0)
        result.review_status = "rejected"
        return result

    # 1. Language detection
    result.language, result.language_confidence = detect_language(text)
    logger.info("pipeline_stage", stage="language", lang=result.language)

    # 2. Entity extraction
    result.entities = extract_entities(text, lang=result.language)
    logger.info("pipeline_stage", stage="entities")

    # 3. Penalty extraction
    result.penalties = extract_penalties(text)
    if result.penalties:
        result.primary_penalty_inr = result.penalties[0]["amount_inr"]
    logger.info("pipeline_stage", stage="penalties")

    # 4. Date extraction
    result.dates = extract_dates(text)
    date_classification = classify_dates(text, result.dates)
    result.order_date = date_classification["order_date"]
    result.violation_date = date_classification["violation_date"]
    logger.info("pipeline_stage", stage="dates")

    # 5. Violation classification
    result.violation_predictions = classify_violation(text)
    if result.violation_predictions:
        top = result.violation_predictions[0]
        domain, subtype = get_domain_and_subtype(top["violation_type"])
        result.violation_category = domain
        result.violation_subtype = subtype
    logger.info("pipeline_stage", stage="classification")

    # 6. Severity determination
    if result.violation_predictions:
        result.severity = determine_severity(
            result.violation_predictions[0]["violation_type"],
            result.primary_penalty_inr,
        )

    # 7. Entity resolution (try CIN first, then company name)
    resolver = _get_resolver()
    if result.entities.cin_numbers:
        for cin in result.entities.cin_numbers:
            resolved = resolver.resolve_cin(cin)
            if resolved:
                result.resolved_entity = resolved
                break

    if not result.resolved_entity and result.entities.companies:
        for company in result.entities.companies:
            resolved = resolver.resolve(company["name"])
            if resolved:
                result.resolved_entity = resolved
                break
    logger.info("pipeline_stage", stage="entity_resolution")

    # 8. Generate summary
    result.summary = _generate_summary(result, regulator_code)

    # 9. Confidence scoring
    entity_conf = max(
        (c.get("confidence", 0) for c in result.entities.companies),
        default=0.0,
    )
    cin_conf = result.resolved_entity["confidence"] if result.resolved_entity else 0.0
    violation_conf = (
        result.violation_predictions[0]["confidence"]
        if result.violation_predictions
        else 0.0
    )
    penalty_conf = result.penalties[0]["confidence"] if result.penalties else 0.0
    date_conf = 0.9 if result.order_date else 0.0

    result.overall_confidence = compute_overall_confidence(
        entity_confidence=entity_conf,
        cin_confidence=cin_conf,
        violation_confidence=violation_conf,
        penalty_confidence=penalty_conf,
        date_confidence=date_conf,
    )

    # 10. Validation
    extraction_data = {
        "companies": [{"name": c["name"]} for c in result.entities.companies],
        "cin_numbers": result.entities.cin_numbers,
        "individuals": result.entities.individuals,
        "penalties": result.penalties,
        "dates": result.dates,
    }
    result.validation_results = validate_extraction(extraction_data)

    # Check if any validation failed
    has_failure = any(not v.is_valid for v in result.validation_results)
    if has_failure:
        result.overall_confidence = min(result.overall_confidence, 0.7)

    # 11. Route
    result.review_status = route_extraction(result.overall_confidence)

    logger.info(
        "pipeline_complete",
        confidence=round(result.overall_confidence, 4),
        review_status=result.review_status,
        entity_count=len(result.entities.companies),
        penalty_count=len(result.penalties),
        violation=result.violation_category,
    )

    return result


def _generate_summary(result: PipelineResult, regulator_code: str) -> str:
    """Generate a factual one-line summary of the enforcement action."""
    parts = []

    # Regulator
    parts.append(regulator_code)

    # Action
    parts.append("imposed a penalty")

    # Amount
    if result.primary_penalty_inr:
        amount = result.primary_penalty_inr
        if amount >= 10_000_000:
            parts.append(f"of INR {amount / 10_000_000:.2f} crore")
        elif amount >= 100_000:
            parts.append(f"of INR {amount / 100_000:.2f} lakh")
        else:
            parts.append(f"of INR {amount:,.0f}")

    # Entity
    if result.entities.companies:
        parts.append(f"on {result.entities.companies[0]['name']}")

    # Violation
    if result.violation_predictions:
        parts.append(f"for {result.violation_predictions[0]['description']}")

    # Date
    if result.order_date:
        parts.append(f"(order dated {result.order_date})")

    return " ".join(parts) + "."
