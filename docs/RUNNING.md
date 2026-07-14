# Running scrapperboi

Step-by-step guide to get from zero to seeing scraped data.

---

## Prerequisites

- **Docker** (v24+) and **Docker Compose** plugin installed
- Your user added to the `docker` group (`sudo usermod -aG docker $USER`, then log out/in)
- ~4GB free disk space for Docker images
- ~16GB RAM recommended (can work with 8GB for testing)

---

## Step 1: Start Infrastructure (2-5 minutes first time)

```bash
cd /home/k-saikumar/Documents/scrapperboi

# Create .env from example if you haven't
cp .env.example .env

# Pull images and start all 7 services
docker compose up -d
```

**What happens:**
- Docker downloads images: PostgreSQL 16, Redis 7, Meilisearch 1.6, MinIO, Python 3.11
- Builds your app image (installs Tesseract OCR, spaCy, fasttext model, all Python deps)
- Starts all services with health checks

**First run takes 5-10 minutes** (downloading images + building). Subsequent runs take seconds.

**What to expect:**
```
[+] Running 7/7
 ✔ Container scrapperboi-db-1          Healthy
 ✔ Container scrapperboi-redis-1       Healthy
 ✔ Container scrapperboi-meilisearch-1 Started
 ✔ Container scrapperboi-minio-1       Started
 ✔ Container scrapperboi-api-1         Started
 ✔ Container scrapperboi-worker-1      Started
 ✔ Container scrapperboi-beat-1        Started
```

**Verify services are running:**
```bash
docker compose ps
```

All 7 services should show `Up` or `Healthy`.

---

## Step 2: Create Database Tables (30 seconds)

```bash
# Run inside the API container
docker compose exec api alembic revision --autogenerate -m "initial schema"
docker compose exec api alembic upgrade head
```

**What happens:**
- Alembic reads all 11 SQLAlchemy models from `storage/db.py`
- Generates a migration file with CREATE TABLE statements
- Applies it to PostgreSQL, creating: regulators, documents, entities, violations, penalties, violation_types, mca_company_master, entity_resolution_log, review_queue, scrape_runs, violation_entities

**What to expect:**
```
INFO  [alembic.runtime.migration] Running upgrade  -> abc123, initial schema
```

---

## Step 3: Trigger a Scrape

### Option A: Via API (easiest)
```bash
curl -X POST http://localhost:8000/api/v1/scrape/rbi
```

**Response:**
```json
{
    "status": "queued",
    "task_id": "abc123-...",
    "regulator": "rbi",
    "message": "Scrape for RBI has been queued. Check /api/v1/stats/scrape-runs for progress."
}
```

### Option B: Via Python
```bash
docker compose exec worker python -c "from workers.tasks import run_scraper; run_scraper.delay('rbi')"
```

### Option C: Wait for automatic schedule
Celery Beat triggers the scrape daily at **6:00 AM IST** automatically. No action needed.

---

## Step 4: Watch the Scrape Progress (15-30 minutes)

```bash
# Follow worker logs in real-time
docker compose logs -f worker
```

**What you'll see happening:**
```
scraper_task_started  regulator=RBI
rbi_scraper_discovering  page=1
rbi_scraper_found_links  count=25 page=1
rbi_scraper_page_delay   delay_seconds=4.2    # Polite delay
rbi_scraper_discovering  page=2
...
document_processing  url=rbi.org.in/.../penalty_xyz.pdf
text_extracted  method=native pages=3
nlp_pipeline_complete  entity=XYZ Finance Ltd  penalty=500000  confidence=0.91
document_saved  violation_id=1 review_status=auto_approved
...
scraper_task_complete  documents_found=200 documents_new=15 documents_failed=0
```

**Why 15-30 minutes?**
- We scrape politely: 3-7 second delay between each request to rbi.org.in
- ~200 pages to check × ~5 seconds = ~17 minutes just for discovery
- Then downloading + processing each new PDF

**First scrape will find the most documents** (all historical orders). Subsequent daily scrapes only find new ones (1-5 per day typically).

---

## Step 5: See Your Data

### 5a. Swagger UI (best for exploring)
Open in browser: **http://localhost:8000/docs**

Click any endpoint → "Try it out" → "Execute". Start with:
- `GET /api/v1/violations` — see all scraped violations
- `GET /api/v1/stats/overview` — total counts
- `GET /api/v1/search?q=kyc` — search by keyword

