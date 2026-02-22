# scrapperboi -- Execution Roadmap

## 30-60-90 Day Plan + Beyond

---

## Overview

```
Days 1-30:   FOUNDATION     Build pipeline, scrape RBI, launch newsletter
Days 31-60:  MONETIZE        Paid dashboard, first 10 customers, INR 50K MRR
Days 61-90:  EXPAND          SEBI data, API beta, fundraise-ready
Days 91-180: SCALE           Multi-regulator, enterprise, seed round
Days 181-365: PLATFORM       Full product suite, 100+ customers
```

---

## Days 1-30: Foundation + First Signal

### Week 1: Project Setup + Infrastructure

| Task | Deliverable | Time |
|------|------------|------|
| Project structure | Full directory tree with __init__.py files, config, scrapers, processors, nlp, storage, api, workers | Day 1 |
| Docker Compose | PostgreSQL 16, Redis 7, Meilisearch 1.6, MinIO -- all services running locally | Day 1-2 |
| Database schema | All tables via Alembic migration (regulators, entities, documents, violations, penalties, mca_company_master, review_queue, scrape_runs) | Day 2-3 |
| SQLAlchemy models | storage/db.py with all models matching schema | Day 3 |
| Config system | Pydantic BaseSettings + sources.yaml for per-regulator config | Day 3-4 |
| Base scraper | scrapers/base.py -- AbstractBaseScraper with polite fetching, rate limiting, content hashing, retry logic | Day 4-5 |
| .env.example | All environment variables documented | Day 5 |
| requirements.txt | All dependencies pinned | Day 5 |

**Week 1 checkpoint**: `docker-compose up` starts all services. Database migrated. Base scraper class ready.

### Week 2: RBI Scraper + PDF Processing

| Task | Deliverable | Time |
|------|------------|------|
| RBI scraper | scrapers/rbi.py -- scrape penalty orders from rbi.org.in with ASP.NET VIEWSTATE pagination, discover + fetch all PDFs from 2020 onward | Day 6-8 |
| PDF processor | processors/pdf_processor.py -- PyMuPDF native text extraction with OCR fallback. Classify as native vs scanned. | Day 8-9 |
| OCR engine | processors/ocr.py -- Tesseract tier 1, Google Vision tier 2 (configurable) | Day 9-10 |
| Raw storage | storage/raw_store.py -- save original PDFs to MinIO with content hash as key | Day 10 |
| Entity extraction | nlp/entity_extractor.py -- regex for CIN/PAN + spaCy NER for company/person names | Day 10-11 |
| Penalty extraction | nlp/penalty_extractor.py -- Indian currency format parser (Rs, INR, lakhs, crores, comma-separated Indian numbering) | Day 11-12 |
| Integration test | Scrape 10 known RBI penalty orders end-to-end, verify extracted fields against manual reading | Day 12 |

**Week 2 checkpoint**: Can scrape RBI penalty orders, extract text from PDFs, pull out entity names, CIN numbers, and penalty amounts. 10 test orders verified correct.

### Week 3: NLP Pipeline + Storage + Search

| Task | Deliverable | Time |
|------|------------|------|
| Date normalizer | nlp/date_normalizer.py -- handle dd/mm/yyyy, dd.mm.yyyy, "1st January 2024", classify order date vs violation date | Day 13 |
| Violation classifier | nlp/violation_classifier.py -- zero-shot with BART-MNLI, 3-level taxonomy, top-3 predictions with confidence | Day 13-14 |
| Validators | nlp/validators.py -- format checks (CIN regex, date range, penalty range), cross-reference checks, confidence scoring (weighted average) | Day 14-15 |
| NLP pipeline orchestrator | nlp/pipeline.py -- chain all stages: lang detect -> entity extract -> penalty extract -> date extract -> classify -> validate -> route (auto-approve / review / reject) | Day 15-16 |
| Meilisearch indexing | storage/search.py -- index violations with searchable, filterable, sortable attributes | Day 16-17 |
| Full pipeline run | Scrape ALL RBI penalty orders (2020-present), process through NLP pipeline, store in PostgreSQL, index in Meilisearch | Day 17-18 |
| Minimal dashboard | api/main.py + basic HTML/JS -- search violations, filter by regulator/date/type, view order details with link to original PDF | Day 18-21 |

