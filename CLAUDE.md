# scrapperboi

Scrapes RBI penalty orders, extracts structured data via NLP, serves via REST API. Indian regulatory intelligence for compliance officers, lenders, law firms.

## Stack

`RBI Website → httpx Scraper → MinIO → PyMuPDF/OCR → NLP Pipeline → PostgreSQL + Meilisearch → FastAPI`

7 Docker services: PostgreSQL 16, Redis 7, Meilisearch 1.6, MinIO, FastAPI, Celery Worker, Celery Beat (daily 6 AM IST).

## Structure

```
config/       settings.py, sources.yaml
scrapers/     base.py (ABC), rbi.py (ASP.NET VIEWSTATE pagination)
processors/   pdf_processor.py, ocr.py (Tesseract→Google Vision), language_detector.py
nlp/          entity_extractor, penalty_extractor, date_normalizer, violation_classifier, entity_resolver, validators, pipeline
storage/      db.py (11 SQLAlchemy models), search.py (Meilisearch), raw_store.py (MinIO)
api/          main.py, routers/ (violations, entities, search, stats)
workers/      celery_app.py, tasks.py
docs/         BLUEPRINT, ROADMAP, HOW_IT_WORKS, FUTURE_SCOPE, RUNNING
tests/        empty
```

## Run

```bash
cp .env.example .env && docker compose up -d
docker compose exec api alembic revision --autogenerate -m "initial"
docker compose exec api alembic upgrade head
curl -X POST http://localhost:8000/api/v1/scrape/rbi
```

## .env

Uses Docker service names: `db`, `redis`, `meilisearch`, `minio` — NOT `localhost`.

## Conventions

- FastAPI async + AsyncSession; Celery sync + `asyncio.run()` for scrapers
- structlog for logging, Pydantic BaseSettings for config
- New scrapers: inherit `AbstractBaseScraper`, implement `discover_documents()` + `parse_listing_page()`
- NLP modules return dataclass/dict, `pipeline.py` orchestrates

## Not Yet Built

- Tests, review queue API, SEBI/CCI/IRDAI scrapers (Phase 2), MCA data loader, auth, dashboard UI
- CORS is `*`, no pre-built Alembic migrations, fasttext model downloaded in Docker build only
