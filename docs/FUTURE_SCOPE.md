# scrapperboi — Future Scope & Plan

## What Exists Today vs What Gets Built Next

---

## Current State (Phase 1 — RBI Only)

```
TODAY:
  ✅ RBI penalty order scraper (live, daily at 6 AM)
  ✅ PDF processing + OCR pipeline
  ✅ NLP pipeline (entity extraction, penalty parsing, classification)
  ✅ PostgreSQL database with full schema
  ✅ Meilisearch for typo-tolerant search
  ✅ REST API with 10+ endpoints
  ✅ Celery scheduling for automated daily scrapes
  ✅ MinIO raw document storage

  ❌ No SEBI, CCI, IRDAI, or other regulators
  ❌ No dashboard UI (API-only)
  ❌ No authentication or paid tiers
  ❌ No alerting system
  ❌ No board report generation
  ❌ No risk scoring API
```

This document maps every feature, expansion, and capability planned from now through Year 5.

---

## Phase 2: Monetization (Months 2-3)

### 2.1 Authentication & User Management

**What**: Email/password auth with API key generation for programmatic access.

**Why now**: Can't charge money without accounts.

**Implementation**:
- Add `users` and `api_keys` tables to PostgreSQL
- JWT tokens for dashboard sessions
- `X-API-Key` header for API access
- Rate limiting per API key (100 requests/hour free, higher for paid)

**Files to create**:
```
api/auth.py              # JWT generation, password hashing (bcrypt)
api/routers/auth.py      # /register, /login, /api-keys
storage/models/user.py   # User, APIKey SQLAlchemy models
api/middleware.py         # Rate limiting middleware
```

### 2.2 Alert System

**What**: Customers save search criteria and receive email notifications when new violations match.

**Why now**: This is the #1 feature compliance officers will pay for. "Tell me when RBI penalizes any NBFC for KYC violations" — that's their core need.

**Implementation**:
- `saved_searches` table: user_id, filter criteria (JSON), notification_channel
- After each scrape run, check new violations against all saved searches
- Send email via Amazon SES or Resend (both free tier: 200-1000 emails/day)
- Daily digest option (batch all matches into one email)

**Files to create**:
```
storage/models/alert.py      # SavedSearch model
workers/tasks.py             # Add check_alerts() task after scrape
notifications/email.py       # Email sending via SES/Resend
templates/alert_email.html   # Jinja2 email template
```

**Future channels**: WhatsApp (via WhatsApp Business API — critical for India), Slack webhook, Microsoft Teams.

### 2.3 Payment Integration

**What**: Razorpay integration for INR payments. UPI, cards, net banking.

**Why Razorpay**: Dominant in Indian B2B SaaS. Supports recurring subscriptions. 2% transaction fee. No monthly minimum.

**Pricing tiers**:

| Tier | Price | Features |
|------|-------|----------|
| Free | ₹0 | 10 searches/day, no alerts, no API |
| Starter | ₹5,000/month | Unlimited search, 5 alerts, 1 user |
| Professional | ₹15,000/month | 5 users, board reports, 20 alerts, peer benchmarking |
| Enterprise | ₹30,000-50,000/month | Unlimited users, API access, custom taxonomies, SSO |

**Founding member offer**: First 50 customers get annual rate of ₹40,000/year (33% discount on Starter).

**Files to create**:
```
api/routers/billing.py       # Subscription management
storage/models/subscription.py  # Plan, Subscription models
payments/razorpay.py         # Razorpay API integration
```

### 2.4 Basic Dashboard UI

**What**: Minimal web frontend — search, filter, view violations, entity profiles.

**Tech choice**: Simple server-rendered HTML with HTMX + Tailwind CSS. NOT a full React SPA.

**Why not React?** For a dashboard with search, filter, and view — React is overkill. HTMX lets you build interactive UIs with zero JavaScript build toolchain. Ship in 3-4 days instead of 2-3 weeks. Switch to React only if dashboard complexity demands it (Phase 4+).

**Pages**:
```
/                        → Search page (search bar + recent violations)
/violations              → Filterable violation list
/violations/{id}         → Violation detail (with link to original PDF)
/entities/{id}           → Entity profile (all violations, timeline)
/stats                   → Charts (penalties by quarter, by type, by regulator)
/alerts                  → Manage saved searches and notification preferences
/account                 → Profile, API keys, billing
```

### 2.5 Board Report Generator