**Week 3 checkpoint**: 800+ RBI penalty orders scraped, parsed, classified, and searchable. Dashboard shows results. Meilisearch handles typo-tolerant search.

### Week 4: Newsletter + Deploy

| Task | Deliverable | Time |
|------|------------|------|
| Deploy | Docker Compose on Hetzner VPS (4 vCPU, 16GB RAM). HTTPS via Caddy or nginx + Let's Encrypt. | Day 22-23 |
| Newsletter setup | Buttondown or Substack free tier. "This Week in RBI Enforcement" -- first edition summarizing latest penalty orders | Day 23-24 |
| LinkedIn content | 3-4 posts about RBI enforcement trends derived from the data. Target compliance officer communities | Day 24-25 |
| Outreach v1 | DM 50 compliance professionals on LinkedIn with link to newsletter. Join NBFC association WhatsApp groups. | Day 25-28 |
| Celery scheduling | workers/celery_app.py + tasks.py -- daily RBI scrape at 6 AM IST, auto-process new orders | Day 28-30 |

**Day 30 milestones**:
- [x] 800+ RBI penalty orders parsed and searchable
- [x] Live dashboard on public URL
- [x] 200+ newsletter subscribers
- [x] 5+ conversations with compliance officers about willingness to pay
- [x] Daily auto-scraping running

---

## Days 31-60: Monetization + Product Tightening

### Weeks 5-6: Paid Dashboard Launch

| Task | Deliverable |
|------|------------|
| Authentication | Email/password auth with session tokens. No SSO yet. |
| Alert system | Save search criteria, get email notification when new violations match. Daily digest option. |
| Basic analytics | Charts: penalties by quarter, top violation categories, most-penalized entity types. Use Chart.js or Recharts. |
| Pricing page | Starter (INR 5K/mo, 1 user, search + alerts). Professional (INR 15K/mo, 5 users, benchmarking, reports). |
| Payment integration | Razorpay (standard Indian B2B SaaS). Support UPI, cards, net banking. |
| Founding member offer | First 50 customers get annual rate of INR 40K/year (33% discount). |

### Weeks 7-8: Sales + Board Reports

| Task | Deliverable |
|------|------------|
| Outbound sales list | Identify 100 NBFCs (AUM INR 1K-10K Cr). Find CCO/CS names from annual reports (filed with RBI/MCA). |
| Cold email campaign | Personalized emails: "I noticed [NBFC] received an RBI observation regarding [topic] in [year]. We built a tool that tracks all RBI enforcement actions so your compliance team can benchmark against peers." |
| Board report generator | Jinja2 template -> PDF/PPTX. Quarterly enforcement trends relevant to the entity's NBFC category. One-click generation. This justifies the Professional tier. |
| Iteration | Track what pilot customers actually use. Common requests to expect: "Add SEBI data", "WhatsApp alerts", "Export to Excel". |

**Day 60 milestones**:
- [x] 10 paying customers
- [x] INR 50K+ MRR
- [x] 500+ newsletter subscribers
- [x] Board report feature shipped
- [x] Clear signal on SEBI expansion demand

---

## Days 61-90: Scale Preparation

### Weeks 9-10: SEBI + Entity Resolution

| Task | Deliverable |
|------|------------|
| SEBI scraper | scrapers/sebi.py -- enforcement orders from sebi.gov.in. Simple HTML pagination. |
| SEBI taxonomy | Extend violation_types: insider trading, market manipulation, disclosure failure, intermediary violations, takeover code. |
| MCA data load | Download company master CSVs from data.gov.in. Load ~2M records into mca_company_master table. |
| Entity resolver | nlp/entity_resolver.py -- normalize names, exact match, fuzzy match (rapidfuzz, threshold 85) against MCA master. Log resolutions. |
| Cross-regulator entity profiles | Entity page shows violations from both RBI and SEBI. Same CIN links across regulators. |

### Weeks 11-12: API + Fundraise Prep

