# How scrapperboi Works

## End-to-End System Walkthrough

This document traces a single RBI penalty order from the moment it appears on rbi.org.in to the moment a customer queries it through our API. Every component, every decision, every data transformation is explained.

---

## Table of Contents

1. [The Big Picture](#1-the-big-picture)
2. [System Boot — What Starts When](#2-system-boot--what-starts-when)
3. [Step 1: SCRAPE — Finding Documents](#3-step-1-scrape--finding-documents)
4. [Step 2: STORE — Saving Raw Files](#4-step-2-store--saving-raw-files)
5. [Step 3: EXTRACT TEXT — Getting Words From PDFs](#5-step-3-extract-text--getting-words-from-pdfs)
6. [Step 4: UNDERSTAND TEXT — The NLP Pipeline](#6-step-4-understand-text--the-nlp-pipeline)
7. [Step 5: VALIDATE — Trust Scoring](#7-step-5-validate--trust-scoring)
8. [Step 6: SAVE — Writing to Databases](#8-step-6-save--writing-to-databases)
9. [Step 7: SERVE — Answering Queries](#9-step-7-serve--answering-queries)
10. [The Daily Cycle](#10-the-daily-cycle)
11. [Data Flow Between Components](#11-data-flow-between-components)
12. [Current Scope](#12-current-scope)
13. [Technology Choices — Why These Tools](#13-technology-choices--why-these-tools)

---

## 1. The Big Picture

The entire system is six steps:

```
SCRAPE → STORE → EXTRACT TEXT → UNDERSTAND TEXT → VALIDATE → SAVE → SERVE
```

In plain terms:

1. **SCRAPE**: Go to rbi.org.in, find penalty order PDFs, download them
2. **STORE**: Save the raw PDF in MinIO (object storage) so we always have the original
3. **EXTRACT TEXT**: Pull the actual words out of the PDF (either native text or OCR for scanned docs)
4. **UNDERSTAND TEXT**: Use NLP to figure out WHO was penalized, HOW MUCH, FOR WHAT, and WHEN
5. **VALIDATE**: Score our confidence in the extraction. Auto-approve good ones, flag uncertain ones for human review
6. **SAVE**: Write structured data to PostgreSQL, index in Meilisearch for search
7. **SERVE**: Customers query the REST API to search, filter, and analyze violations

---

## 2. System Boot — What Starts When

When `docker-compose up` runs, six services start on a single VPS:

```
┌─────────────────────────────────────────────────────────┐
│                    Your VPS (16GB RAM)                   │
│                                                         │
│  ┌──────────┐  ┌───────┐  ┌────────────┐  ┌──────────┐ │
│  │PostgreSQL│  │ Redis │  │Meilisearch │  │  MinIO   │ │
│  │  (4GB)   │  │(256MB)│  │  (512MB)   │  │ (512MB)  │ │
│  │          │  │       │  │            │  │          │ │
│  │ All      │  │Message│  │ Search     │  │ Raw PDF  │ │
│  │ tables,  │  │queue  │  │ index for  │  │ storage  │ │
│  │ data,    │  │broker │  │ fast typo- │  │ (S3-     │ │
│  │ indexes  │  │between│  │ tolerant   │  │ compat.) │ │
│  │          │  │Celery │  │ search     │  │          │ │
│  │          │  │& Beat │  │            │  │          │ │
│  └──────────┘  └───────┘  └────────────┘  └──────────┘ │
│                                                         │
│  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │   FastAPI (2GB)   │  │   Celery Worker (4GB)        │ │
│  │                   │  │                              │ │
│  │  Handles all API  │  │  Runs the scrapers,          │ │
│  │  requests from    │  │  PDF processing, and         │ │
│  │  customers        │  │  NLP pipeline                │ │
│  └──────────────────┘  └──────────────────────────────┘ │
│                                                         │
│  ┌──────────────────┐                                   │
│  │   Celery Beat     │                                  │
│  │                   │                                  │
│  │  The alarm clock. │                                  │
│  │  At 6:00 AM IST   │                                  │
│  │  every day, tells  │                                  │
│  │  the Worker to     │                                  │
│  │  start scraping.   │                                  │
│  └──────────────────┘                                   │
└─────────────────────────────────────────────────────────┘
```

### What each service does:

| Service | Role | Why it exists |
|---------|------|---------------|
| **PostgreSQL** | Source of truth. Stores all structured data: entities, violations, penalties, documents | Relational data with complex queries (joins, aggregations, filtering) |
| **Redis** | Message broker. Celery Beat puts "run scraper" messages in, Worker picks them up | Lightweight queue. Also available for API caching later |
| **Meilisearch** | Search index. Makes text search fast and typo-tolerant | PostgreSQL's LIKE is slow for text search. Meilisearch handles "HDFC Bnk" → "HDFC Bank" |
| **MinIO** | Object storage. Holds raw PDF files | We need originals for reprocessing when NLP models improve |
| **FastAPI** | HTTP API server. Handles customer requests | Serves the REST API that customers query |
| **Celery Worker** | Background processor. Runs scrapers and NLP pipeline | Heavy processing shouldn't block the API |
| **Celery Beat** | Scheduler. Triggers scrapes on a cron schedule | Automated daily scraping without manual intervention |

---

## 3. Step 1: SCRAPE — Finding Documents

**File**: `scrapers/rbi.py` inheriting from `scrapers/base.py`

### 3.1 What triggers a scrape

Every day at 6:00 AM IST, Celery Beat drops a message into Redis:

```
Message: {"task": "workers.tasks.run_scraper", "args": ["rbi"]}
```

The Celery Worker picks this up and starts the RBI scraper.

### 3.2 Loading regulator config

The worker reads `config/sources.yaml`:

```yaml
rbi:
  code: RBI
  base_url: https://www.rbi.org.in
  min_delay_sec: 3      # Wait 3-7 seconds between requests
  max_delay_sec: 7      # Randomized to look like a human
  max_concurrent: 1     # Only 1 connection at a time
  respect_robots_txt: true
  schedule: "0 6 * * *" # Daily at 6 AM
  enabled: true          # This is the only enabled scraper right now
```

### 3.3 The ASP.NET challenge

RBI's website (rbi.org.in) is built on ASP.NET WebForms — a server-side framework from the 2000s. When you click "Next Page" in a browser, it doesn't change the URL. Instead, the browser sends a hidden form field called `__VIEWSTATE` — a giant encrypted blob telling the server what page you want.

Most scrapers would need a full browser (Playwright/Selenium) to handle this. We replay the VIEWSTATE directly with HTTP POST requests, saving 200-500MB of RAM:

```
How a browser does it:              How we do it:
┌──────────────┐                    ┌──────────────┐
│ Launch Chrome │ (200MB RAM)       │ httpx POST   │ (10MB RAM)
│ Render page   │                   │ with form    │
│ Click "Next"  │                   │ data         │
│ Wait for JS   │                   │              │
│ Read DOM      │                   │              │
└──────────────┘                    └──────────────┘
```

### 3.4 Discovery process step by step

```
1. GET rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx
   └── Parse HTML with BeautifulSoup
   └── Find all <a> tags containing "penalty", "fine", "monetary"
   └── Extract the __VIEWSTATE hidden field

2. POST back with __VIEWSTATE + "Page$2" to get next page
   └── Wait 3-7 seconds (random delay — politeness)
   └── Parse page 2, collect more links
   └── Repeat for pages 3, 4, 5...

3. Also check rbi.org.in/Scripts/Penaltyorders.aspx
   └── This is RBI's dedicated penalty page (separate from press releases)
   └── Same parsing logic

4. Merge and deduplicate all discovered URLs
   └── Remove duplicates by URL
   └── Result: list of ~200-400 penalty order URLs
```

### 3.5 Politeness — why we wait between requests

Government websites have limited server capacity. If we send 100 requests per second, we could:
- Crash the site (affecting real users)
- Get our IP blocked
- Potentially face legal issues

Our politeness rules:
- **1 concurrent connection** per government domain
- **3-7 second random delay** between requests (looks like human browsing)
- **Respect robots.txt** (parse what's allowed/blocked)
- **Identify ourselves** in User-Agent: `ScrapperBoi/1.0; +https://scrapperboi.in/bot`
- **Run at 6 AM IST** (off-peak hours for government sites)

### 3.6 Fetching each document

For every discovered link:

```
Link: "Penalty on XYZ Finance Ltd for KYC violations"
  │
  ├── Is it a direct PDF link?
  │     YES → Download the PDF bytes directly
  │
  └── Is it an HTML press release page?
        YES → Fetch the page
              → Look for PDF links within the page
              → If found, download the linked PDF
              → If no PDF, use the HTML content itself
```

For each downloaded file:
- Compute **SHA-256 hash** of the raw bytes
- Check if this hash already exists in the `documents` table
- If it exists → **skip** (already processed, deduplication)
- If new → proceed to Step 2

**Output**: A list of `ScrapedDocument` objects containing raw bytes, source URL, content hash, and title.

---

## 4. Step 2: STORE — Saving Raw Files

**File**: `storage/raw_store.py`

Before any processing, the original PDF is saved to MinIO:

```
Raw PDF bytes (content hash: a3f2b7c9e8d1...4567)
    │
    ▼
MinIO stores at: raw/a3f2/a3f2b7c9e8d1...4567.pdf
```

The path uses the first 4 chars of the hash as a directory prefix. This prevents any single directory from having millions of files (filesystem performance issue).

A `Document` record is also created in PostgreSQL:

```
documents table:
┌────┬───────────────────────────┬──────────────┬──────────┬────────────┐
│ id │ source_url                │ content_hash │ doc_type │ status     │
├────┼───────────────────────────┼──────────────┼──────────┼────────────┤
│ 42 │ rbi.org.in/.../xyz.pdf    │ a3f2b7c9...  │ PDF      │ pending    │
└────┴───────────────────────────┴──────────────┴──────────┴────────────┘
```

**Why store raw files?** NLP models improve over time. In 3 months, when we fine-tune a better violation classifier, we can reprocess every document from the original PDF. If we only stored extracted text, we'd lose layout information, images, and formatting that might help extraction.

---

## 5. Step 3: EXTRACT TEXT — Getting Words From PDFs

**File**: `processors/pdf_processor.py` and `processors/ocr.py`

### 5.1 The decision tree

Not all PDFs are the same. Some were created digitally (Word → PDF). Others are scanned paper documents (photographed pages). The extraction strategy differs:

```
PDF bytes arrive
    │
    ▼
PyMuPDF opens the PDF
    │
    ▼
For each page, try native text extraction: page.get_text()
    │
    ├── Got 100+ characters of text per page?
    │       │
    │       YES → This is a NATIVE TEXT PDF
    │             Text extraction is instant and free
    │             Accuracy: ~99%
    │             Used for: Most RBI and SEBI orders
    │
    └── Got < 100 characters per page?
            │
            This is a SCANNED PDF (photograph of paper)
            │
            ▼
        Convert each page to a 300 DPI image
            │
            ▼
        Run Tesseract OCR
            │
            ├── Average word confidence >= 60%?
            │       │
            │       YES → Tesseract output is good enough
            │             Cost: Free
            │             Accuracy: ~85% for English
            │
            └── Confidence < 60%?
                    │
                    The text is garbled (common with Hindi/regional docs)
                    │
                    ▼
                Send image to Google Cloud Vision API
                    │
                    Cost: $0.0015 per page (~$1.50 per 1000 pages)
                    Accuracy: ~95% for Indic scripts
                    │
                    ▼
                Use Vision API's text
```

### 5.2 Why 100 characters as the threshold?

A real page of text has thousands of characters. A scanned page might produce a few garbled characters from watermarks or page numbers when native extraction is attempted. 100 characters is the empirical threshold — if PyMuPDF extracts fewer than 100 chars from a page, it's almost certainly a scanned image, not real text.

### 5.3 Why 60% OCR confidence as the Tesseract threshold?

Tesseract returns per-word confidence scores (0-100). Below 60% average:
- English text with artifacts → some words garbled, but fixable
- Hindi/Marathi/Tamil text → Tesseract's Indic models are weak, output is unusable
- Poor scan quality → too many errors for reliable extraction

At 60%+, Tesseract's output is good enough for our NLP pipeline to work with.

### 5.4 Concrete example

An RBI penalty order against a Rajasthan-based NBFC:

| Page | Content | Native text? | Method used | Cost |
|------|---------|-------------|-------------|------|
| 1 | English header + Hindi body (scanned) | No (43 chars) | Google Vision | $0.0015 |
| 2 | English penalty details (digital) | Yes (2,847 chars) | PyMuPDF native | Free |
| 3 | Hindi legal provisions (scanned) | No (12 chars) | Google Vision | $0.0015 |

Total cost for this document: $0.003. Most RBI orders are fully digital, costing $0.

### 5.5 For HTML documents

Some press releases are HTML, not PDF. For these:

```python
soup = BeautifulSoup(html_content, "lxml")
# Remove script, style, nav, header, footer tags
text = soup.get_text(separator="\n", strip=True)
```

**Output of Step 3**: A dict containing:

```python
{
    "page_count": 3,
    "extraction_method": "ocr",     # or "native"
    "full_text": "Reserve Bank of India... penalty of Rs. 5,00,000...",
    "pages": [
        {"page_num": 1, "text": "...", "method": "ocr_gcloud"},
        {"page_num": 2, "text": "...", "method": "native"},
        {"page_num": 3, "text": "...", "method": "ocr_gcloud"},
    ]
}
```

---

## 6. Step 4: UNDERSTAND TEXT — The NLP Pipeline

**File**: `nlp/pipeline.py` orchestrating all NLP modules

This is the brain of the system. It takes raw text and produces structured data. Think of it as 6 specialists examining the same document:

```
                        Raw Text
                           │
        ┌──────────────────┼──────────────────────┐
        ▼                  ▼                      ▼
 SPECIALIST 1       SPECIALIST 2           SPECIALIST 3
 "What language?"   "Who's mentioned?"     "How much was the fine?"
 (language_detector) (entity_extractor)     (penalty_extractor)
        │                  │                      │
        │           ┌──────┼──────┐               │
        │           ▼      ▼      ▼               │
        │       Companies People CIN/PAN          │
        │       (spaCy)  (spaCy) (regex)          │
        │                                         │
        ▼                  ▼                      ▼
 SPECIALIST 4       SPECIALIST 5           Results merged
 "When did this     "What type of
  happen?"           violation?"
 (date_normalizer)  (violation_classifier)
        │                  │
        ▼                  ▼
 SPECIALIST 6       Severity determined
 "Match to MCA
  records?"
 (entity_resolver)
        │
        └──────────┬───────┘
                   ▼
        CONFIDENCE SCORING
                   │
                   ▼
        ROUTE: approve / review / reject
```

### 6.1 Language Detection

**File**: `processors/language_detector.py`

```
Input:  "Reserve Bank of India imposed a penalty..."
Output: ("en", 0.97)  → English, 97% confident

Input:  "भारतीय रिज़र्व बैंक ने जुर्माना लगाया..."
Output: ("hi", 0.94)  → Hindi, 94% confident
```

Uses Facebook's fasttext language ID model (176 languages, runs in microseconds). The detected language determines which NER model to use next.

### 6.2 Entity Extraction

**File**: `nlp/entity_extractor.py`

Three extraction strategies run on the same text:

**Strategy 1: Regex for structured identifiers (language-independent)**

```
CIN pattern: [A-Z]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}
  "U65990MH2010PLC123456" → MATCH ✓
  (21-character code uniquely identifying every Indian company)

PAN pattern: [A-Z]{5}\d{4}[A-Z]
  "AABCX1234Z" → MATCH ✓

GSTIN pattern: \d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]
  "27AABCX1234Z1ZP" → MATCH ✓
```

These are exact patterns — no ML needed, no ambiguity. If a CIN is found in the text, we know exactly which company.

**Strategy 2: spaCy NER for English entity names**

```python
text = "RBI imposed a penalty on HDFC Bank Limited for violations of..."

# spaCy identifies:
#   "HDFC Bank Limited" → ORG (organization)
#   "Shri Rajesh Kumar"  → PERSON (if director named)
```

spaCy's model was trained on millions of English documents. It recognizes organization names, person names, locations, etc.

**Strategy 3: ai4bharat/IndicNER for Hindi/regional entity names**

Used only when language is detected as Hindi, Marathi, Bengali, Tamil, Telugu, etc.

**Filtering**: The system removes regulator names from results. We want the penalized entity ("HDFC Bank"), not the penalizer ("Reserve Bank of India"). A blocklist of known regulator names handles this.

### 6.3 Penalty Amount Extraction

**File**: `nlp/penalty_extractor.py`

Indian documents express money in uniquely complex ways. The extractor handles all of them:

```
Input text contains:          Parsed as:
────────────────────          ──────────
"Rs. 5,00,000"                ₹ 5,00,000    (Indian comma format: 5 lakh)
"Rs. 5 lakh"                  ₹ 5,00,000    (word multiplier)
"INR 2.5 crores"              ₹ 2,50,00,000 (decimal + multiplier)
"Rs.50,000/-"                 ₹ 50,000      (trailing slash-dash)
"penalty of Rs. 25 lac"       ₹ 25,00,000   ("lac" = "lakh" variant)
"monetary penalty of Rs.1 Cr" ₹ 1,00,00,000 ("Cr" = crore abbreviation)
```

The multiplier map:

```
lakh / lakhs / lac / lacs  → × 1,00,000
crore / crores / cr        → × 1,00,00,000
thousand                   → × 1,000
million                    → × 10,00,000
```

**Sanity check**: If a matched amount is below Rs 1,000 or above Rs 500 crore, it's probably a misparse (phone number, financial year, section number). Those get discarded.

**Deduplication**: The same penalty is often mentioned multiple times in a document ("RBI imposed Rs. 5 lakh... the penalty of Rs. 5,00,000..."). The extractor deduplicates by amount value.

### 6.4 Date Extraction and Classification

**File**: `nlp/date_normalizer.py`

Indian documents use DD/MM/YYYY format (not American MM/DD/YYYY). The parser handles this with `dayfirst=True`:

```
"01.03.2025"       → 2025-03-01  (March 1, not January 3)
"1st March 2025"   → 2025-03-01
"01/03/2025"       → 2025-03-01
"15 Jan 2025"      → 2025-01-15
```

**But which date is which?** A penalty order mentions multiple dates. The classifier looks at surrounding text (150 characters before the date):

```
"order dated 01.03.2025"
  Keywords: "order dated", "pronounced on", "passed on"
  → This is the ORDER DATE (when the penalty was officially imposed)

"during the period April 2023 to March 2024"
  Keywords: "during the period", "inspection on", "audit for"
  → This is the VIOLATION PERIOD (when the bad behavior happened)
```

**Fallback**: If no order date is identified by context, the latest date in the document is assumed to be the order date (because penalty orders are dated at the end).

### 6.5 Violation Type Classification

**File**: `nlp/violation_classifier.py`

Given the text, what type of violation is this? The system uses a 3-level taxonomy:

```
Level 1 (Domain):    BANKING_REGULATORY
Level 2 (Category):  KYC_AML_VIOLATION
Level 3 (Specific):  "Failure to verify PAN of borrowers" (from raw text)
```

**How classification works on Day 1 (zero training data):**

Zero-shot classification with facebook/bart-large-mnli. This model was trained on textual entailment — "does text A imply text B?"

```
Question the model answers:
  "Does 'failure to comply with KYC norms and AML guidelines'
   entail 'KYC or anti-money laundering violation'?"

Answer: Yes, with 89% confidence

Also checked:
  "Does it entail 'lending norms violation'?"        → 12% confidence
  "Does it entail 'insider trading'?"                → 3% confidence
  "Does it entail 'food adulteration'?"              → 0.1% confidence
```

Top prediction wins. The top 3 predictions are stored for transparency.

**Fallback if ML model is unavailable**: Keyword-based matching. Count how many KYC-related keywords ("kyc", "anti-money laundering", "customer due diligence") appear in the text. Category with most keyword hits wins. Less accurate (~60%) but the pipeline never breaks.

**Severity determination**: Based on violation type + penalty amount:

```
Insider trading + Rs 5 crore+     → CRITICAL
Any violation + Rs 5 crore+       → CRITICAL
Any violation + Rs 1-5 crore      → HIGH
Any violation + Rs 10 lakh-1 crore → MEDIUM
Everything else                    → LOW
```

### 6.6 Entity Resolution

**File**: `nlp/entity_resolver.py`

We have a company name ("HDFC Bank Limited") from spaCy. Now we link it to the official MCA (Ministry of Corporate Affairs) record to get the CIN.

The resolver loads ~2 million company records from the `mca_company_master` table:

```
Step 1: NORMALIZE the extracted name
  "HDFC Bank Limited" → "HDFC BANK"
  (strip "LIMITED", "PVT LTD", "PRIVATE LIMITED", uppercase, remove punctuation)

Step 2: TRY EXACT MATCH
  "HDFC BANK" in MCA records?
  → YES → CIN: L65920MH1994PLC080618, confidence: 1.0

Step 3 (if exact fails): FUZZY MATCH
  "XYZ Finannce" → compare against 2 million names
  → Best match: "XYZ FINANCE" (token_sort_ratio score: 91/100)
  → CIN: U65990RJ2015PTC123456, confidence: 0.91
```

**Why token_sort_ratio?** It sorts words alphabetically before comparing:
- "XYZ FINANCE PRIVATE LIMITED" vs "PRIVATE LIMITED XYZ FINANCE" → score: 100
- Word order doesn't matter. This is critical because company names appear in different orders across documents.

**Threshold: 85**. Below 85, the match is unreliable and the entity goes to human review.

### 6.7 Summary Generation

After all extraction, a one-line factual summary is generated:

```
"RBI imposed a penalty of INR 5.00 lakh on HDFC Bank Limited
 for KYC or anti-money laundering violation (order dated 2025-03-01)."
```

This summary is always factual, neutral, and links directly to the original order. No editorializing — this is important for defamation risk.

---

## 7. Step 5: VALIDATE — Trust Scoring

**File**: `nlp/validators.py`

### 7.1 Sanity checks on every field

```
CHECK 1: CIN format valid?
  "U65990MH2010PLC123456" matches regex? → ✅ (confidence: 1.0)

CHECK 2: Penalty amount in reasonable range?
  Rs. 5,00,000 between Rs 1,000 and Rs 500 crore? → ✅ (confidence: 0.9)

CHECK 3: Date makes sense?
  2025-03-01 between 1990 and today+30 days? → ✅ (confidence: 0.95)

CHECK 4: Company name reasonable length?
  "HDFC Bank Limited" is 18 chars (between 3 and 200)? → ✅ (confidence: 0.8)

CHECK 5: At least one entity found?
  Yes, found "HDFC Bank Limited" → ✅ (confidence: 0.9)
```

### 7.2 Overall confidence — weighted average

Each field contributes to the overall score based on business importance:

```
Field                  Confidence  ×  Weight  =  Contribution
─────                  ──────────     ──────     ────────────
Entity name            0.85       ×   0.30   =   0.255
CIN resolution         1.00       ×   0.15   =   0.150
Violation type         0.89       ×   0.20   =   0.178
Penalty amount         0.90       ×   0.20   =   0.180
Date                   0.95       ×   0.15   =   0.143
                                       ────
                        Overall:       0.906 (90.6%)
```

**Why these weights?**

| Field | Weight | Reasoning |
|-------|--------|-----------|
| Entity name | 30% | If you don't know WHO was penalized, the record is useless |
| Penalty amount | 20% | The most searched/filtered field by customers |
| Violation type | 20% | Drives taxonomy, analytics, and board reports |
| CIN resolution | 15% | Links the entity across regulators and MCA records |
| Date | 15% | Important but rarely wrong (dates are the easiest to extract) |

### 7.3 Three-tier routing

```
Confidence >= 0.85    →   AUTO-APPROVE
                          Written directly to database
                          No human review needed
                          Expected: ~60% of documents on Day 1, ~85% by Month 3

0.30 <= Confidence < 0.85  →   HUMAN REVIEW QUEUE
                               Flagged for manual verification
                               Human sees: original PDF + extracted fields side-by-side
                               Human can: approve, edit+approve, or reject
                               Expected: ~35% of documents initially

Confidence < 0.30     →   REJECT
                          Not written to the violations table
                          Logged for debugging
                          Expected: ~5% (garbled OCR, non-penalty documents)
```

**Why these thresholds?**

- **0.85 for auto-approve**: At this level, extractions are consistently accurate. False approval rate < 5%. Acceptable for a compliance tool.
- **0.30 for rejection**: Below this, the extraction is essentially random. Not worth human review time.
- **The middle band (0.30-0.85)**: Uncertain. A human can quickly verify by glancing at the original PDF. Their corrections feed back into model improvement.

---

## 8. Step 6: SAVE — Writing to Databases

**File**: `workers/tasks.py` (the `_scrape_and_process` function)

### 8.1 PostgreSQL — structured data

Three records are created for each processed document:

```
1. ENTITY (if new)
   ┌──────────────────────────────────────────────────────────┐
   │ entities table                                           │
   │ id: 15                                                   │
   │ entity_type: "NBFC"                                      │
   │ entity_name: "HDFC Bank Limited"                         │
   │ cin: "L65920MH1994PLC080618"                             │
   └──────────────────────────────────────────────────────────┘

2. VIOLATION
   ┌──────────────────────────────────────────────────────────┐
   │ violations table                                         │
   │ id: 88                                                   │
   │ document_id: 42                                          │
   │ regulator_id: 1 (RBI)                                    │
   │ entity_id: 15                                            │
   │ order_date: 2025-03-01                                   │
   │ violation_category: "BANKING_REGULATORY"                 │
   │ violation_subtype: "KYC_AML_VIOLATION"                   │
   │ severity: "MEDIUM"                                       │
   │ summary: "RBI imposed a penalty of INR 5.00 lakh..."    │
   │ extraction_confidence: 0.906                             │
   │ review_status: "auto_approved"                           │
   └──────────────────────────────────────────────────────────┘

3. PENALTY
   ┌──────────────────────────────────────────────────────────┐
   │ penalties table                                          │
   │ id: 201                                                  │
   │ violation_id: 88                                         │
   │ penalty_type: "MONETARY"                                 │
   │ amount_inr: 500000.00                                    │
   │ amount_raw_text: "Rs. 5,00,000"                          │
   └──────────────────────────────────────────────────────────┘
```

### 8.2 Meilisearch — search index

Simultaneously, the violation is indexed for fast search:

```json
{
    "id": 88,
    "entity_name": "HDFC Bank Limited",
    "cin": "L65920MH1994PLC080618",
    "regulator_code": "RBI",
    "violation_category": "BANKING_REGULATORY",
    "violation_subtype": "KYC_AML_VIOLATION",
    "severity": "MEDIUM",
    "summary": "RBI imposed a penalty of INR 5.00 lakh on HDFC Bank Limited...",
    "order_date": "2025-03-01",
    "penalty_amount_inr": 500000
}
```

Meilisearch makes this searchable with typo tolerance. Searching "HDFC Bnk" matches "HDFC Bank".

### 8.3 Document status update

The document record is updated from `pending` to `completed`:

```sql
UPDATE documents SET processing_status = 'completed', processed_at = NOW()
WHERE id = 42;
```

---

## 9. Step 7: SERVE — Answering Queries

**Files**: `api/main.py` and `api/routers/*.py`

### 9.1 Example queries a customer can make

**"Show me all KYC violations by RBI in the last year"**

```
GET /api/v1/violations?regulator=RBI
                      &violation_type=BANKING_REGULATORY/KYC_AML_VIOLATION
                      &date_from=2024-03-01

→ Hits PostgreSQL with a filtered JOIN query
→ Returns paginated JSON with violation details
```

**"Search for HDFC" (even with a typo: "HDFC Bnk")**

```
GET /api/v1/search?q=HDFC%20Bnk

→ Hits Meilisearch (not PostgreSQL)
→ Meilisearch's typo tolerance: "Bnk" matches "Bank" (edit distance = 1)
→ Returns matching violations with relevance ranking
```

**"Is this company a repeat offender?"**

```
GET /api/v1/entities/15

→ Returns entity profile with ALL violations:
{
    "entity_name": "HDFC Bank Limited",
    "summary": {
        "total_violations": 7,
        "total_penalty_inr": 35000000,
        "first_violation": "2019-06-15",
        "latest_violation": "2025-03-01"
    },
    "violations": [...]
}
```

**"Who are the biggest repeat offenders?"**

```
GET /api/v1/recidivists?min_violations=3&regulator=RBI

→ Runs aggregation query grouping by entity
→ Returns entities with 3+ violations, sorted by count
```

**"How are penalties trending?"**

```
GET /api/v1/stats/penalties-by-quarter?regulator=RBI

→ Returns quarterly aggregates:
  Q1 2025: 45 violations, total Rs 12.5 crore, avg Rs 27.8 lakh
  Q4 2024: 38 violations, total Rs 9.2 crore, avg Rs 24.2 lakh
  ...
```

### 9.2 Two databases, two purposes

| Query type | Database used | Why |
|-----------|---------------|-----|
| Filter by exact fields (regulator, date range, violation type) | PostgreSQL | SQL is perfect for relational filtering with JOINs |
| Full-text search ("HDFC Bank KYC violation") | Meilisearch | Typo tolerance, relevance ranking, sub-millisecond response |
| Aggregations (total by quarter, top violators) | PostgreSQL | SQL GROUP BY with SUM/COUNT is the right tool |
| Entity profiles (all violations for one entity) | PostgreSQL | JOIN violations + penalties + regulators for complete picture |

---

## 10. The Daily Cycle

What happens every 24 hours, automatically:

```
6:00 AM IST
    │
    ▼
Celery Beat drops message into Redis: "run RBI scraper"
    │
    ▼
Celery Worker picks up the message
    │
    ▼
RBI Scraper visits rbi.org.in
    │
    ├── Found 3 new PDFs (hash doesn't exist in database)
    ├── Found 197 existing PDFs (hash matches existing → SKIP)
    │
    ▼
For each of the 3 new PDFs:
    │
    ├── Save raw PDF to MinIO
    ├── Extract text (PyMuPDF native or OCR fallback)
    ├── Run NLP pipeline:
    │     ├── Detect language
    │     ├── Extract entities (companies, CIN, PAN)
    │     ├── Extract penalty amounts
    │     ├── Extract and classify dates
    │     ├── Classify violation type
    │     ├── Resolve entity against MCA records
    │     └── Score confidence
    ├── Route: auto-approve (2 docs) / review queue (1 doc)
    ├── Write to PostgreSQL
    ├── Index in Meilisearch
    │
    ▼
Log scrape run:
    "RBI scrape complete: 200 found, 3 new, 0 failed"
    │
    ▼
Done. System sleeps until tomorrow 6:00 AM.

Total time: ~15-30 minutes (mostly waiting for polite delays)
Total cost: ~$0.01 (a few OCR pages at most)
```

---

## 11. Data Flow Between Components

```
┌─────────────┐     ┌──────────┐     ┌──────────────┐
│  RBI Website │────▶│ Scraper  │────▶│    MinIO      │
│ (rbi.org.in) │     │(httpx +  │     │ (raw PDFs,   │
│              │     │ BS4)     │     │  never deleted)│
└─────────────┘     └────┬─────┘     └──────────────┘
                         │
                    raw bytes
                         │
                         ▼
                  ┌──────────────┐
                  │PDF Processor │
                  │              │
                  │ PyMuPDF for  │
                  │ native text  │
                  │              │
                  │ Tesseract    │
                  │ for scanned  │
                  │ English docs │
                  │              │
                  │ Google Vision│
                  │ for scanned  │
                  │ Hindi docs   │
                  └──────┬───────┘
                         │
                  extracted text
                         │
                         ▼
                  ┌──────────────┐
                  │ NLP Pipeline │
                  │              │
                  │ 1. Language  │
                  │ 2. Entities  │
                  │ 3. Penalties │
                  │ 4. Dates     │
                  │ 5. Classify  │
                  │ 6. Resolve   │
                  │ 7. Validate  │
                  └──────┬───────┘
                         │
                  structured data
                         │
              ┌──────────┼───────────┐
              ▼                      ▼
       ┌────────────┐        ┌────────────┐
       │ PostgreSQL  │        │Meilisearch │
       │             │        │            │
       │ Source of   │        │ Search     │
       │ truth.      │        │ replica.   │
       │ All tables, │        │ Fast,      │
       │ all JOINs,  │        │ typo-      │
       │ all         │        │ tolerant.  │
       │ analytics.  │        │            │
       └──────┬─────┘        └──────┬─────┘
              │                      │
              └──────────┬───────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │   FastAPI    │
                  │   REST API   │
                  │              │
                  │ /violations  │
                  │ /entities    │
                  │ /search      │
                  │ /stats       │
                  │ /recidivists │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  Customer    │
                  │              │
                  │ Dashboard    │
                  │ API client   │
                  │ Newsletter   │
                  └──────────────┘
```

---

## 12. Current Scope

### What we scrape RIGHT NOW

| Source | Status | Scraper file |
|--------|--------|-------------|
| **RBI** (Reserve Bank of India) | **ACTIVE** | `scrapers/rbi.py` |
| SEBI | Config exists, scraper disabled | `enabled: false` in sources.yaml |
| CCI | Config exists, scraper disabled | `enabled: false` |
| CPCB | Config exists, scraper disabled | `enabled: false` |
| IRDAI | Config exists, scraper disabled | `enabled: false` |
| Indian Kanoon | Config exists, scraper disabled | `enabled: false` |

### What data we extract

| Field | Extraction method | Current accuracy |
|-------|------------------|-----------------|
| Company name | spaCy NER (ORG label) | ~85% |
| CIN number | Regex pattern | ~99% (when present) |
| PAN number | Regex pattern | ~99% (when present) |
| Penalty amount | Regex + multiplier map | ~90% |
| Order date | Regex + context classification | ~85% |
| Violation type | Zero-shot classification (BART-MNLI) | ~75% |
| Entity resolution (CIN) | Fuzzy match vs MCA master | ~80% (depends on data loaded) |

### What the API serves

| Endpoint | What it returns |
|----------|----------------|
| `GET /api/v1/violations` | Paginated, filtered violations |
| `GET /api/v1/violations/{id}` | Full violation with document + entity + penalties |
| `GET /api/v1/entities/{id}` | Entity profile with all violations |
| `GET /api/v1/entities/{id}/timeline` | Chronological violation timeline |
| `GET /api/v1/search?q=...` | Typo-tolerant full-text search |
| `GET /api/v1/stats/overview` | Total violations, entities, penalties |
| `GET /api/v1/stats/regulators` | Stats grouped by regulator |
| `GET /api/v1/stats/violations-by-type` | Stats grouped by violation category |
| `GET /api/v1/stats/penalties-by-quarter` | Quarterly penalty trends |
| `GET /api/v1/recidivists` | Repeat offenders |
| `GET /health` | System health check |

---

## 13. Technology Choices — Why These Tools

### Why each tool was chosen over alternatives

| Component | Tool chosen | Alternative considered | Why this one wins |
|-----------|------------|----------------------|-------------------|
| HTTP client | **httpx** | requests, aiohttp | Async, HTTP/2, cleaner API than aiohttp |
| HTML parsing | **BeautifulSoup + lxml** | parsel, selectolax | Mature, everyone knows it, lxml backend is fast |
| PDF text | **PyMuPDF** | pdfplumber, pdfminer, Tika | 10-100x faster, no JVM (Tika), handles images too |
| OCR | **Tesseract → Google Vision** | AWS Textract, Azure | Tesseract is free; Vision is best for Indic scripts and cheaper than Textract |
| English NER | **spaCy** | HuggingFace, Stanza | Loads once, runs in milliseconds; HF models are 5-10x slower |
| Classification | **BART-MNLI (zero-shot)** | Fine-tuned BERT | No training data on Day 1; fine-tune later when we have 500+ labeled samples |
| Fuzzy matching | **rapidfuzz** | fuzzywuzzy | Same algorithm, 10x faster (C++ backend) |
| Database | **PostgreSQL** | MySQL, MongoDB | pg_trgm for fuzzy search, JSONB for flexible fields, best for relational data |
| Search | **Meilisearch** | Elasticsearch | 300MB RAM vs 2GB+, single binary, built-in typo tolerance, no JVM |
| Object storage | **MinIO** | S3, Cloudflare R2 | Self-hosted (free), S3-compatible API |
| API framework | **FastAPI** | Django, Flask | Native async, auto-generated API docs, Pydantic validation |
| Task queue | **Celery + Redis** | Airflow, Temporal, RQ | Built-in scheduler (Beat), handles both periodic tasks and ad-hoc processing |
| Deployment | **Docker Compose** | Kubernetes | K8s is overkill for a single VPS; Docker Compose is simple and sufficient |

### The overriding constraint

Every tool was chosen asking one question:

**"Can this run on a single 16GB VPS alongside everything else, costing ~$20/month?"**

When your first 10 customers pay INR 5,000/month ($60 each = $600 total MRR), your infrastructure can't cost $300/month. That eliminates AWS managed services, Elasticsearch, Airflow, and anything with a JVM.
