import re
from dataclasses import dataclass
from datetime import date, timedelta

import structlog

logger = structlog.get_logger(__name__)

CIN_REGEX = re.compile(r"^[A-Z]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$")


@dataclass
class ValidationResult:
    field: str
    is_valid: bool
    reason: str
    confidence: float


def validate_extraction(extraction: dict) -> list[ValidationResult]:
    """Validate all extracted fields from a document.

    Checks:
        1. CIN format
        2. Penalty amount range
        3. Date range sanity
        4. Company name length
        5. Required fields present
    """
    results = []

    # 1. CIN format validation
    for cin in extraction.get("cin_numbers", []):
        valid = bool(CIN_REGEX.match(cin))
        results.append(ValidationResult(
            "cin", valid, f"format_check: {cin}", 1.0 if valid else 0.0,
        ))

    # 2. Penalty amount sanity
    for penalty in extraction.get("penalties", []):
        amount = penalty["amount_inr"]
        # Indian regulatory penalties: Rs 1,000 to Rs 500 crore
        valid = 1_000 <= amount <= 5_000_000_000
        results.append(ValidationResult(
            "penalty_amount", valid,
            f"range_check: {amount}",
            0.9 if valid else 0.3,
        ))

    # 3. Date sanity
    for d in extraction.get("dates", []):
        try:
            parsed = date.fromisoformat(d["date"])
            valid = date(1990, 1, 1) <= parsed <= date.today() + timedelta(days=30)
        except (ValueError, TypeError):
            valid = False
        results.append(ValidationResult(
            "date", valid,
            f"range_check: {d.get('date', 'INVALID')}",
            0.95 if valid else 0.1,
        ))

    # 4. Company name sanity
    for company in extraction.get("companies", []):
        name = company.get("name", "")
        valid = 3 <= len(name) <= 200
        results.append(ValidationResult(
            "company_name", valid,
            f"length_check: {len(name)} chars",
            0.8 if valid else 0.2,
        ))

    # 5. At least one entity found
    has_entity = bool(
        extraction.get("companies")
        or extraction.get("cin_numbers")
        or extraction.get("individuals")
    )
    results.append(ValidationResult(
        "entity_present", has_entity,
        "at least one entity required",
        0.9 if has_entity else 0.4,
    ))

    return results


def compute_overall_confidence(
    entity_confidence: float = 0.0,
    cin_confidence: float = 0.0,
    violation_confidence: float = 0.0,
    penalty_confidence: float = 0.0,
    date_confidence: float = 0.0,
) -> float:
    """Compute weighted overall extraction confidence.

    Weights:
        entity:    30% (most important -- who was penalized)
        penalty:   20% (how much)
        violation: 20% (what for)
        cin:       15% (entity resolution quality)
        date:      15% (when)
    """
    weights = {
        "entity": 0.30,
        "cin": 0.15,
        "violation": 0.20,
        "penalty": 0.20,
        "date": 0.15,
    }
    scores = {
        "entity": entity_confidence,
        "cin": cin_confidence,
        "violation": violation_confidence,
        "penalty": penalty_confidence,
        "date": date_confidence,
    }
    overall = sum(weights[k] * scores[k] for k in weights)

    logger.debug(
        "confidence_computed",
        overall=round(overall, 4),
        scores={k: round(v, 4) for k, v in scores.items()},
    )
    return overall


# Thresholds
AUTO_APPROVE_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.30


def route_extraction(confidence: float) -> str:
    """Determine routing based on confidence score.

    Returns:
        "auto_approved" | "pending_review" | "rejected"
    """
    if confidence >= AUTO_APPROVE_THRESHOLD:
        return "auto_approved"
    elif confidence >= REVIEW_THRESHOLD:
        return "pending_review"
    else:
        return "rejected"
