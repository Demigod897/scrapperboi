import structlog

logger = structlog.get_logger(__name__)

# 3-level violation taxonomy: DOMAIN / CATEGORY
VIOLATION_TAXONOMY = {
    "BANKING_REGULATORY": {
        "KYC_AML_VIOLATION": "KYC or anti-money laundering violation",
        "LENDING_NORMS_VIOLATION": "lending norms or loan regulation violation",
        "FAIR_PRACTICES_CODE": "fair practices code or customer service violation",
        "DEPOSIT_ACCEPTANCE_VIOLATION": "unauthorized deposit acceptance or NBFC deposit violation",
        "REPORTING_FAILURE": "regulatory reporting or filing failure",
        "CAPITAL_ADEQUACY": "capital adequacy or CRAR violation",
        "ASSET_CLASSIFICATION": "asset classification or NPA provisioning violation",
        "INTEREST_RATE_VIOLATION": "interest rate ceiling or usurious lending",
        "OUTSOURCING_VIOLATION": "outsourcing norms or third party management failure",
        "CYBER_SECURITY": "IT security or cyber security framework violation",
    },
    "SECURITIES_MARKET": {
        "INSIDER_TRADING": "insider trading or UPSI violation",
        "MARKET_MANIPULATION": "market manipulation or fraudulent trading",
        "DISCLOSURE_FAILURE": "disclosure failure or non-compliance with listing regulations",
        "INTERMEDIARY_VIOLATION": "broker or intermediary regulation violation",
        "TAKEOVER_CODE_VIOLATION": "takeover code or acquisition regulation violation",
        "MUTUAL_FUND_VIOLATION": "mutual fund regulation violation",
    },
    "FOOD_SAFETY": {
        "ADULTERATION": "food adulteration",
        "MISLABELING": "food mislabeling or false claims",
        "HYGIENE_VIOLATION": "food hygiene or sanitation violation",
        "LICENSE_VIOLATION": "food license or registration violation",
        "SUBSTANDARD_PRODUCT": "substandard food product",
    },
    "ENVIRONMENTAL": {
        "EMISSION_STANDARD_VIOLATION": "emission standard or air pollution violation",
        "EFFLUENT_DISCHARGE": "effluent discharge or water pollution violation",
        "HAZARDOUS_WASTE": "hazardous waste management violation",
        "CONSENT_ORDER_VIOLATION": "consent order or environmental clearance violation",
    },
    "COMPETITION": {
        "ANTI_COMPETITIVE_AGREEMENT": "anti-competitive agreement or cartel",
        "ABUSE_OF_DOMINANCE": "abuse of dominant position",
        "GUN_JUMPING": "gun jumping or merger filing violation",
    },
    "CORPORATE_GOVERNANCE": {
        "DIRECTOR_DISQUALIFICATION": "director disqualification",
        "FILING_DEFAULT": "annual filing or statutory return default",
        "FRAUD": "corporate fraud or misrepresentation",
        "RELATED_PARTY_TRANSACTION": "related party transaction violation",
    },
}

# Build flat label map: human-readable description -> taxonomy code
_LABEL_MAP = {}
_CANDIDATE_LABELS = []
for domain, categories in VIOLATION_TAXONOMY.items():
    for code, description in categories.items():
        full_code = f"{domain}/{code}"
        _LABEL_MAP[description] = full_code
        _CANDIDATE_LABELS.append(description)

# Classifier loaded lazily
_classifier = None


def _get_classifier():
    global _classifier
    if _classifier is None:
        try:
            from transformers import pipeline

            _classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=-1,  # CPU; use 0 for GPU
            )
        except Exception as e:
            logger.warning("classifier_not_available", error=str(e))
            _classifier = "unavailable"
    return _classifier