**What**: One-click generation of a quarterly compliance report in PDF or PPTX format.

**Why this matters**: Compliance officers present to their board of directors quarterly. Today they manually compile data from RBI's website into PowerPoint. This feature alone justifies the Professional tier (₹15,000/month).

**Template contents**:
- Executive summary (total RBI enforcement actions this quarter)
- Penalties by violation type (bar chart)
- Peer benchmarking ("NBFCs in your AUM bracket received X penalties averaging ₹Y")
- Top enforcement trends (what's RBI focusing on?)
- Recommendations (based on most common violation types)

**Implementation**: Jinja2 templates → WeasyPrint (PDF) or python-pptx (PPTX).

**Files to create**:
```
reports/generator.py             # Report generation logic
reports/templates/quarterly.html # Jinja2 HTML template (for PDF)
reports/templates/quarterly.pptx # PPTX template
api/routers/reports.py           # /api/v1/reports/generate endpoint
```

---

## Phase 3: Multi-Regulator Expansion (Months 3-6)

### 3.1 SEBI Scraper

**What**: Scrape SEBI enforcement orders from sebi.gov.in.

**Why SEBI second**: Highest demand from Phase 2 customers. SEBI covers securities markets — relevant to brokers, AMCs, listed companies, and any compliance team that cares about capital markets.

**Technical approach**:
- sebi.gov.in uses a Java backend with simple HTML pagination (query params: `page=1`, `page=2`)
- Much simpler than RBI's ASP.NET — standard httpx + BeautifulSoup
- Documents are almost entirely PDFs (native text, rarely scanned)

**New violation taxonomy entries**:
```
SECURITIES_MARKET/
    INSIDER_TRADING
    MARKET_MANIPULATION
    DISCLOSURE_FAILURE
    INTERMEDIARY_VIOLATION
    TAKEOVER_CODE_VIOLATION
    MUTUAL_FUND_VIOLATION
```

**File to create**: `scrapers/sebi.py`

**Estimated data volume**: 500-800 enforcement orders per year.

### 3.2 MCA Entity Resolution (Full Load)

**What**: Download the complete MCA company master CSV from data.gov.in and load ~2 million company records into PostgreSQL.

**Why**: Entity resolution quality jumps dramatically. Instead of fuzzy-matching company names extracted from RBI orders against nothing, we match against the official government registry. This enables:
- Linking "XYZ Finance Ltd" (RBI order) to CIN U65990MH2010PLC12345 (MCA)
- Cross-referencing the same company across RBI and SEBI
- Enriching entity profiles with incorporation date, registered state, company status

**Implementation**:
```bash
# Download from data.gov.in (published monthly by MCA)
wget https://data.gov.in/...company_master_data.csv

# Load into PostgreSQL
COPY mca_company_master FROM '/path/to/csv' WITH CSV HEADER;
```

**Data**: ~2 million rows, ~200MB. Refresh monthly.

### 3.3 CCI Scraper

**What**: Scrape Competition Commission of India orders.

**Why**: CCI covers anti-competitive agreements (cartels), abuse of dominance, and merger violations. High-value data — CCI penalties can be hundreds of crores. Relevant to corporate law firms and enterprise compliance teams.

**Technical approach**: Well-structured website with year-wise filters. Standard httpx scraping.

**New taxonomy**:
```
COMPETITION/
    ANTI_COMPETITIVE_AGREEMENT
    ABUSE_OF_DOMINANCE
    GUN_JUMPING
```

**File to create**: `scrapers/cci.py`

### 3.4 IRDAI Scraper

**What**: Scrape Insurance Regulatory and Development Authority orders.

**Why**: Opens up the insurance vertical — a new customer segment (insurance companies, brokers, TPAs).

**File to create**: `scrapers/irdai.py`

### 3.5 Cross-Regulator Entity Graph

**What**: When viewing an entity profile, show violations from ALL regulators. "HDFC has 7 RBI violations, 3 SEBI violations, 1 CCI investigation."

**Why**: This is where the platform becomes genuinely more valuable than checking each regulator's website individually. No one else can show a unified view.

**Implementation**: Already built into the data model. The `violations` table has `regulator_id` and `entity_id` — the entity profile endpoint (`GET /api/v1/entities/{id}`) already shows all violations across regulators. Just needs data from multiple scrapers.

---

## Phase 4: Risk Scoring API (Months 6-9)

### 4.1 Regulatory Risk Score

**What**: REST API endpoint that takes a company name or CIN and returns a regulatory risk score (0-100).

```
GET /api/v1/risk/U65990MH2010PLC123456

Response:
{
    "cin": "U65990MH2010PLC123456",
    "entity_name": "XYZ Finance Private Limited",
    "risk_score": 72,
    "risk_level": "HIGH",
    "breakdown": {
        "violation_frequency": 0.8,      # Multiple violations
        "violation_severity": 0.65,       # Some medium/high severity
        "penalty_magnitude": 0.7,         # Total penalties above peer average
        "recency": 0.75,                  # Recent violation (last 6 months)
        "trend": "DETERIORATING"          # Getting worse, not better
    },
    "peer_percentile": 85,               # Worse than 85% of peers
    "peer_group": "NBFC-ICC (AUM 1000-5000 Cr)",
    "violations_summary": {
        "total": 5,
        "last_12_months": 2,
        "total_penalty_inr": 15000000,
        "categories": ["KYC_AML_VIOLATION", "LENDING_NORMS_VIOLATION"]
    }
}
```

### 4.2 Risk Score Algorithm

```
risk_score = weighted_sum(
    violation_count_score     × 0.25,   # More violations = higher risk
    severity_score            × 0.20,   # Critical/High = more risk
    penalty_magnitude_score   × 0.20,   # Large penalties = more risk
    recency_score             × 0.20,   # Recent = more risk (exponential decay)
    multi_regulator_score     × 0.15,   # Violations from multiple regulators = more risk
)

Each component: normalized 0-1
Final score: scaled 0-100
```

### 4.3 Target Customers for Risk API

| Customer type | Use case | How they'd integrate |
|--------------|----------|---------------------|
| **Fintech lenders** | Check borrower's regulatory history before approving loan | Call API during underwriting |
| **Trade credit insurers** | Assess regulatory risk of insured companies | Batch score portfolio nightly |
| **B2B marketplaces** | Verify supplier compliance standing | Badge on marketplace profile |
| **Banks (KYC teams)** | Enhanced due diligence for high-risk customers | Embed in onboarding workflow |

### 4.4 Pricing

| Plan | Price | Volume |
|------|-------|--------|
| Starter | ₹25,000/month | 5,000 API calls |
| Growth | ₹1,00,000/month | 50,000 API calls |
| Enterprise | Custom | Unlimited + SLA |
| Pay-per-call | ₹5-20/call | No commitment |

### 4.5 Legal Consideration

If risk scores are used in credit decisions, this could be classified as a "credit information company" under the Credit Information Companies (Regulation) Act, 2005 — which requires RBI registration.

**Mitigation**:
- Position as "regulatory intelligence" not "credit information"
- Do NOT market as a substitute for CIBIL, Equifax, Experian, or CRIF
- Terms of service explicitly state: "Not to be used as the sole basis for credit decisions"
- Consult a fintech regulation lawyer before commercial launch

**Files to create**:
```
api/routers/risk.py              # Risk score endpoint
nlp/risk_scorer.py               # Score computation logic
storage/models/risk_cache.py     # Cache scores (recompute daily, not per-request)
```

---

## Phase 5: Enterprise Features (Months 9-12)

### 5.1 SSO / SAML Authentication

**What**: Allow enterprise customers to login with their corporate identity (Google Workspace, Azure AD, Okta).

**Why**: Enterprise procurement requires SSO. Banks and Big 4 firms won't approve a tool without it.

**Implementation**: python-saml2 or authlib library.

### 5.2 Audit Trails

**What**: Log every action (who searched what, who viewed which violation, who exported which report) for compliance audit purposes.

**Why**: Enterprise compliance teams need to prove they performed regulatory horizon scanning. An audit trail of "CCO searched for KYC violations on [date], reviewed [N] results" satisfies this.

### 5.3 Custom Taxonomy Mapping

**What**: Let enterprise customers map our violation taxonomy to their internal categories.

**Why**: A bank's internal GRC system might categorize violations differently. Custom mapping lets them integrate our data into their existing framework without changing their processes.

### 5.4 Webhook / Event Streaming

**What**: Push notifications when new violations are processed.

```
POST https://customer.example.com/webhook
{
    "event": "new_violation",
    "violation_id": 88,
    "regulator": "RBI",
    "entity_name": "XYZ Finance Ltd",
    "violation_type": "BANKING_REGULATORY/KYC_AML_VIOLATION",
    "penalty_inr": 500000
}
```

**Why**: API customers want real-time data, not polling. Webhooks are the standard integration pattern.

### 5.5 Bulk Export

**What**: CSV/Excel download of filtered violations.

**Why**: Compliance teams need to import data into their own tools (Excel, GRC platforms). Every customer will ask for this.

### 5.6 WhatsApp Alerts

**What**: Send violation alerts via WhatsApp Business API.

**Why**: Indian compliance officers live on WhatsApp. Email open rates in India are 15-20%. WhatsApp message read rates are 90%+. This is the highest-impact notification channel.

**Implementation**: WhatsApp Business API via Gupshup or Twilio (both have India pricing). Template messages with violation summaries.

---

## Phase 6: Data Moat Deepening (Year 2)

### 6.1 NCLT/NCLAT Insolvency Cases

**What**: Scrape National Company Law Tribunal cases (insolvency, winding up, oppression & mismanagement).

**Why**: Insolvency data is extremely valuable for credit risk assessment. A company under NCLT proceedings is a major red flag.

**Data source**: eCourts portal (nclt.gov.in).

### 6.2 Indian Kanoon Integration

**What**: Scrape court judgments mentioning regulatory penalties from indiankanoon.org.

**Why**: Appeals of regulatory orders are heard by High Courts and Supreme Court. The judgment often reveals additional context (was the penalty upheld, reduced, or overturned?). This enriches our violation records with outcome data.

### 6.3 Consumer Court Rulings

**What**: Consumer disputes from confonet.nic.in.

**Why**: Opens insurance and consumer goods verticals. High volume of data.

### 6.4 India Compliance Graph

**What**: A linked knowledge graph connecting entities across all regulators:

```
Company A (CIN: U12345...)
  ├── RBI: 3 penalties (₹25L total)
  ├── SEBI: 1 adjudication order
  ├── CCI: Under investigation
  ├── Directors:
  │     ├── Person X → also director at Company B
  │     │     └── Company B: RBI penalty for fraud
  │     └── Person Y → disqualified by MCA
  ├── Group companies:
  │     ├── Company C (subsidiary) → FSSAI violation
  │     └── Company D (associate) → Clean record
  └── MCA status: Active, last AGM: March 2025
```

**Why**: This is the deepest moat. No one else has this linked view. It takes 12+ months of data accumulation and entity resolution to build. A competitor starting then can't catch up for another 12 months.

**Implementation**: Neo4j or PostgreSQL with recursive CTEs. Start with PostgreSQL (simpler); move to Neo4j if graph traversal queries become the bottleneck.

### 6.5 NLP Model Fine-Tuning

**What**: Fine-tune a distilbert-base-uncased classifier on our actual labeled data (accumulated from human reviews over 6+ months).

**Expected improvement**: Violation classification accuracy jumps from ~75% (zero-shot) to ~92% (fine-tuned). Auto-approve rate increases from ~60% to ~85%.

**Training data needed**: 500+ human-reviewed violations (achievable by Month 4-6).

### 6.6 State-Level Regulators

**What**: Scrape state Pollution Control Boards, state Food Safety departments, RTOs.

**Why**: Massive data volume, but fragmented and poorly digitized. This is the hardest data to collect — anyone who does it has a permanent advantage.

**Challenge**: Each state has different websites, formats, languages. Expect 2-3 months per state.

---

## Phase 7: SE Asia Expansion (Year 3-4)

### 7.1 Why SE Asia

| Market | Regulator | Language | Willingness to pay |
|--------|-----------|----------|-------------------|
| **Singapore** | MAS | English | Highest |
| **Indonesia** | OJK | Bahasa Indonesia | Medium |
| **Philippines** | BSP | English | Medium |
| **Thailand** | BOT | Thai | Medium |
| **Vietnam** | SBV | Vietnamese | Lower |

**Singapore first**: English-language regulators, highest ACV per customer, strong rule-of-law environment where compliance data is valued.

### 7.2 Architecture for Multi-Country

The architecture already supports this:

```
config/sources.yaml:
  rbi:
    jurisdiction: INDIA
    ...
  mas:
    jurisdiction: SINGAPORE
    base_url: https://www.mas.gov.sg
    ...
```

Same pipeline: scrape → extract → NLP → validate → store → serve. Different scraper classes for different regulators. Different NLP models for different languages (Bahasa, Thai). Same database schema, same API.

### 7.3 Revenue Impact

SE Asia is what unlocks $10M ARR. India alone caps at ~$4-6M ARR due to low ACV. Singapore MAS customers would pay 5-10x Indian rates ($500-2,000/month per seat).

---

## Phase 8: Platform Integrations (Year 4-5)

### 8.1 ERP Integration

**Tally**: India's dominant accounting software (80%+ market share in SMEs). A Tally plugin that flags vendors/customers with regulatory violations.

**Zoho Books / Zoho CRM**: Indian SaaS giant. Plugin marketplace integration.

**SAP Business One**: For larger enterprises. Embed risk scores in procurement workflows.

### 8.2 GRC Platform Integration

**MetricStream, ServiceNow GRC, Archer**: Enterprise governance, risk, and compliance platforms. Our violation data and risk scores feed into their dashboards.

**Why this matters**: Once embedded in a GRC platform, we become infrastructure. Switching cost is extremely high.

### 8.3 Compliance LLM

**What**: Fine-tune a language model on the largest corpus of Indian regulatory enforcement data.

**Capabilities**:
- "What are the most common KYC violations for NBFCs with AUM > 5000 Cr?"
- "Summarize RBI's enforcement focus areas for Q3 2026"
- "Compare penalty trends for private banks vs cooperative banks"
- Natural language querying of the entire violation database

**Why**: This is the endpoint of the data moat. The model is only as good as the proprietary data it's trained on. Competitors can build a model, but they can't replicate 3+ years of structured, validated, cross-referenced enforcement data.

### 8.4 Data Licensing

**What**: License our structured dataset to existing platforms (Bloomberg Terminal, Refinitiv, Moody's, FactSet).

**Why**: These platforms already have India-focused institutional investors as customers. They need regulatory enforcement data for India but don't have the scraping/NLP infrastructure. We become a data supplier.

**Pricing**: Annual data licenses at $50K-200K/year per platform.

---

## Technical Debt & Improvements Planned

### Near-Term (Next 30 Days)

| Item | Priority | Effort |
|------|----------|--------|
| Add unit tests for penalty_extractor and entity_extractor | HIGH | 2 days |
| Add integration test: scrape 10 known RBI orders, verify end-to-end | HIGH | 1 day |
| Set up structlog JSON logging to file (not just stdout) | MEDIUM | 0.5 day |
| Add /health endpoint that checks DB, Redis, Meilisearch connectivity | MEDIUM | 0.5 day |
| Add error alerting (email when scraper fails 3x consecutively) | MEDIUM | 1 day |

### Medium-Term (Months 2-3)

| Item | Priority | Effort |
|------|----------|--------|
| Switch spaCy from en_core_web_sm to en_core_web_trf (transformer) | HIGH | 0.5 day (just model swap) |
| Add near-duplicate detection (same entity + same date ± 7 days + same amount ± 5%) | HIGH | 1 day |
| Build human review UI (show PDF + extracted fields side by side) | HIGH | 5 days |
| Add Prometheus metrics export for monitoring | MEDIUM | 1 day |
| Set up CI/CD pipeline (GitHub Actions: lint, test, build Docker image) | MEDIUM | 1 day |

### Longer-Term (Months 4-6)

| Item | Priority | Effort |
|------|----------|--------|
| Fine-tune violation classifier on labeled data | HIGH | 3 days |
| Move from MinIO to Cloudflare R2 (free egress) | LOW | 1 day |
| Add GraphQL API alongside REST (for flexible frontend queries) | MEDIUM | 3 days |
| Implement connection pooling (asyncpg pool) for API under load | MEDIUM | 0.5 day |
| Add Redis caching for frequent API queries (stats, popular entities) | MEDIUM | 1 day |

---

## Revenue Projections

```
                 Customers    Avg ACV     MRR          ARR
                 ─────────    ───────     ────         ────
Month 3          10-20        ₹60K        ₹50K-1L      ₹6-12L
Month 6          50-100       ₹80K        ₹3-7L        ₹36-84L
Month 12         100-200      ₹1.2L       ₹10-20L      ₹1.2-2.4Cr
Month 24         200-400      ₹1.5L       ₹25-50L      ₹3-6Cr
Month 36         400-700      ₹2L         ₹65L-1.2Cr   ₹8-14Cr
Month 48         700-1000     ₹2.5L       ₹1.5-2Cr     ₹18-24Cr
Month 60         1000+        ₹3L+        ₹2.5Cr+      ₹30Cr+ ($3.6M+)
```

Add SE Asia for the $10M ARR path:
```
India ARR (Year 5):            ₹30-50 Cr ($3.6-6M)
Singapore + SE Asia ARR:       ₹25-40 Cr ($3-5M)
API / Data licensing ARR:      ₹10-20 Cr ($1.2-2.4M)
────────────────────────────────────────────────
Total potential (Year 5):      ₹65-110 Cr ($8-13M ARR)
```

---

## Risk Checkpoints

### Month 3 — Go/No-Go on SEBI Expansion

| Signal | Action |
|--------|--------|
| 10+ paying RBI customers | ✅ Proceed: build SEBI scraper |
| 3-9 paying customers | ⚠️ Proceed cautiously: focus on product-market fit, more customer interviews |
| 0-2 paying customers | 🔴 Pivot: try different persona (law firms), different pricing (lower), or sell as data feed to Manupatra/SCC Online |

### Month 6 — Go/No-Go on Risk API

| Signal | Action |
|--------|--------|
| 50+ customers + 2 fintech API beta partners | ✅ Proceed: build commercial Risk API |
| 25-49 customers + interest from fintechs | ⚠️ Build MVP API, don't invest in commercial pricing yet |
| < 25 customers | 🔴 This may be a feature, not a product. Consider acqui-hire or data licensing deal |

### Month 12 — Go/No-Go on Enterprise

| Signal | Action |
|--------|--------|
| 100+ customers + ₹10L+ MRR + enterprise inbound | ✅ Hire sales, build enterprise features (SSO, audit, custom taxonomies) |
| 50-99 customers + ₹5-10L MRR | ⚠️ Stay PLG (product-led growth). Enterprise sales is expensive; don't burn cash on it yet |
| < 50 customers | 🔴 Fundamental product-market fit issue. Deep customer development needed |

### Month 18 — Go/No-Go on SE Asia

| Signal | Action |
|--------|--------|
| ₹3Cr+ ARR in India + seed round closed | ✅ Hire Singapore-based BD, build MAS scraper |
| ₹1.5-3Cr ARR + seed pending | ⚠️ Wait for funding. SE Asia is expensive without capital |
| < ₹1.5Cr ARR | 🔴 India isn't working at scale. Fix India before expanding |

---

## Potential Acquirers (Year 3-5)

| Company | Why they'd acquire | Estimated price range |
|---------|-------------------|----------------------|
| **Thomson Reuters** | Fill India regulatory data gap in Westlaw/Practical Law | $20-50M |
| **Wolters Kluwer** | Complement CCH/TeamMate GRC products with India enforcement data | $15-40M |
| **Moody's** | Add regulatory risk intelligence to credit analytics | $30-80M |
| **MSCI** | ESG/governance risk scoring for India-exposed portfolios | $20-50M |
| **Reliance / Jio** | Build Indian enterprise SaaS ecosystem | $10-30M |
| **Info Edge / Naukri** | Diversification into B2B data (they already own Shiksha, 99acres) | $10-25M |

**IPO path**: Possible at ₹100Cr+ ARR ($12M+), but Indian public markets value SaaS differently than US markets. More likely path is acquisition by a global legal/financial data company.

---

## Summary: What Gets Built When

```
NOW          RBI scraper + NLP pipeline + API (DONE)
Month 2      Auth + alerts + payments + dashboard + board reports
Month 3      SEBI scraper + MCA entity resolution
Month 4-5    CCI + IRDAI scrapers + human review UI
Month 6      Risk scoring API + first enterprise features
Month 9      Cross-regulator entity graph + NLP fine-tuning
Month 12     5+ regulators + enterprise (SSO, audit) + WhatsApp alerts
Month 18     NCLT/courts + state regulators + India Compliance Graph
Month 24     SE Asia (Singapore MAS first)
Month 36     ERP integrations + Compliance LLM + data licensing
Month 48+    Full platform: India + SE Asia + API + Enterprise + LLM
```

Each phase is gated by the previous one's traction metrics. We don't build SEBI until RBI has paying customers. We don't build enterprise until we have 50+ mid-market customers. We don't expand to SE Asia until India works at ₹3Cr+ ARR.

**The #1 rule**: Revenue validates the roadmap. If customers aren't paying for Phase N, don't build Phase N+1.
