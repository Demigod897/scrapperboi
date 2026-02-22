# scrapperboi -- Project Blueprint

## Regulatory Problem Intelligence Engine for India

---

## Table of Contents

1. [Vision](#1-vision)
2. [The Problem](#2-the-problem)
3. [Strategic Positioning](#3-strategic-positioning)
4. [Competitive Analysis](#4-competitive-analysis)
5. [Productization Paths](#5-productization-paths)
6. [Data Sources](#6-data-sources)
7. [Technical Architecture](#7-technical-architecture)
8. [Database Schema](#8-database-schema)
9. [NLP Pipeline](#9-nlp-pipeline)
10. [API Design](#10-api-design)
11. [Moat Strategy](#11-moat-strategy)
12. [Risks & Legal Concerns](#12-risks--legal-concerns)
13. [Long-Term Vision (5 Years)](#13-long-term-vision-5-years)

---

## 1. Vision

Build an AI-powered **Regulatory Problem Intelligence Engine** for India that:

- Scrapes and structures enforcement data from Indian regulators
- Extracts patterns of recurring violations
- Quantifies financial impact
- Identifies systemic compliance gaps
- Suggests monetizable SaaS opportunities
- Sells risk intelligence to enterprises, insurers, and investors

This is NOT a generic legal search tool. It becomes one of:

- A **vertical compliance SaaS** (Path A -- start here)
- A **regulatory risk data platform** (Path B -- enterprise, later)
- An **enterprise intelligence API** (Path C -- highest stickiness)

**Positioning statement**: *"The Bloomberg Terminal for Indian regulatory enforcement -- structured, searchable, alertable penalty and enforcement data for compliance teams."*

---

## 2. The Problem

India has 20+ central regulators and hundreds of state-level bodies that publish enforcement actions (penalty orders, show-cause notices, fines, directions). This data is:

- **Public** but fragmented across dozens of government websites
- **Unstructured** -- buried in PDFs, often scanned, sometimes multilingual
- **Un-mined** -- no one has built structured, queryable intelligence on top of it
- **Valuable** -- compliance officers at 9,500+ NBFCs, 80+ banks, thousands of regulated entities manually check regulator websites weekly

The compliance officer at a mid-cap NBFC today spends **4-8 hours/week** downloading RBI PDFs, reading them, and creating internal summaries. There is no tool that gives them a searchable feed, entity profiles, violation trends, or board-ready reports from enforcement data.

**No one has treated enforcement orders as a first-class data asset.**

---

## 3. Strategic Positioning

### 3.1 First Customer: NBFC Compliance Officers

| Dimension | Detail |
|-----------|--------|
| **Who** | Chief Compliance Officers (CCOs) and Company Secretaries at mid-cap NBFCs (AUM INR 1,000-20,000 Cr) |
| **Market size** | ~500-700 NBFCs in the "serious but under-resourced" sweet spot out of 9,500+ RBI-registered NBFCs |
| **Why them** | RBI's Scale-Based Regulation (SBR) framework forced mid-tier NBFCs into compliance obligations they previously didn't face. They need regulatory horizon scanning but lack Big 4 advisory budgets (INR 50L-1Cr/year). Teams are 2-5 people |
| **Budget** | INR 50K-3L/year for compliance tools. CCOs can approve under INR 2L without board sign-off -- critical for fast sales velocity |
| **Pain** | 4-8 hours/week per person manually downloading RBI PDFs, reading them, creating internal summaries. No peer benchmarking, no trend analysis, no alerts |
| **Secondary** | Tier 2-3 law firms with NBFC/banking practice (INR 1-3L/year per firm) |

### 3.2 First Vertical: RBI

| Factor | RBI | SEBI | FSSAI |
|--------|-----|------|-------|
| Data quality | Excellent -- PDFs on rbi.org.in, semi-standard format | Good but scattered across sections | Poor, inconsistent, mostly state-level |
| Enforcement volume | 200-400 penalty orders/year | 500-800 but many minor adjudications | Low, mostly state-level |
| Willingness to pay | **HIGH** -- license cancellation risk is existential | Medium | Low -- SME customers with near-zero compliance budgets |
| Customer concentration | 9,500+ NBFCs + 80+ banks + payment aggregators + fintechs | Fragmented: brokers, AMCs, listed cos, merchant bankers | Millions of unorganized food businesses |
| Regulatory pressure trend | **Increasing sharply** (SBR, digital lending, climate risk) | Stable to increasing | Stable |
| Data structure feasibility | High -- semi-standardized formats | Medium -- varies by division | Low |

**RBI wins on every dimension.** SEBI is the natural second vertical at Month 6-9.

### 3.3 Why NOT Other Positionings

| Positioning | Why Not (Initially) |
|-------------|-------------------|
| Founder idea tool | Too vague. No one pays for "inspiration" |
| PE/VC research product | Sales cycle is 3-6 months. Expect free trials. Revisit in Year 2 |
| Insurance risk intelligence | Indian insurers are 5 years behind on API-first tools. Legitimate long-term play, not a wedge |
| General legal research | Commodity market. Manupatra/SCC Online already own it. Don't compete on their terms |

### 3.4 Wedge Strategy: Free Newsletter -> Paid Dashboard

| Phase | Timeline | Action |
|-------|----------|--------|
| 1 | Weeks 1-4 | Scrape RBI penalty orders. Publish free weekly email -- **"This Week in RBI Enforcement"**. Distribute via LinkedIn, compliance WhatsApp groups, direct outreach |
| 2 | Weeks 5-8 | With 500+ subscribers, launch paid dashboard at **INR 5,000/month** (INR 60K/year). Full searchable archive, entity profiles, violation taxonomy, email alerts |
| 3 | Weeks 9-12 | Upgrade tier at **INR 15,000/month** with peer benchmarking ("How does your penalty history compare to similar-sized NBFCs?"), board-ready reports, API access |

This wedge works in India because:
- Free content builds trust and demonstrates data quality before asking for money
- INR 5K/month is within the "expense it without approval" range for compliance teams
- The email-to-dashboard conversion funnel is proven in Indian B2B SaaS (Tally, Zoho, and others have used variants)

---

## 4. Competitive Analysis

### 4.1 Existing Players in India

| Player | What They Do | Annual Revenue | Why They Miss Enforcement Intelligence |
|--------|-------------|---------------|---------------------------------------|
| **Manupatra** | India's oldest legal database. Case law, statutes, regulatory content | INR 30K-3L/year per customer | Search engine for legal text, not structured data. No entity profiles, no violation taxonomies, no analytics, no dashboards. "Library" model, not "analyst" model |
| **SCC Online** | Premium legal database (Supreme Court Cases brand) | Similar to Manupatra | Stronger in judicial content than regulatory. Same limitation: text-centric, not data-centric |
| **Indian Kanoon** | Free, open-source legal search engine | Free | Excellent for basic case law search. Terrible for regulatory enforcement analysis. No structured metadata extraction. Not a competitor but a potential data source |
| **Legistify** | Litigation management SaaS for enterprises | B2B SaaS | Different market: serves legal departments managing their own litigation, not compliance teams monitoring the landscape |
| **Leegality** | E-signing and document management | B2B SaaS | Zero overlap |
| **Signzy** | RegTech for KYC onboarding, AI-based document verification | Well-funded | "Prevent violations" space; scrapperboi is "learn from violations." Potential future partner -- Signzy could integrate scrapperboi's risk scores into onboarding decisions |

### 4.2 Three Structural Reasons No One Has Done This

1. **Legal databases think in documents, not data.** Manupatra and SCC Online index text. They don't extract structured fields (entity name, violation category, penalty amount, date, regulatory provision) from enforcement orders. Building structured data from unstructured PDFs requires NLP/ML investment that legal publishers haven't made because their customers (lawyers) don't demand it.

2. **RegTech companies focus on workflow, not intelligence.** Legistify, Leegality, and Signzy solve operational problems (manage cases, sign documents, verify identity). Market intelligence is a different product category requiring different data pipelines, different UX, and different buyer personas.

3. **No one has treated enforcement orders as a first-class data asset.** In the US, enforcement data (SEC EDGAR, CFPB complaints, FDA warning letters) has been productized by multiple startups. In India, this data sits in PDFs on regulator websites, largely un-mined.

### 4.3 International Validation

| Company | Market | What They Did | Relevance |
|---------|--------|--------------|-----------|
| **Enigma Technologies** (US) | $200M+ raised | Built business identity graph from government data (SEC, state filings, permits, violations) | India equivalent doesn't exist. scrapperboi's entity resolution is analogous |
| **Corlytics** (Ireland) | Enterprise | Regulatory risk intelligence, tracking enforcement fines globally. Serves global banks | Closest international analog. Demonstrates the model works at scale |
| **Compliance.ai** (US, acquired by Ascent) | Acquired | Regulatory change management. Tracked rule changes and mapped to obligations | Different angle (rules, not outcomes). Enforcement intelligence is arguably more valuable |
| **Behavox** (UK/US) | Enterprise | Communications surveillance for financial services compliance | Different product but pricing ($100K+ ACV) shows where the market ceiling is |

**Key insight: The enforcement intelligence category is validated globally but unoccupied in India. This is a timing arbitrage opportunity.**

### 4.4 Where scrapperboi Differentiates

- **Structured data extraction**: Converting PDF penalty orders into queryable, filterable, analyzable data. The core technical moat
- **Entity resolution**: Linking the same company across multiple enforcement actions, across regulators, and to MCA/ROC filings
- **Proprietary compliance taxonomy**: Categorizing violations into a standardized hierarchy. Whoever builds it first owns the language of compliance analytics
- **Temporal intelligence**: Trend analysis no existing tool can produce. "KYC penalty actions by RBI increased 43% in Q3 2025 vs Q2 2025" is a headline no one can currently generate from structured data

---

## 5. Productization Paths

### Path A: Vertical Compliance SaaS -- "RBI Enforcement Monitor" (START HERE)

| Dimension | Detail |
|-----------|--------|
| **Target** | CCOs and Company Secretaries at NBFCs, payment aggregators, small finance banks, cooperative banks |
| **Core features** | Real-time enforcement feed, entity profiles (full history per entity), violation taxonomy filters, peer benchmarking ("Companies in your NBFC-ICC category have faced X penalties averaging INR Y"), board report generator (one-click PDF/PPTX), alert system (email/Slack/WhatsApp) |
| **Pricing** | Starter: INR 5K/mo (1 user, search + alerts). Professional: INR 15K/mo (5 users, benchmarking, reports). Enterprise: INR 30-50K/mo (unlimited users, API, custom taxonomies) |
| **Sales cycle** | 2-4 weeks (Starter), 4-8 weeks (Professional), 8-16 weeks (Enterprise) |
| **Revenue ceiling** | 500 customers x INR 1.5L avg = **INR 7.5 Cr/year (~$900K)** |
| **Direct competitors** | Zero. Indirect: "doing it manually" + Manupatra (unstructured search) |

### Path C: Risk Scoring API -- "scrapperboi Risk API" (Month 6-9)

| Dimension | Detail |
|-----------|--------|
| **Target** | Lending platforms (fintech + traditional), insurance underwriters, trade credit insurers, B2B marketplace platforms |
| **Core features** | REST API: input company name or CIN, get back regulatory risk score (0-100) with breakdown, penalty history, violation severity, peer comparison percentile, compliance trend (improving/deteriorating). Bulk scoring for portfolio analysis |
| **Pricing** | Pay-per-call: INR 5-20/call. Monthly: INR 25K for 5K calls, INR 1L for 50K calls. Enterprise: custom |
| **Sales cycle** | 4-12 weeks (requires engineering integration, but once embedded, churn is extremely low) |
| **Revenue ceiling** | 100 API customers x INR 6L avg = **INR 6 Cr/year (~$720K)** |
| **Competitors** | Signzy, Perfios, CRIF India provide some company risk data but not enforcement-based scores. Genuinely greenfield |

### Path B: Enterprise Intelligence Platform -- "scrapperboi Intelligence" (Month 12+)

| Dimension | Detail |
|-----------|--------|
| **Target** | Large banks (SBI, HDFC, ICICI), Big 4 consulting firms (Deloitte, PwC, EY, KPMG India), PE/VC funds |
| **Core features** | Multi-regulator coverage, cross-regulator entity graph, industry risk heatmaps, regulatory trend forecasting (ML-driven), custom research reports, SSO/SAML, audit trails |
| **Pricing** | Annual contracts: INR 10L-50L/year. Big 4: INR 25-50L/year per practice. Banks: INR 15-40L/year. PE/VC: INR 5-15L/year |
| **Sales cycle** | 3-9 months. Enterprise procurement in India is slow, requires POC (30-60 days) |
| **Revenue ceiling** | 50 accounts x INR 25L avg = **INR 12.5 Cr/year (~$1.5M)** |

**Sequencing: A -> C -> B.** Path A builds the data pipeline and proves demand. Path C is a natural byproduct of structured data. Path B requires multi-regulator coverage and a sales team.

---

## 6. Data Sources

### 6.1 Central Regulators (Priority Order)

| # | Regulator | Data Type | URL Pattern | Format | Priority |
|---|-----------|-----------|-------------|--------|----------|
| 1 | **RBI** | Monetary penalties for banks/NBFCs | rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx | PDF + HTML press releases | **P0 -- Start here** |
| 2 | **SEBI** | Orders and enforcement actions | sebi.gov.in (enforcement section) | PDF | P1 -- Month 3 |
| 3 | **CCI** | Competition orders (cartels, abuse of dominance) | cci.gov.in/orders | PDF (native text) | P2 -- Month 6 |
| 4 | **MCA** | Corporate filings, insolvency | data.gov.in (CSV dumps) | CSV | P1 (for entity resolution only) |
| 5 | **FSSAI** | Food safety violations | fssai.gov.in + state FDA sites | PDF (often scanned) | P3 -- Month 9+ |
| 6 | **CPCB** | Pollution control directions | cpcb.nic.in | PDF | P3 |
| 7 | **CDSCO** | Pharma enforcement | cdsco.gov.in | PDF | P3 |
| 8 | **DGCA** | Aviation penalties | dgca.gov.in | PDF | P3 |
| 9 | **TRAI/DoT** | Telecom enforcement | trai.gov.in | PDF | P3 |
| 10 | **IRDAI** | Insurance penalties | irdai.gov.in | PDF | P2 -- Month 6 |

### 6.2 Judicial Data

| Source | Coverage | Access Method |
|--------|----------|--------------|
| **Indian Kanoon** | Supreme Court, High Courts, Tribunals | httpx (rate limit 1 req/5 sec) |
| **NCLT/NCLAT** | Insolvency cases | eCourts portal |
| **Consumer Courts** | Consumer complaints | confonet.nic.in |

### 6.3 State-Level (Deferred to Phase 3+)

- State Pollution Control Boards
- State Food Safety Departments
- RTO/Transport enforcement
- Labour department penalties

### 6.4 Data Challenges

| Challenge | Approach |
|-----------|----------|
| Fragmented across 50+ sources | Modular scraper architecture -- one scraper class per regulator |
| Poor formatting | Robust PDF processor with native text + OCR fallback |
| PDF-heavy content | PyMuPDF for native text, Tesseract/Google Vision for scanned |
| OCR requirements | Tiered OCR: Tesseract (free, English) -> Google Vision (Indic scripts, $1.50/1K pages) |
| Multilingual documents | fasttext language detection + ai4bharat/IndicNER for Hindi/regional NER. Do NOT translate -- extract entities from original text |
| ASP.NET government sites | Replay __VIEWSTATE POST parameters for pagination |

---

## 7. Technical Architecture

### 7.1 System Overview

```
[Gov Sites] --> [Scraper Fleet] --> [Raw Store (MinIO)]
                                        |
                                  [Doc Processor]
                                   /          \
                            [OCR Pipeline]  [Text Extractor]
                                   \          /
                                  [NLP Pipeline]
                                        |
                                  [Validation + HITL]
                                        |
                                  [PostgreSQL + Meilisearch]
                                        |
                                  [REST API (FastAPI)]
                                        |
                                  [Dashboard / Clients]
```

### 7.2 Project Structure

```
scrapperboi/
    config/
        settings.py              # Pydantic BaseSettings (env-based)
        sources.yaml             # Per-regulator config (URLs, schedules, delays)
    scrapers/
        __init__.py
        base.py                  # AbstractBaseScraper
        rbi.py                   # RBI penalty orders
        sebi.py                  # SEBI enforcement orders (Phase 2)
    processors/
        __init__.py
        pdf_processor.py         # PDF text extraction + OCR routing
        ocr.py                   # Tiered OCR (Tesseract -> Google Vision)
        language_detector.py     # fasttext-based detection
    nlp/
        __init__.py
        pipeline.py              # Orchestrator
        entity_extractor.py      # spaCy + IndicNER + regex (CIN, PAN)
        penalty_extractor.py     # Indian currency parsing (Rs, lakhs, crores)
        date_normalizer.py       # Indian date formats (dd/mm/yyyy)
        violation_classifier.py  # Zero-shot BART-MNLI + taxonomy
        entity_resolver.py       # Fuzzy match against MCA master (rapidfuzz)
        validators.py            # Confidence scoring + sanity checks
    storage/
        __init__.py
        db.py                    # SQLAlchemy 2.0 models
        search.py                # Meilisearch client
        raw_store.py             # MinIO/S3 abstraction
    api/
        __init__.py
        main.py                  # FastAPI app
        dependencies.py          # DB sessions, auth
        routers/
            __init__.py
            violations.py
            entities.py
            search.py
            stats.py
    workers/
        __init__.py
        celery_app.py            # Celery + Redis
        tasks.py                 # Scrape + process tasks
    tests/
    alembic/                     # DB migrations
    docker-compose.yml
    Dockerfile
    requirements.txt
    .env.example
```

### 7.3 Tech Stack

| Layer | Technology | Version | Why |
|-------|-----------|---------|-----|
| **Language** | Python | 3.11+ | Best ecosystem for NLP + scraping |
| **HTTP Client** | httpx | 0.27+ | Async, HTTP/2, modern |
| **HTML Parsing** | BeautifulSoup4 + lxml | 4.12+ | Fast, reliable |
| **JS Rendering** | Playwright | 1.40+ | Only for FSSAI state sites |
| **PDF Text** | PyMuPDF (fitz) | 1.24+ | Fastest native text extraction |
| **PDF to Image** | pdf2image (poppler) | 0.17+ | For OCR pipeline |
| **OCR Tier 1** | Tesseract | 5.3+ | Free, good for clean English prints |
| **OCR Tier 2** | Google Cloud Vision | latest | Excellent for Indic scripts (~$1.50/1K pages) |
| **Language Detection** | fasttext | 0.9.2 | Fast, accurate, multilingual |
| **NLP (English)** | spaCy | 3.7+ | en_core_web_trf model (transformer-based) |
| **NLP (Indic)** | ai4bharat/IndicNER | HF latest | Hindi, Marathi, Bengali, Tamil, Telugu NER |
| **Classification** | HuggingFace transformers | 4.38+ | Zero-shot with facebook/bart-large-mnli |
| **Fuzzy Matching** | rapidfuzz | 3.6+ | Entity resolution against MCA master |
| **Task Queue** | Celery + Redis | 5.3+ / 7+ | Scheduling, async processing |
| **Database** | PostgreSQL | 16 | Primary store + pg_trgm for fuzzy search |
| **ORM** | SQLAlchemy | 2.0+ | Async support, mature |
| **Migrations** | Alembic | 1.13+ | Standard for SQLAlchemy |
| **Search** | Meilisearch | 1.6+ | Lightweight (300MB RAM), typo-tolerant, free |
| **Object Storage** | MinIO | latest | S3-compatible, self-hosted, free |
| **API** | FastAPI | 0.109+ | Auto-docs, async, fast |
| **Logging** | structlog | latest | Structured JSON logs |
| **Monitoring** | Celery Flower | latest | Task monitoring web UI |
| **Containerization** | Docker + docker-compose | latest | Dev and prod |

### 7.4 Scraping Strategy Per Regulator

| Source | Site Tech | Scraping Tool | Key Challenge | Concurrency |
|--------|-----------|--------------|---------------|-------------|
| **RBI** | ASP.NET | httpx + POST | Replay __VIEWSTATE for pagination | 1 connection, 3-7 sec delay |
| **SEBI** | Java webapp | httpx + BS4 | Simple query param pagination | 2 connections, 2-5 sec delay |
| **CCI** | Standard HTML | httpx | Year-wise filters, straightforward | 1 connection, 2-5 sec delay |
| **CPCB** | NIC template | httpx | Standard NIC site | 1 connection, 3-5 sec delay |
| **Indian Kanoon** | Simple HTML | httpx | Rate limit aggressively (1 req/5 sec) | 1 connection, 5-10 sec delay |
| **MCA** | N/A (CSV) | Direct download from data.gov.in | Not scraping -- bulk CSV load | N/A |
| **FSSAI state sites** | Some React/Angular | Playwright | Most challenging, defer to Phase 2 | 1 connection, 5-10 sec delay |

**Rule**: Default to httpx. Only use Playwright for sites that genuinely require JS execution (10x more resource-intensive).

**Politeness rules**:
- 1 concurrent connection per government domain
- Random delays between requests (2-10 sec depending on source)
- Respect robots.txt (parse with `urllib.robotparser`)
- Identify in User-Agent with contact URL
- If 429/503, exponential backoff + alert
- Run scrapes during off-peak IST hours (6 AM)

### 7.5 Infrastructure (Cost-Effective)

**Phase 1 (0-6 months): Single VPS**

- Provider: Hetzner Cloud (best price/performance)
- Spec: 4 vCPU, 16GB RAM, 160GB SSD (~$15-20/month)
- Everything via docker-compose: PostgreSQL, Redis, Meilisearch, MinIO, FastAPI, Celery
- Handles: ~10K documents, ~50K violations, 10 concurrent API users

**Phase 2 (6-12 months): Split services**

- PostgreSQL -> managed service (Supabase/Neon/Aiven free tier)
- MinIO -> Cloudflare R2 (free egress, $0.015/GB)
- Compute stays on Hetzner

**Phase 3 (12+ months): Scale**

- Kubernetes on Hetzner or AWS
- Separate scraper workers from NLP workers
- GPU instance for NLP inference if volume justifies

---

## 8. Database Schema

### 8.1 Core Tables

```sql
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Reference data
CREATE TABLE regulators (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(20) UNIQUE NOT NULL,     -- 'RBI', 'SEBI'
    full_name       TEXT NOT NULL,
    website_url     TEXT,
    jurisdiction    VARCHAR(50) DEFAULT 'INDIA',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE violation_types (
    id              SERIAL PRIMARY KEY,
    category        VARCHAR(50) NOT NULL,             -- 'BANKING_REGULATORY'
    subtype         VARCHAR(50) NOT NULL,             -- 'KYC_AML_VIOLATION'
    description     TEXT,
    UNIQUE (category, subtype)
);

-- Entities (companies, individuals, banks)
CREATE TABLE entities (
    id              SERIAL PRIMARY KEY,
    entity_type     VARCHAR(20) NOT NULL,             -- COMPANY, INDIVIDUAL, BANK, NBFC
    entity_name     TEXT NOT NULL,
    cin             VARCHAR(21) UNIQUE,               -- MCA Corporate Identity Number
    pan             VARCHAR(10),
    gstin           VARCHAR(15),
    mca_status      VARCHAR(30),
    aliases         TEXT[],
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Documents (scraped files)
CREATE TABLE documents (
    id              SERIAL PRIMARY KEY,
    source_url      TEXT NOT NULL,
    content_hash    VARCHAR(64) NOT NULL UNIQUE,      -- SHA-256, dedup key
    regulator_id    INTEGER REFERENCES regulators(id),
    document_type   VARCHAR(10) NOT NULL,             -- PDF, HTML, IMAGE
    title           TEXT,
    raw_storage_key TEXT NOT NULL,                     -- MinIO key
    extracted_text  TEXT,
    extraction_method VARCHAR(20),                     -- native, ocr_tesseract, ocr_gcloud
    language        VARCHAR(10) DEFAULT 'en',
    page_count      INTEGER,
    scraped_at      TIMESTAMPTZ NOT NULL,
    processed_at    TIMESTAMPTZ,
    processing_status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed, review
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Violations (CORE TABLE)
CREATE TABLE violations (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id),
    regulator_id    INTEGER NOT NULL REFERENCES regulators(id),
    entity_id       INTEGER REFERENCES entities(id),
    violation_type_id INTEGER REFERENCES violation_types(id),
    order_date      DATE,
    violation_date  DATE,
    summary         TEXT,
    raw_excerpt     TEXT,
    violation_category VARCHAR(50),
    violation_subtype  VARCHAR(50),
    severity        VARCHAR(20),                       -- LOW, MEDIUM, HIGH, CRITICAL
    appeal_status   VARCHAR(30),
    extraction_confidence FLOAT NOT NULL DEFAULT 0.0,
    review_status   VARCHAR(20) DEFAULT 'auto_approved',
    reviewed_by     VARCHAR(100),
    reviewed_at     TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Penalties
CREATE TABLE penalties (
    id              SERIAL PRIMARY KEY,
    violation_id    INTEGER NOT NULL REFERENCES violations(id),
    penalty_type    VARCHAR(30) NOT NULL,              -- MONETARY, SUSPENSION, REVOCATION, WARNING, DEBARMENT
    amount_inr      NUMERIC(15, 2),
    amount_raw_text TEXT,
    currency        VARCHAR(3) DEFAULT 'INR',
    duration_days   INTEGER,
    description     TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Multi-entity orders
CREATE TABLE violation_entities (
    violation_id    INTEGER NOT NULL REFERENCES violations(id),
    entity_id       INTEGER NOT NULL REFERENCES entities(id),
    role            VARCHAR(30) DEFAULT 'RESPONDENT',
    PRIMARY KEY (violation_id, entity_id, role)
);

-- MCA Company Master (entity resolution reference)
CREATE TABLE mca_company_master (
    cin             VARCHAR(21) PRIMARY KEY,
    company_name    TEXT NOT NULL,
    company_status  VARCHAR(30),
    company_class   VARCHAR(30),
    date_of_incorporation DATE,
    registered_state VARCHAR(50),
    roc             VARCHAR(50),
    email           TEXT,
    loaded_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Operational tables
CREATE TABLE entity_resolution_log (
    id              SERIAL PRIMARY KEY,
    extracted_name  TEXT NOT NULL,
    resolved_entity_id INTEGER REFERENCES entities(id),
    resolution_method VARCHAR(30),
    confidence      FLOAT,
    resolved_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE review_queue (
    id              SERIAL PRIMARY KEY,
    violation_id    INTEGER REFERENCES violations(id),
    document_id     INTEGER REFERENCES documents(id),
    reason          TEXT NOT NULL,
    priority        INTEGER DEFAULT 5,
    assigned_to     VARCHAR(100),
    status          VARCHAR(20) DEFAULT 'open',
    resolution_notes TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ
);

CREATE TABLE scrape_runs (
    id              SERIAL PRIMARY KEY,
    regulator_id    INTEGER NOT NULL REFERENCES regulators(id),
    started_at      TIMESTAMPTZ NOT NULL,
    completed_at    TIMESTAMPTZ,
    status          VARCHAR(20) DEFAULT 'running',
    documents_found INTEGER DEFAULT 0,
    documents_new   INTEGER DEFAULT 0,
    documents_failed INTEGER DEFAULT 0,
    error_message   TEXT,
    metadata        JSONB DEFAULT '{}'
);
```

### 8.2 Key Indexes

```sql
CREATE INDEX idx_entities_name_trgm ON entities USING gin (entity_name gin_trgm_ops);
CREATE INDEX idx_entities_cin ON entities (cin) WHERE cin IS NOT NULL;
CREATE INDEX idx_documents_hash ON documents (content_hash);
CREATE INDEX idx_documents_status ON documents (processing_status);
CREATE INDEX idx_violations_entity ON violations (entity_id);
CREATE INDEX idx_violations_regulator ON violations (regulator_id);
CREATE INDEX idx_violations_order_date ON violations (order_date DESC);
CREATE INDEX idx_violations_type ON violations (violation_category, violation_subtype);
CREATE INDEX idx_violations_review ON violations (review_status) WHERE review_status = 'pending_review';
CREATE INDEX idx_penalties_amount ON penalties (amount_inr DESC) WHERE amount_inr IS NOT NULL;
CREATE INDEX idx_mca_name_trgm ON mca_company_master USING gin (company_name gin_trgm_ops);
CREATE INDEX idx_review_queue_status ON review_queue (status, priority);
```

### 8.3 Materialized View: Recidivism

```sql
CREATE MATERIALIZED VIEW entity_violation_summary AS
SELECT
    e.id AS entity_id,
    e.entity_name,
    e.cin,
    COUNT(v.id) AS total_violations,
    COUNT(DISTINCT v.regulator_id) AS distinct_regulators,
    COALESCE(SUM(p.amount_inr), 0) AS total_penalty_inr,
    MIN(v.order_date) AS first_violation_date,
    MAX(v.order_date) AS latest_violation_date,
    array_agg(DISTINCT v.violation_category)
        FILTER (WHERE v.violation_category IS NOT NULL) AS violation_categories
FROM entities e
JOIN violations v ON v.entity_id = e.id
LEFT JOIN penalties p ON p.violation_id = v.id
GROUP BY e.id, e.entity_name, e.cin;

-- Refresh nightly: REFRESH MATERIALIZED VIEW CONCURRENTLY entity_violation_summary;
```

### 8.4 Search Indexing (Meilisearch)

Meilisearch over Elasticsearch because:
- 10x simpler to operate (single binary, no JVM)
- 300MB RAM vs 2GB+ for Elasticsearch
- Built-in typo tolerance (critical for misspelled Indian company names)
- Free and open source

Index settings:
- Searchable: entity_name, summary, violation_category, violation_subtype, regulator_code, raw_excerpt
- Filterable: regulator_code, violation_category, order_date, penalty_amount_inr, entity_type, review_status
- Sortable: order_date, penalty_amount_inr, created_at

---

## 9. NLP Pipeline

### 9.1 Pipeline Flow

```
Raw Text
    |-> Language Detection (fasttext)
    |-> Text Cleaning (normalize whitespace, remove headers/footers)
    |-> Entity Extraction
    |     |-> Regex: CIN (L/U + 5 digits + 2 alpha + 4 digits + 3 alpha + 6 digits)
    |     |-> Regex: PAN ([A-Z]{5}[0-9]{4}[A-Z])
    |     |-> spaCy en_core_web_trf: ORG and PERSON entities (English)
    |     |-> ai4bharat/IndicNER: ORG and PER entities (Hindi/Indic)
    |     |-> Keyword matching: Regulator names
    |-> Penalty Amount Extraction
    |     |-> Indian formats: "Rs. 5,00,000", "Rs.5 lakh", "INR 2.5 crores"
    |     |-> Multiplier map: lakh=100K, crore=10M, lac=100K, cr=10M
    |     |-> Sanity check: Rs 1,000 to Rs 500 crore range
    |-> Date Extraction + Normalization
    |     |-> Indian formats: dd/mm/yyyy, dd.mm.yyyy, "1st January 2024"
    |     |-> Context classification: order date vs violation date
    |     |-> Sanity: 1990 to today+30 days
    |-> Violation Type Classification
    |     |-> Zero-shot with facebook/bart-large-mnli
    |     |-> 3-level taxonomy: Domain > Category > Specific Violation
    |     |-> Phase 2: Fine-tune distilbert after 500 labeled samples
    |-> Entity Resolution
    |     |-> Normalize company name (remove PVT LTD, LIMITED, punctuation)
    |     |-> Exact match against MCA company master
    |     |-> Fuzzy match (rapidfuzz token_sort_ratio, threshold 85)
    |     |-> If CIN extracted, cross-validate name against MCA record
    |-> Confidence Scoring
    |     |-> Per-field confidence from extractors
    |     |-> Weighted average: entity 30%, penalty 20%, violation 20%, CIN 15%, date 15%
    |-> Validation Gate
          |-> >= 0.85: auto-approve -> write to DB
          |-> 0.3 to 0.85: route to human review queue
          |-> < 0.3: reject (log only)
```

### 9.2 Violation Taxonomy

```
BANKING_REGULATORY/
    KYC_AML_VIOLATION
    LENDING_NORMS_VIOLATION
    FAIR_PRACTICES_CODE
    DEPOSIT_ACCEPTANCE_VIOLATION
    REPORTING_FAILURE
    CAPITAL_ADEQUACY
    ASSET_CLASSIFICATION

SECURITIES_MARKET/
    INSIDER_TRADING
    MARKET_MANIPULATION
    DISCLOSURE_FAILURE
    INTERMEDIARY_VIOLATION
    TAKEOVER_CODE_VIOLATION
    MUTUAL_FUND_VIOLATION

FOOD_SAFETY/
    ADULTERATION
    MISLABELING
    HYGIENE_VIOLATION
    LICENSE_VIOLATION
    SUBSTANDARD_PRODUCT

ENVIRONMENTAL/
    EMISSION_STANDARD_VIOLATION
    EFFLUENT_DISCHARGE
    HAZARDOUS_WASTE
    CONSENT_ORDER_VIOLATION

COMPETITION/
    ANTI_COMPETITIVE_AGREEMENT
    ABUSE_OF_DOMINANCE
    GUN_JUMPING

CORPORATE_GOVERNANCE/
    DIRECTOR_DISQUALIFICATION
    FILING_DEFAULT
    FRAUD
    RELATED_PARTY_TRANSACTION
```

### 9.3 Avoiding Hallucinations

- **Never use LLMs for fact extraction without validation.** Use regex/rule-based for structured fields (CIN, PAN, amounts, dates). Use NLP models only for NER and classification where regex is insufficient.
- **Every extraction passes 3 validation gates**: format check, cross-reference check, confidence threshold.
- **Human-in-the-loop**: Anything below 0.85 confidence goes to review queue. Human corrections are logged and used to retrain models.
- **Link to original source**: Every data point traces back to the source document. Users can verify.

---

## 10. API Design

### 10.1 Endpoints

```
GET  /api/v1/violations
     ?regulator=RBI
     &entity_name=HDFC
     &date_from=2023-01-01
     &date_to=2024-12-31
     &violation_type=BANKING_REGULATORY/KYC_AML_VIOLATION
     &min_penalty=100000
     &page=1&per_page=20

GET  /api/v1/violations/{id}
     Full violation detail with document, entity, penalties

GET  /api/v1/entities/{id}
     Entity profile with all violations (recidivism view)

GET  /api/v1/entities/{id}/timeline
     Chronological violation timeline

GET  /api/v1/search?q=insider+trading+HDFC
     Full-text search via Meilisearch

GET  /api/v1/stats/regulators
     Aggregate: violations by regulator, by year, total penalties

GET  /api/v1/recidivists?min_violations=3
     Repeat offenders list

POST /api/v1/webhooks
     Subscribe to new violations matching a filter (alerting)
```

### 10.2 Authentication

- Phase 1: API key header (`X-API-Key`). Keys stored in DB with rate limits.
- Phase 2: JWT/OAuth2 for dashboard users.

---

## 11. Moat Strategy

### 11.1 Data Normalization (Primary Moat)

The raw data is public. Anyone can download RBI penalty orders. **The moat is the structured, normalized, linked, enriched version:**

- **Entity resolution graph**: Linking "XYZ Finance Ltd" (RBI) to CIN U65990MH2010PLC12345 (MCA) to "XYZ Finance Limited" (SEBI). Gets more accurate monthly. A new competitor needs months to replicate.
- **Historical depth**: By Day 90, 5+ years of structured RBI data. Backfilling is expensive.
- **Cross-reference links**: Same entity across multiple regulators, with timeline.

### 11.2 Proprietary Compliance Taxonomy (Deepest Moat)

Three-level violation hierarchy that doesn't exist as a standard in India. Once compliance teams use your taxonomy in board reports, they've adopted your language. Switching means retraining and re-mapping everything.

### 11.3 Network Effects

- **Weak initially**: Each customer uses independently (not a marketplace)
- **Stronger over time**: If "compliance community" feature added (anonymous sharing of violation resolution approaches -- Stack Overflow for compliance), value grows with participants
- **Data network effects from API**: Every integration teaches which entities/dimensions matter, allowing prioritized enrichment

### 11.4 Switching Costs (Escalating by Tier)

| Tier | Switching Cost | Why |
|------|---------------|-----|
| Starter (INR 5K/mo) | Low | Can go back to manual checking |
| Professional (INR 15K/mo) | Medium | Board reports built on your taxonomy |
| Enterprise/API | High | Embedded in GRC platforms, lending engines. Ripping out requires engineering re-validation |

**Honest assessment**: Moat is thin initially. It's a data quality and speed moat, not structural. Deepens with time, taxonomy adoption, and API integrations. First 12-18 months are a race.

---

## 12. Risks & Legal Concerns

### 12.1 Scraping Legality -- LOW RISK

- **IT Act Section 43**: Penalizes unauthorized access. But scraping publicly available data from government websites (no login, no paywall, no ToS prohibiting bots) is generally not "unauthorized access."
- **Copyright Act Section 52(1)(q)**: Reproduction of judgments/orders of courts, tribunals, or quasi-judicial authorities is NOT copyright infringement. RBI penalty orders are quasi-judicial orders. Strong legal defense.
- **Mitigation**: Rate-limit (1 req/3 sec), identify in User-Agent, respect robots.txt, cache aggressively, link to original source, consider filing RTI requests for paper trail.

### 12.2 Defamation Risk -- MEDIUM RISK

- If a summary is inaccurate, the penalized entity could claim defamation (BNS 356/357) or file civil suit.
- If a risk score causes business loss (lender refuses based on score), tortious interference claim possible.
- **Mitigation**: Always link to original source. Factual, neutral language only ("RBI imposed a penalty of INR X on [entity] for [violation as stated in the order]"). Never editorialize. Add disclaimers. Get a media/defamation lawyer on retainer (INR 50K-1L/year).

### 12.3 Credit Bureau Regulation -- MEDIUM RISK (Path C only)

- If API risk scores are used in credit decisions, could be classified as "credit information company" under CICRA 2005 (requires RBI registration).
- **Mitigation**: Position as "regulatory intelligence" not "credit information." Do not market as substitute for CIBIL/Equifax. Consult fintech regulation lawyer before commercial API launch.

### 12.4 Regulator Sensitivity -- LOW RISK

- RBI is sensitive about data aggregation and fintech. If scrapperboi becomes prominent, questions may arise.
- **Mitigation**: Stay in data/intelligence lane. Frame as "improving regulatory compliance culture." Not a financial services provider.

### 12.5 Data Quality Liability -- MEDIUM RISK

- Compliance officer relies on wrong data for board report -> company makes bad decision.
- **Mitigation**: ToS with liability cap at fees paid. Disclaim fitness for any particular purpose. Confidence scoring + human review to minimize errors.

### 12.6 Indian Customers Don't Pay Fast Enough -- HIGH RISK

- This is the #1 startup risk. Not competition.
- **Mitigation**: Free content wedge (builds trust), low entry price (INR 5K/mo), annual billing discounts, target compliance (regulatory cost, not discretionary spend), keep costs brutally low (single VPS at $20/mo).

---

## 13. Long-Term Vision (5 Years)

| Year | Revenue Target | Team | Key Milestones |
|------|---------------|------|----------------|
| 1 | INR 50L-1.5Cr ($60-180K) | 2-4 | 100+ customers, RBI+SEBI data, product-market fit |
| 2 | INR 3-6Cr ($360-720K) | 8-12 | Multi-regulator (IRDAI, CCI, NCLT, FSSAI), first enterprise clients (banks, Big 4), seed round at INR 25-40Cr valuation |
| 3 | INR 10-20Cr ($1.2-2.4M) | 20-30 | 50+ API integrations, "India Compliance Graph" (linked dataset across all regulators + MCA + courts), Series A |
| 4 | INR 30-50Cr ($3.6-6M) | 40-60 | SE Asia expansion (Singapore MAS, Indonesia OJK, Philippines BSP -- same pipeline architecture works), Singapore as entry point (English-language, highest willingness to pay) |
| 5 | INR 80Cr+ ($10M+ ARR) | 80+ | Full platform. ERP integration (Tally, Zoho Books, SAP). Potential acquirers: Thomson Reuters, Wolters Kluwer, Moody's, MSCI. Or: build the "Compliance LLM" -- fine-tuned on largest corpus of Indian regulatory enforcement data |

**$10M ARR reality check**: Realistic but requires SE Asia expansion. India alone caps at ~$4-6M ARR due to low ACV. Need either 500+ mid-market customers at INR 1.5-2L avg, or 50-100 enterprise at INR 8-15L avg, or a combination with API revenue.

**Maximum outcome**: The Moody's of emerging market regulatory risk. Every lending decision, insurance underwriting, M&A due diligence, and investor risk assessment references your data. Billion-dollar company.

**Most likely good outcome**: $30-100M company (revenue or valuation) acquired by Thomson Reuters/Wolters Kluwer, or profitable growing Indian SaaS.

**Most common failure mode**: Not competition. Indian customers don't pay enough, fast enough, and the company burns through runway. Mitigate by starting with NBFC compliance (clear pain, budget, short sales cycle) and keeping costs at $20/month infrastructure.
