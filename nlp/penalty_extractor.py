import re
from decimal import Decimal, InvalidOperation

import structlog

logger = structlog.get_logger(__name__)

# Indian number multipliers
MULTIPLIERS = {
    "hundred": 100,
    "thousand": 1_000,
    "lakh": 100_000,
    "lakhs": 100_000,
    "lac": 100_000,
    "lacs": 100_000,
    "crore": 10_000_000,
    "crores": 10_000_000,
    "cr": 10_000_000,
    "million": 1_000_000,
    "billion": 1_000_000_000,
}

# Patterns ordered from most specific to least specific
PENALTY_PATTERNS = [
    # "penalty of Rs. 5 lakh" or "fine of INR 2.5 crores" (broadest context match)
    re.compile(
        r"(?:penalty|fine|penalt[iy]|imposed|monetary\s+penalty)\s+(?:of\s+)?(?:Rs\.?|INR|Rupees)\s*"
        r"([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|lac|lacs|crore|crores|cr|thousand|million|hundred)?",
        re.IGNORECASE,
    ),
    # "Rs. 5 lakh" or "Rs.2.5 crores" or "INR 10 lakh"
    re.compile(
        r"(?:Rs\.?|INR|Rupees)\s*([\d,.]+)\s*(lakh|lakhs|lac|lacs|crore|crores|cr|thousand|million|hundred)\b",
        re.IGNORECASE,
    ),
    # "Rs. 5,00,000/-" or "Rs.5,00,000" (Indian comma format, no multiplier word)
    re.compile(
        r"(?:Rs\.?|INR|Rupees)\s*([\d,]+(?:\.\d+)?)\s*/?-?(?!\s*(?:lakh|lac|crore|cr|thousand|million))",
        re.IGNORECASE,
    ),
]

# Sanity bounds for penalty amounts (INR)
MIN_PENALTY = 1_000  # Rs 1,000
MAX_PENALTY = 5_000_000_000  # Rs 500 crore


def parse_indian_number(num_str: str) -> Decimal:
    """Parse Indian number format: 5,00,000 -> 500000."""
    cleaned = num_str.replace(",", "").replace(" ", "").strip()
    if not cleaned:
        raise ValueError("Empty number string")
    return Decimal(cleaned)


def extract_penalties(text: str) -> list[dict]:
    """Extract penalty amounts from document text.

    Handles Indian currency formats:
        - "Rs. 5,00,000" (Indian comma notation)
        - "Rs. 5 lakh" / "Rs. 5 lakhs" / "Rs. 5 lac"
        - "INR 2.5 crores" / "INR 2.5 cr"
        - "Rupees fifty thousand" (word-based -- NOT handled, too complex)
        - "Rs. 5,00,000/-" (with trailing slash-dash)

    Returns:
        List of dicts with keys: amount_inr, raw_text, span, confidence
    """
    penalties = []

    for pattern in PENALTY_PATTERNS:
        for match in pattern.finditer(text):
            groups = match.groups()
            amount_str = groups[0]
            multiplier_str = groups[1] if len(groups) > 1 and groups[1] else None

            try:
                amount = parse_indian_number(amount_str)
                if multiplier_str:
                    mult = MULTIPLIERS.get(multiplier_str.lower(), 1)
                    amount = amount * mult

                amount_float = float(amount)

                # Sanity check
                if not (MIN_PENALTY <= amount_float <= MAX_PENALTY):
                    logger.debug(
                        "penalty_outside_range",
                        amount=amount_float,
                        raw=match.group(0),
                    )
                    continue

                penalties.append({
                    "amount_inr": amount_float,
                    "raw_text": match.group(0).strip(),
                    "span": (match.start(), match.end()),
                    "confidence": 0.9 if multiplier_str else 0.95,
                })
            except (InvalidOperation, ValueError) as e:
                logger.debug("penalty_parse_failed", raw=match.group(0), error=str(e))
                continue

    # Deduplicate by amount (same penalty mentioned multiple times in doc)
    seen = set()
    unique = []
    for p in penalties:
        if p["amount_inr"] not in seen:
            seen.add(p["amount_inr"])
            unique.append(p)

    # Sort by amount descending (largest penalty first -- usually the main one)
    unique.sort(key=lambda x: x["amount_inr"], reverse=True)

    logger.info("penalties_extracted", count=len(unique), amounts=[p["amount_inr"] for p in unique])

    return unique
