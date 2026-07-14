import re
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)

# --- Regex patterns for structured identifiers ---

CIN_PATTERN = re.compile(r"[A-Z]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}")
PAN_PATTERN = re.compile(r"[A-Z]{5}\d{4}[A-Z]")
GSTIN_PATTERN = re.compile(r"\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]")
RBI_LICENSE_PATTERN = re.compile(
    r"(?:License|Licence)\s*(?:No\.?|Number)\s*[:.]?\s*([A-Z0-9\-/]+)",
    re.IGNORECASE,
)

# Regulator keyword mapping
REGULATOR_KEYWORDS = {
    "RBI": ["Reserve Bank of India", "RBI", "reserve bank"],
    "SEBI": ["Securities and Exchange Board", "SEBI"],
    "FSSAI": ["Food Safety and Standards Authority", "FSSAI"],
    "CPCB": ["Central Pollution Control Board", "CPCB"],
    "CCI": ["Competition Commission of India", "CCI"],
    "IRDAI": ["Insurance Regulatory and Development Authority", "IRDAI", "IRDA"],
    "MCA": ["Ministry of Corporate Affairs", "MCA"],
    "NCLT": ["National Company Law Tribunal", "NCLT"],
    "NCLAT": ["National Company Law Appellate Tribunal", "NCLAT"],
}

# spaCy model loaded lazily
_nlp_en = None


def _get_spacy_model():
    global _nlp_en
    if _nlp_en is None:
        import spacy

        try:
            _nlp_en = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spacy_model_not_found", model="en_core_web_sm")
            _nlp_en = "unavailable"
    return _nlp_en


@dataclass
class ExtractedEntities:
    """Container for all entities extracted from a document."""

    companies: list[dict] = field(default_factory=list)
    individuals: list[dict] = field(default_factory=list)
    cin_numbers: list[str] = field(default_factory=list)
    pan_numbers: list[str] = field(default_factory=list)
    gstin_numbers: list[str] = field(default_factory=list)
    rbi_license_numbers: list[str] = field(default_factory=list)
    regulators_mentioned: list[str] = field(default_factory=list)


def extract_entities(text: str, lang: str = "en") -> ExtractedEntities:
    """Extract entities from document text.

    Uses regex for structured identifiers (CIN, PAN, GSTIN) and
    spaCy NER for company/person names.

    Args:
        text: Document text
        lang: Language code ("en" for English, "hi" for Hindi, etc.)

    Returns:
        ExtractedEntities with all found entities
    """
    result = ExtractedEntities()

    # 1. Regex-based structured ID extraction (language-independent)
    result.cin_numbers = list(set(CIN_PATTERN.findall(text)))
    result.pan_numbers = list(set(PAN_PATTERN.findall(text)))
    result.gstin_numbers = list(set(GSTIN_PATTERN.findall(text)))
    result.rbi_license_numbers = list(set(RBI_LICENSE_PATTERN.findall(text)))

    # 2. Regulator detection
    text_lower = text.lower()
    for code, keywords in REGULATOR_KEYWORDS.items():
        if any(kw.lower() in text_lower for kw in keywords):
            result.regulators_mentioned.append(code)

    # 3. NLP-based name extraction
    if lang == "en":
        result.companies, result.individuals = _extract_with_spacy(text)
    else:
        result.companies, result.individuals = _extract_with_indic_ner(text)

    logger.info(
        "entities_extracted",
        companies=len(result.companies),
        individuals=len(result.individuals),
        cins=len(result.cin_numbers),
        pans=len(result.pan_numbers),
        regulators=result.regulators_mentioned,
    )

    return result


def _extract_with_spacy(text: str) -> tuple[list[dict], list[dict]]:
    """Extract ORG and PERSON entities using spaCy."""
    nlp = _get_spacy_model()
    if nlp == "unavailable":
        return [], []

    # spaCy has a max length; process in chunks if needed
    max_length = 100_000
    doc = nlp(text[:max_length])

    companies = []
    individuals = []
    seen_companies = set()
    seen_individuals = set()

    for ent in doc.ents:
        name = ent.text.strip()
        if not name or len(name) < 3:
            continue

        if ent.label_ == "ORG" and name not in seen_companies:
            # Filter out regulator names -- we want regulated entities, not regulators
            if not _is_regulator_name(name):
                companies.append({
                    "name": name,
                    "confidence": 0.85,
                    "label": "ORG",
                    "span": (ent.start_char, ent.end_char),
                })
                seen_companies.add(name)

        elif ent.label_ == "PERSON" and name not in seen_individuals:
            individuals.append({
                "name": name,
                "confidence": 0.85,
                "label": "PERSON",
                "span": (ent.start_char, ent.end_char),
            })
            seen_individuals.add(name)

    return companies, individuals


def _extract_with_indic_ner(text: str) -> tuple[list[dict], list[dict]]:
    """Extract entities from Indic language text using ai4bharat/IndicNER."""
    try:
        from transformers import pipeline as hf_pipeline

        ner = hf_pipeline(
            "token-classification",
            model="ai4bharat/IndicNER",
            aggregation_strategy="simple",
        )
    except Exception as e:
        logger.warning("indic_ner_not_available", error=str(e))
        return [], []

    # IndicNER has input length limits
    results = ner(text[:5000])

    companies = [
        {"name": r["word"], "confidence": r["score"], "label": "ORG"}
        for r in results
        if r["entity_group"] == "ORG"
    ]
    individuals = [
        {"name": r["word"], "confidence": r["score"], "label": "PER"}
        for r in results
        if r["entity_group"] == "PER"
    ]

    return companies, individuals


def _is_regulator_name(name: str) -> bool:
    """Check if a name is a known regulator (not a regulated entity)."""
    name_lower = name.lower()
    regulator_names = [
        "reserve bank of india", "rbi",
        "securities and exchange board", "sebi",
        "competition commission", "cci",
        "ministry of corporate affairs", "mca",
        "food safety and standards", "fssai",
        "central pollution control", "cpcb",
        "insurance regulatory", "irdai", "irda",
        "government of india",
        "supreme court", "high court",
    ]
    return any(rn in name_lower for rn in regulator_names)
