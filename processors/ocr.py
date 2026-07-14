import io

import structlog
from PIL import Image

logger = structlog.get_logger(__name__)


class OCREngine:
    """Tiered OCR engine.

    Tier 1: Tesseract (free, good for clean English prints)
    Tier 2: Google Cloud Vision (excellent for Indic scripts, ~$1.50/1K pages)

    Falls back to Tier 2 when Tesseract confidence is below threshold.
    """

    CONFIDENCE_THRESHOLD = 60  # Minimum avg confidence to accept Tesseract result

    def __init__(self, fallback_to_cloud: bool = True):
        self.fallback = fallback_to_cloud

    def extract_text(self, image: Image.Image, lang: str = "eng") -> tuple[str, str]:
        """Extract text from an image.

        Args:
            image: PIL Image
            lang: Tesseract language code (e.g., "eng", "eng+hin")

        Returns:
            (extracted_text, method_used)
        """
        text, confidence = self._tesseract_ocr(image, lang)

        if confidence >= self.CONFIDENCE_THRESHOLD or not self.fallback:
            return text, "ocr_tesseract"

        logger.info(
            "tesseract_low_confidence",
            confidence=confidence,
            falling_back_to="google_vision",
        )

        # Tier 2: Google Cloud Vision
        try:
            gv_text = self._google_vision_ocr(image)
            if gv_text:
                return gv_text, "ocr_gcloud"
        except Exception as e:
            logger.warning("google_vision_failed", error=str(e))

        # Fall back to Tesseract result even if low confidence
        return text, "ocr_tesseract"

    def _tesseract_ocr(self, image: Image.Image, lang: str) -> tuple[str, float]:
        """Run Tesseract OCR and return text + average confidence."""
        try:
            import pytesseract
        except ImportError:
            raise ImportError("pytesseract is required: pip install pytesseract")

        # Get per-word confidence data
        data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
        confidences = [int(c) for c in data["conf"] if int(c) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        # Get full text
        text = pytesseract.image_to_string(image, lang=lang)

        logger.debug(
            "tesseract_result",
            text_length=len(text),
            avg_confidence=round(avg_confidence, 1),
            word_count=len(confidences),
        )

        return text, avg_confidence

    def _google_vision_ocr(self, image: Image.Image) -> str:
        """Run Google Cloud Vision OCR."""
        from config.settings import settings

        if not settings.google_application_credentials:
            logger.warning("google_vision_not_configured")
            return ""

        try:
            from google.cloud import vision
        except ImportError:
            logger.warning("google_cloud_vision_not_installed")
            return ""

        client = vision.ImageAnnotatorClient()
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        gimage = vision.Image(content=buf.getvalue())
        response = client.document_text_detection(image=gimage)

        if response.error.message:
            raise Exception(f"Google Vision error: {response.error.message}")

        text = response.full_text_annotation.text if response.full_text_annotation else ""
        logger.debug("google_vision_result", text_length=len(text))
        return text