| Task | Deliverable |
|------|------------|
| Risk scoring API | `GET /api/v1/risk/{cin}` -- returns regulatory risk score (0-100), penalty history, violation severity, peer percentile, trend (improving/deteriorating). |
| API keys + rate limiting | X-API-Key header auth. Per-key rate limits (100/hour free, higher for paid). |
| Fintech beta | Offer API free to 2-3 fintech lending platforms. "Before you lend to a company, check regulatory enforcement history." |
| Metrics dashboard | Internal: MRR, subscriber count, data volume (total documents, violations, entities), API calls, search queries. |
| Fundraising deck | 10-12 slides: problem, solution, traction (MRR, customers, data), market size, moat, team, ask. |
| Investor targeting | Blume Ventures, 3one4 Capital, Kalaari, pi Ventures (India). YC or Antler India application. |

**Day 90 milestones**:
- [x] 25-50 paying customers
- [x] INR 1.5-3L MRR
- [x] SEBI data live
- [x] Entity resolution linking companies across regulators
- [x] API beta with 2-3 fintech partners
- [x] Fundraising deck ready
- [x] First investor conversations started

---

## Days 91-180: Scale

### Months 4-5: Multi-Regulator + Enterprise

| Task | Deliverable |
|------|------------|
| CCI scraper | scrapers/cci.py -- competition orders. Well-structured, year-wise filters. |
| IRDAI scraper | Insurance penalty orders. |
| Enterprise features | SSO/SAML, role-based access, audit trails, custom taxonomy mapping. |
| Enterprise sales | Target 2-3 large banks, 1-2 Big 4 advisory firms. POC-driven (30-60 day free trial). |
| Pricing: Enterprise | INR 10-50L/year. Custom contracts. |

### Month 6: Seed Round

| Metric | Target |
|--------|--------|
| MRR | INR 5-10L |
| Customers | 50-100 |
| Regulators covered | 4+ (RBI, SEBI, CCI, IRDAI) |
| Data volume | 5,000+ enforcement orders, 2,000+ entities |
| API integrations | 5-10 |
| Ask | INR 3-5 Cr at INR 25-40 Cr valuation |

---

## Days 181-365: Platform

### Months 7-9: Data Moat + Product Depth

| Task | Deliverable |
|------|------------|
| NCLT/NCLAT | Insolvency cases via eCourts. |
| Indian Kanoon integration | Court judgments mentioning regulatory penalties. |
| "India Compliance Graph" | Cross-regulator entity graph. Same company -> all regulatory touchpoints -> all directors -> linked companies. |
| Peer benchmarking v2 | "Your NBFC vs all NBFCs in your AUM bracket vs industry average." Quartile rankings. |
| Compliance community | Anonymous forum for CCOs to share how they resolved specific violation types. Stack Overflow for compliance. |

### Months 10-12: Revenue Optimization

| Task | Deliverable |
|------|------------|
| Annual contracts push | Convert monthly to annual (20% discount). Reduce churn. |
| API commercial launch | End beta. Pricing: INR 25K/mo for 5K calls, INR 1L/mo for 50K calls. |
| Board report v2 | Customizable templates. Auto-generate quarterly. Include regulator-specific sections. |
| WhatsApp alerts | Indian compliance officers live on WhatsApp. WhatsApp Business API integration for alerts. |

**Year 1 targets**:
- INR 50L-1.5Cr ARR
- 100+ customers
- RBI + SEBI + CCI + IRDAI coverage
- 10,000+ enforcement orders structured
- Team of 2-4

---

## Year 2-5 Roadmap (High Level)

### Year 2: Enterprise + Seed Growth

- Multi-regulator: add FSSAI, CPCB, DGCA, TRAI
- Enterprise clients: 5-10 (banks + Big 4)
- Revenue: INR 3-6 Cr ARR
- Team: 8-12
- Raise seed round

### Year 3: India Compliance Graph + Series A

- 50+ API integrations
- Linked dataset across all regulators + MCA + courts
- Revenue: INR 10-20 Cr ARR
- Team: 20-30
- Series A

### Year 4: SE Asia Expansion

- Singapore (MAS), Indonesia (OJK), Philippines (BSP), Thailand (BOT)
- Same pipeline architecture, different scrapers
- Singapore first: English-language, highest willingness to pay
- Revenue: INR 30-50 Cr ARR

