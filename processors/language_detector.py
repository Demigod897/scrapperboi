import structlog

logger = structlog.get_logger(__name__)

# Language model loaded lazily
_model = None


def _load_model():
    global _model
    if _model is None:
        try:
            import fasttext
            import os

            # Try multiple paths (local dev vs Docker)
            model_paths = [
                "models/lid.176.ftz",
                "/app/models/lid.176.ftz",
            ]
            for path in model_paths:
                if os.path.exists(path):
                    _model = fasttext.load_model(path)
                    logger.info("fasttext_model_loaded", path=path)
                    return _model

            logger.warning(
                "fasttext_model_not_found",
                hint="Download from: https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz into models/",
            )
            _model = "unavailable"
        except Exception as e:
            logger.warning("fasttext_model_not_available", error=str(e))
            _model = "unavailable"
    return _model


def detect_language(text: str) -> tuple[str, float]:
    """Detect the language of text.

    Returns:
        (language_code, confidence) e.g. ("en", 0.95) or ("hi", 0.88)
    """
    model = _load_model()

    if model == "unavailable" or not text.strip():
        return "en", 0.0

    # Clean text for detection (first 500 chars, no newlines)
    sample = text.replace("\n", " ")[:500].strip()
    if not sample:
        return "en", 0.0

    predictions = model.predict(sample)
    lang = predictions[0][0].replace("__label__", "")
    confidence = float(predictions[1][0])

    logger.debug("language_detected", lang=lang, confidence=round(confidence, 3))
    return lang, confidence


def is_indic(lang_code: str) -> bool:
    """Check if a language code represents an Indic language."""
    indic_codes = {"hi", "mr", "ta", "te", "bn", "gu", "kn", "ml", "pa", "or", "as", "ur"}
    return lang_code in indic_codes
