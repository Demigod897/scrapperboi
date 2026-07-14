import structlog

from processors.ocr import OCREngine

logger = structlog.get_logger(__name__)

# Minimum chars per page to consider native text extraction successful
NATIVE_TEXT_THRESHOLD = 100


class PDFProcessor:
    """Extract text from PDFs using native extraction or OCR fallback.

    Strategy:
        1. Try PyMuPDF native text extraction
        2. If text per page < threshold, classify as scanned and OCR all pages
    """

    def __init__(self, ocr_engine: OCREngine | None = None):
        self.ocr = ocr_engine or OCREngine()

    def process(self, pdf_bytes: bytes) -> dict:
        """Process a PDF and return extracted text with metadata.

        Returns:
            {
                "page_count": int,
                "extraction_method": "native" | "ocr",
                "pages": [{"page_num": int, "text": str, "method": str}],
                "full_text": str,
            }
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("pymupdf_not_installed")
            raise ImportError("PyMuPDF is required: pip install PyMuPDF")

        if not pdf_bytes.startswith(b"%PDF"):
            raise ValueError(f"Content is not a PDF (got HTML/other, first bytes: {pdf_bytes[:50]})")

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(doc)
        pages = []
        needs_ocr = False

        # First pass: try native text extraction
        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text")
            if len(text.strip()) < NATIVE_TEXT_THRESHOLD:
                needs_ocr = True
                break
            pages.append({
                "page_num": page_num + 1,
                "text": text,
                "method": "native",
            })

        doc.close()

        if needs_ocr:
            logger.info("ocr_required", page_count=page_count)
            pages = self._ocr_all_pages(pdf_bytes)

        method = "ocr" if needs_ocr else "native"
        full_text = "\n\n".join(p["text"] for p in pages)

        logger.info(
            "pdf_processed",
            page_count=page_count,
            method=method,
            text_length=len(full_text),
        )

        return {
            "page_count": page_count,
            "extraction_method": method,
            "pages": pages,
            "full_text": full_text,
        }

    def _ocr_all_pages(self, pdf_bytes: bytes) -> list[dict]:
        """OCR all pages of a PDF."""
        try:
            from pdf2image import convert_from_bytes
        except ImportError:
            logger.error("pdf2image_not_installed")
            raise ImportError("pdf2image is required: pip install pdf2image")

        images = convert_from_bytes(pdf_bytes, dpi=300)
        pages = []
        for i, img in enumerate(images):
            text, method = self.ocr.extract_text(img, lang="eng+hin")
            pages.append({
                "page_num": i + 1,
                "text": text,
                "method": method,
            })
        return pages

    def process_html(self, html_content: str) -> dict:
        """Process HTML content (for non-PDF documents)."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "lxml")

        # Remove script and style elements
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        return {
            "page_count": 1,
            "extraction_method": "html",
            "pages": [{"page_num": 1, "text": text, "method": "html"}],
            "full_text": text,
        }