### Year 5: $10M+ ARR Platform

- Full suite: Compliance SaaS + Enterprise Intelligence + Risk API + SE Asia
- ERP integration: Tally, Zoho Books, SAP Business One
- Compliance LLM: fine-tuned on largest corpus of Indian regulatory data
- Revenue: INR 80Cr+ ARR ($10M+)
- Potential exits: Thomson Reuters, Wolters Kluwer, Moody's, MSCI acquisition. Or IPO path.

---

## Key Hiring Plan

| When | Role | Why |
|------|------|-----|
| Day 1 | Founder (you) | Everything |
| Month 2 | Backend Engineer | Scale scrapers + NLP pipeline. Python, scraping experience preferred. INR 8-15L/year |
| Month 4 | Sales/BD (part-time or fractional) | Outbound to NBFCs. Can be founder-led initially. |
| Month 6 | Full-stack Engineer | Dashboard, board reports, user-facing features. INR 10-18L/year |
| Month 9 | Data/NLP Engineer | Improve extraction accuracy, fine-tune models, entity resolution. INR 12-20L/year |
| Month 12 | Head of Sales | Enterprise sales motion for banks + Big 4. INR 20-30L/year + commission |

---

## Key Metrics to Track

### Product Metrics

| Metric | Day 30 | Day 60 | Day 90 | Month 6 | Year 1 |
|--------|--------|--------|--------|---------|--------|
| Documents scraped | 800+ | 1,200+ | 2,000+ | 5,000+ | 10,000+ |
| Entities tracked | 200+ | 400+ | 800+ | 2,000+ | 5,000+ |
| Extraction accuracy | 80%+ | 85%+ | 90%+ | 92%+ | 95%+ |
| Search queries/day | 10+ | 50+ | 100+ | 500+ | 2,000+ |

### Business Metrics

| Metric | Day 30 | Day 60 | Day 90 | Month 6 | Year 1 |
|--------|--------|--------|--------|---------|--------|
| Newsletter subs | 200+ | 500+ | 1,000+ | 3,000+ | 5,000+ |
| Paying customers | 0 | 10 | 25-50 | 50-100 | 100+ |
| MRR (INR) | 0 | 50K+ | 1.5-3L | 5-10L | 10-15L |
| Churn (monthly) | - | <10% | <8% | <5% | <5% |
| API integrations | 0 | 0 | 2-3 beta | 5-10 | 20+ |

### Infrastructure Costs

| Item | Month 1 | Month 3 | Month 6 | Year 1 |
|------|---------|---------|---------|--------|
| Hetzner VPS | $20/mo | $20/mo | $40/mo | $60/mo |
| Domain + SSL | $15/yr | - | - | $15/yr |
| Google Vision OCR | $0 | $15/mo | $30/mo | $50/mo |
| Email (Buttondown) | $0 | $9/mo | $29/mo | $29/mo |
| Razorpay | 0 | 2% of revenue | 2% of revenue | 2% of revenue |
| **Total** | **~$25/mo** | **~$50/mo** | **~$110/mo** | **~$160/mo** |

---

## Risk Checkpoints

### Day 30 Kill/Pivot Decision

If after 30 days:
- Cannot scrape RBI data reliably -> investigate alternative data access (RTI, partnerships)
- Zero interest from compliance officers -> pivot to law firm persona or PE/VC use case
- PDF extraction accuracy < 70% -> invest more in OCR/parsing before proceeding

### Day 60 Kill/Pivot Decision

If after 60 days:
- 0 paying customers -> the pain is not strong enough at this price. Try: lower price (INR 2K/mo), different persona, or pivot to API-first (sell to fintechs, not compliance teams)
- < 3 paying customers -> product gaps. Intensify customer development. What's missing?

### Day 90 Kill/Pivot Decision

If after 90 days:
- < 10 paying customers AND < INR 1L MRR -> serious product-market fit concern. Consider: is this a feature, not a product? Could this be a data feed sold to existing legal databases (Manupatra, SCC Online) instead of a standalone product?
- 25+ customers + INR 2L+ MRR -> strong signal. Fundraise aggressively.
