# scrapperboi

Regulatory Problem Intelligence Engine for India.

## What it does

scrapperboi scrapes public enforcement data from Indian regulators (RBI, SEBI, CCI, etc.), extracts structured intelligence using NLP, and serves it via a searchable API and dashboard.

**Turn penalty orders into actionable compliance intelligence.**

## Architecture

```
[Gov Sites] --> [Scraper Fleet] --> [Raw Store (MinIO)]
                                        |
                                  [PDF/OCR Processor]
                                        |
                                  [NLP Pipeline]
                                  (entity extraction, penalty parsing,
                                   violation classification, entity resolution)
                                        |
                                  [PostgreSQL + Meilisearch]
                                        |
                                  [FastAPI REST API]
```

## Quick Start

```bash
# Clone and setup
cp .env.example .env
docker-compose up -d

# Run migrations
alembic upgrade head

# Start the API
uvicorn api.main:app --reload

# Trigger a scrape
celery -A workers.celery_app worker -l info
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/violations` | List violations with filters (regulator, entity, date, type, severity) |
| `GET /api/v1/violations/{id}` | Full violation details |
| `GET /api/v1/entities/{id}` | Entity profile with all violations |
| `GET /api/v1/entities/{id}/timeline` | Chronological violation timeline |
| `GET /api/v1/search?q=...` | Full-text search (typo-tolerant) |
| `GET /api/v1/stats/regulators` | Aggregate stats by regulator |
| `GET /api/v1/recidivists` | Repeat offenders |

## Tech Stack

- **Python 3.11+** with FastAPI, Celery, SQLAlchemy 2.0
- **PostgreSQL 16** with pg_trgm for fuzzy search
- **Meilisearch** for typo-tolerant full-text search
- **PyMuPDF + Tesseract** for PDF text extraction and OCR
- **spaCy + HuggingFace** for NLP (entity extraction, classification)
- **MinIO** for raw document storage
- **Docker Compose** for local development

## Documentation

- [BLUEPRINT.md](docs/BLUEPRINT.md) -- Full strategic + technical blueprint
- [ROADMAP.md](docs/ROADMAP.md) -- 30-60-90 day execution plan

## License

MIT