def classify_violation(text: str, top_k: int = 3) -> list[dict]:
    """Classify the violation type using zero-shot classification.

    Uses the first ~2000 chars of text (violation type is usually stated
    early in the document).

    Args:
        text: Document text
        top_k: Number of top predictions to return

    Returns:
        List of dicts with keys: violation_type, description, confidence
    """
    classifier = _get_classifier()
    if classifier == "unavailable":
        return _fallback_classify(text, top_k)

    # Use a truncated snippet -- violation type is usually in the first portion
    snippet = text[:2000]

    try:
        result = classifier(
            snippet,
            candidate_labels=_CANDIDATE_LABELS,
            multi_label=True,
        )

        predictions = []
        for label, score in zip(result["labels"][:top_k], result["scores"][:top_k]):
            predictions.append({
                "violation_type": _LABEL_MAP[label],
                "description": label,
                "confidence": round(score, 4),
            })

        logger.info(
            "violation_classified",
            top_prediction=predictions[0]["violation_type"] if predictions else None,
            top_confidence=predictions[0]["confidence"] if predictions else 0,
        )
        return predictions

    except Exception as e:
        logger.error("classification_failed", error=str(e))
        return _fallback_classify(text, top_k)


def _fallback_classify(text: str, top_k: int = 3) -> list[dict]:
    """Keyword-based fallback classification when the ML model is unavailable."""
    text_lower = text.lower()
    scores = {}

    keyword_map = {
        "BANKING_REGULATORY/KYC_AML_VIOLATION": [
            "kyc", "know your customer", "anti-money laundering",
            "aml", "cdd", "customer due diligence", "suspicious transaction",
        ],
        "BANKING_REGULATORY/LENDING_NORMS_VIOLATION": [
            "lending", "loan", "credit", "disbursement", "interest rate",
            "emi", "prepayment", "digital lending",
        ],
        "BANKING_REGULATORY/FAIR_PRACTICES_CODE": [
            "fair practices", "customer grievance", "complaint",
            "transparency", "disclosure to borrower",
        ],
        "BANKING_REGULATORY/REPORTING_FAILURE": [
            "reporting", "filing", "return", "submission",
            "crilc", "statutory return",
        ],
        "BANKING_REGULATORY/ASSET_CLASSIFICATION": [
            "asset classification", "npa", "non-performing",
            "provisioning", "slippage",
        ],
        "SECURITIES_MARKET/INSIDER_TRADING": [
            "insider trading", "upsi", "unpublished price sensitive",
            "trading window",
        ],
        "SECURITIES_MARKET/DISCLOSURE_FAILURE": [
            "disclosure", "listing obligation", "lodr",
            "annual report", "corporate governance",
        ],
    }

    for violation_type, keywords in keyword_map.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[violation_type] = score / len(keywords)

    # Sort by score, return top_k
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    return [
        {
            "violation_type": vtype,
            "description": "keyword-based classification",
            "confidence": round(score, 4),
        }
        for vtype, score in sorted_scores
    ]


def get_domain_and_subtype(violation_type: str) -> tuple[str, str]:
    """Split 'BANKING_REGULATORY/KYC_AML_VIOLATION' into domain and subtype."""
    parts = violation_type.split("/", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return parts[0], ""


def determine_severity(violation_type: str, penalty_amount: float | None) -> str:
    """Determine violation severity based on type and penalty amount."""
    # High-severity violations by type
    high_severity_types = {
        "SECURITIES_MARKET/INSIDER_TRADING",
        "SECURITIES_MARKET/MARKET_MANIPULATION",
        "CORPORATE_GOVERNANCE/FRAUD",
        "COMPETITION/ANTI_COMPETITIVE_AGREEMENT",
    }

    if violation_type in high_severity_types:
        return "CRITICAL" if (penalty_amount and penalty_amount > 10_000_000) else "HIGH"

    if penalty_amount:
        if penalty_amount >= 50_000_000:  # Rs 5 crore+
            return "CRITICAL"
        elif penalty_amount >= 10_000_000:  # Rs 1 crore+
            return "HIGH"
        elif penalty_amount >= 1_000_000:  # Rs 10 lakh+
            return "MEDIUM"

    return "LOW"
