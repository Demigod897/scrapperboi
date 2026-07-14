import re
from datetime import date, timedelta

import structlog
from dateutil import parser as dateutil_parser

logger = structlog.get_logger(__name__)

# Date patterns common in Indian regulatory documents
DATE_PATTERNS = [
    # "01.01.2024", "01/01/2024", "01-01-2024"
    re.compile(r"\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{4})\b"),
    # "January 1, 2024" or "1st January 2024" or "1 January 2024"
    re.compile(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+"
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r",?\s+(\d{4})\b",
        re.IGNORECASE,
    ),
    # "1 Jan 2024" or "01 Feb 2024"
    re.compile(
        r"\b(\d{1,2})\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*"
        r",?\s+(\d{4})\b",
        re.IGNORECASE,
    ),
    # "January 2024" (month-year only)
    re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
        r",?\s+(\d{4})\b",
        re.IGNORECASE,
    ),
]

# Valid date range for regulatory documents
MIN_DATE = date(1990, 1, 1)
MAX_DATE_OFFSET = timedelta(days=30)  # Allow dates up to 30 days in future


def extract_dates(text: str) -> list[dict]:
    """Extract all dates from text.

    Returns:
        List of dicts with keys: date (ISO format), raw_text, span
    """
    dates = []
    seen = set()

    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            raw = match.group(0)
            try:
                # dayfirst=True because Indian dates are DD/MM/YYYY
                parsed = dateutil_parser.parse(raw, dayfirst=True)
                iso = parsed.date().isoformat()

                # Sanity check
                if not (MIN_DATE <= parsed.date() <= date.today() + MAX_DATE_OFFSET):
                    continue

                if iso not in seen:
                    seen.add(iso)
                    dates.append({
                        "date": iso,
                        "raw_text": raw,
                        "span": (match.start(), match.end()),
                    })
            except (ValueError, OverflowError):
                continue

    logger.debug("dates_extracted", count=len(dates))
    return dates


def classify_dates(text: str, dates: list[dict]) -> dict:
    """Classify extracted dates into order_date and violation_date.

    Uses context keywords around each date to determine its role.

    Returns:
        {"order_date": "YYYY-MM-DD" | None, "violation_date": "YYYY-MM-DD" | None}
    """
    result = {"order_date": None, "violation_date": None}

    order_keywords = [
        "order dated", "dated this", "pronounced on", "order of",
        "passed on", "order is", "this order", "imposed on",
        "date of order", "order no",
    ]
    violation_keywords = [
        "during the period", "violation on", "inspection on",
        "inspection conducted", "audit for", "period from",
        "year ended", "financial year", "assessment year",
        "between", "during",
    ]

    for d in dates:
        start = max(0, d["span"][0] - 150)
        end = min(len(text), d["span"][1] + 50)
        context = text[start:end].lower()

        if any(kw in context for kw in order_keywords):
            if result["order_date"] is None:
                result["order_date"] = d["date"]
        elif any(kw in context for kw in violation_keywords):
            if result["violation_date"] is None:
                result["violation_date"] = d["date"]

    # Fallback: if no order_date found, use the latest date
    if not result["order_date"] and dates:
        sorted_dates = sorted(dates, key=lambda x: x["date"], reverse=True)
        result["order_date"] = sorted_dates[0]["date"]

    logger.info("dates_classified", order_date=result["order_date"], violation_date=result["violation_date"])
    return result
