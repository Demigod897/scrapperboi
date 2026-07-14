import re

import structlog
from rapidfuzz import fuzz, process

logger = structlog.get_logger(__name__)

# Common suffixes to strip for matching
COMPANY_SUFFIXES = [
    "PRIVATE LIMITED", "PVT LTD", "PVT. LTD.", "PVT LTD.",
    "LIMITED", "LTD", "LTD.",
    "LLP", "INC", "INCORPORATED",
    "CORPORATION", "CORP", "CORP.",
    "CO-OPERATIVE", "COOPERATIVE", "CO OPERATIVE",
    "SOCIETY", "TRUST", "FOUNDATION",
]


class EntityResolver:
    """Resolve extracted company names to MCA CIN numbers.

    Uses fuzzy matching against the MCA company master data loaded into
    PostgreSQL. The company master is loaded from data.gov.in CSV dumps.
    """

    def __init__(self):
        self._companies: dict[str, str] = {}  # cin -> company_name
        self._cin_by_name: dict[str, str] = {}  # normalized_name -> cin
        self._names: list[str] = []
        self._loaded = False

    def load_from_db(self):
        """Load MCA company master data from PostgreSQL."""
        from storage.db import MCACompanyMaster, SyncSessionLocal

        if self._loaded:
            return

        logger.info("loading_mca_company_master")
        with SyncSessionLocal() as session:
            rows = session.query(
                MCACompanyMaster.cin,
                MCACompanyMaster.company_name,
            ).all()

        self._companies = {row.cin: row.company_name for row in rows}
        self._cin_by_name = {row.company_name.upper().strip(): row.cin for row in rows}
        self._names = list(self._cin_by_name.keys())
        self._loaded = True

        logger.info("mca_master_loaded", count=len(self._companies))

    def resolve(self, extracted_name: str, threshold: int = 85) -> dict | None:
        """Resolve a company name to its MCA CIN.

        Args:
            extracted_name: Company name extracted from document
            threshold: Minimum fuzzy match score (0-100)

        Returns:
            Dict with cin, matched_name, confidence, method or None
        """
        if not self._loaded:
            self.load_from_db()

        if not self._names:
            logger.warning("mca_master_empty")
            return None

        normalized = self._normalize(extracted_name)
        if not normalized:
            return None

        # Step 1: Exact match
        if normalized in self._cin_by_name:
            cin = self._cin_by_name[normalized]
            return {
                "cin": cin,
                "matched_name": normalized,
                "confidence": 1.0,
                "method": "exact",
            }

        # Step 2: Fuzzy match
        match = process.extractOne(
            normalized,
            self._names,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=threshold,
        )

        if match:
            matched_name, score, _ = match
            cin = self._cin_by_name[matched_name]
            logger.debug(
                "fuzzy_match",
                extracted=extracted_name,
                matched=matched_name,
                score=score,
            )
            return {
                "cin": cin,
                "matched_name": matched_name,
                "confidence": score / 100.0,
                "method": "fuzzy",
            }

        logger.debug("no_match_found", extracted_name=extracted_name)
        return None

    def resolve_cin(self, cin: str) -> dict | None:
        """Look up a CIN directly."""
        if not self._loaded:
            self.load_from_db()

        if cin in self._companies:
            return {
                "cin": cin,
                "matched_name": self._companies[cin],
                "confidence": 1.0,
                "method": "cin_lookup",
            }
        return None

    @staticmethod
    def _normalize(name: str) -> str:
        """Normalize a company name for matching."""
        name = name.upper().strip()

        # Remove common suffixes
        for suffix in COMPANY_SUFFIXES:
            name = name.replace(suffix, "").strip()

        # Remove punctuation except spaces
        name = re.sub(r"[^\w\s]", "", name)

        # Normalize whitespace
        name = " ".join(name.split())

        return name