### 5b. curl (quick checks)
```bash
# How many violations were found?
curl -s http://localhost:8000/api/v1/stats/overview | python3 -m json.tool

# List recent violations
curl -s http://localhost:8000/api/v1/violations | python3 -m json.tool

# Search for a company
curl -s "http://localhost:8000/api/v1/search?q=hdfc" | python3 -m json.tool

# Who are the repeat offenders?
curl -s http://localhost:8000/api/v1/recidivists | python3 -m json.tool

# Check scrape history
curl -s http://localhost:8000/api/v1/stats/scrape-runs | python3 -m json.tool
```

### 5c. Meilisearch Dashboard
Open: **http://localhost:7700**
- Type any company name — gets typo-tolerant instant search
- "HDFC Bnk" matches "HDFC Bank"

### 5d. MinIO Console (raw PDFs)
Open: **http://localhost:9001**
- Login: `minioadmin` / `minioadmin`
- Browse `scrapperboi-raw` bucket to see stored PDFs

### 5e. Direct PostgreSQL
```bash
docker compose exec db psql -U scrapperboi -d scrapperboi

-- Recent violations
SELECT v.id, e.entity_name, v.violation_category, v.severity,
       p.amount_inr, v.order_date, v.review_status
FROM violations v
LEFT JOIN entities e ON v.entity_id = e.id
LEFT JOIN penalties p ON p.violation_id = v.id
ORDER BY v.order_date DESC
LIMIT 20;

-- Top penalized companies
SELECT e.entity_name, COUNT(*) as violations, SUM(p.amount_inr) as total_penalty
FROM violations v
JOIN entities e ON v.entity_id = e.id
LEFT JOIN penalties p ON p.violation_id = v.id
GROUP BY e.entity_name
ORDER BY violations DESC
LIMIT 10;

-- Scrape run history
SELECT * FROM scrape_runs ORDER BY started_at DESC LIMIT 5;
```

---

## Common Operations

### Stop everything
```bash
docker compose down          # Stop services, keep data
docker compose down -v       # Stop services AND delete all data (fresh start)
```

### Restart after code changes
```bash
docker compose up -d --build   # Rebuild app image with code changes
```

### Check if something is wrong
```bash
docker compose ps              # Are all services running?
docker compose logs api        # API errors?
docker compose logs worker     # Worker/scraper errors?
docker compose logs db         # Database errors?
```

### Trigger a re-scrape
```bash
curl -X POST http://localhost:8000/api/v1/scrape/rbi
```

### Fresh start (wipe everything)
```bash
docker compose down -v
docker compose up -d
docker compose exec api alembic revision --autogenerate -m "initial schema"
docker compose exec api alembic upgrade head
curl -X POST http://localhost:8000/api/v1/scrape/rbi
```

---

## What to Expect: First Scrape Results

After the first RBI scrape completes, you should see:

| Metric | Expected range |
|--------|---------------|
| Documents found | 150-400 (all historical) |
| New documents processed | 150-400 (first run, all are new) |
| Violations created | 100-350 (some docs may fail extraction) |
| Entities discovered | 80-250 unique companies |
| Auto-approved | ~60% of violations |
| Pending review | ~35% of violations |
| Rejected | ~5% of violations |
| Time taken | 15-30 minutes |
| Cost | ~$0-0.05 (most RBI docs are native text, no OCR needed) |

Subsequent daily scrapes: 0-5 new documents per day.

---

## Troubleshooting

### "Connection refused" on API
```bash
docker compose ps    # Check if api service is running
docker compose logs api   # Check for startup errors
```

### "No data" after scrape
```bash
docker compose logs worker   # Check for scraping errors
curl http://localhost:8000/api/v1/stats/scrape-runs | python3 -m json.tool  # Did the scrape run?
```

### Worker keeps restarting
```bash
docker compose logs worker --tail 50   # Check memory/import errors
```

### "Permission denied" on Docker
```bash
# Make sure your user is in docker group
groups $USER   # Should include 'docker'
# If not: sudo usermod -aG docker $USER && newgrp docker
```

### Out of memory
The full stack needs ~8GB RAM. If constrained, stop beat and trigger scrapes manually:
```bash
docker compose up -d db redis meilisearch minio api worker  # Skip beat
```
