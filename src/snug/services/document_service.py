# src/snug/services/document_service.py
import re
import json
from pathlib import Path
from typing import Dict, Any, Optional

from ..logging import log

try:
    from pdfminer.high_level import extract_text
except ImportError:
    extract_text = None


class DocumentService:
    """
    Service for extracting structured data from payslips / PDFs.

    - Supports either raw text or a path to a PDF.
    - Uses regex-based parsing for key fields.
    - Designed to be extended with OCR / AI-powered parsing.
    """

    def __init__(self, use_ocr: bool = False):
        # Placeholder flag: you can later wire OCR libraries here (tesseract, pdf2image, etc.)
        self.use_ocr = use_ocr

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────
    def extract_payslip_data(self, input_source: str) -> Dict[str, Any]:
        """
        Extract structured payslip data from either:
        - raw text (e.g. pasted content), or
        - a PDF path (e.g. 'payslip.pdf').
        """
        text = self._load_text(input_source)
        original_text = text or ""
        normalized_text = self._normalize_text(original_text)

        fields = self._parse_payslip_fields(original_text)
        fields["raw_text"] = normalized_text[:1000]

        log.info("document_extracted", result_summary=json.dumps(fields, indent=2))
        return fields

    # Placeholder for future AI/OCR powered extraction
    def extract_with_ai(self, input_source: str) -> Dict[str, Any]:
        """
        Future extension point:

        - Use OCR (e.g. Tesseract + pdf2image) to get text from scans.
        - Then call an LLM to robustly extract fields beyond simple regex.
        - For now, this simply delegates to regex-based extraction.
        """
        return self.extract_payslip_data(input_source)

    # ─────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────
    def _load_text(self, input_source: str) -> str:
        """
        Decide how to interpret `input_source`:
        - If it looks like a PDF path (ends with .pdf): call read_pdf (which tests monkeypatch).
        - Otherwise: treat as raw text.
        """
        # If it looks like a PDF, always go through read_pdf so monkeypatch works.
        if input_source.lower().endswith(".pdf"):
            # NOTE: we deliberately *do not* catch RuntimeError here so tests can assert on it.
            return read_pdf(input_source)

        # Otherwise, treat as plain text
        return input_source

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize whitespace for cleaner downstream processing/logging."""
        return re.sub(r"\s+", " ", text.strip())

    @staticmethod
    def _parse_payslip_fields(text: str) -> Dict[str, Any]:
        """
        Extract key fields using regex.

        IMPORTANT: we run regex against the *original* text, preserving line breaks,
        so patterns like 'Employer: ABC Pty Ltd\\nGross Income: 5000' are parsed correctly.
        """
        # Match up to the end of the line for employee/employer to avoid grabbing entire document
        employee_match = re.search(
            r"^Employee[:\-]?\s*([^\n\r]+)",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        employer_match = re.search(
            r"^Employer[:\-]?\s*([^\n\r]+)",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        gross_match = re.search(
            r"Gross\s*Income[:\-]?\s*\$?([\d,\.]+)",
            text,
            flags=re.IGNORECASE,
        )
        net_match = re.search(
            r"Net\s*Income[:\-]?\s*\$?([\d,\.]+)",
            text,
            flags=re.IGNORECASE,
        )
        period_match = re.search(
            r"Pay\s*Period[:\-]?\s*([^\n\r]+)",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        def _to_float(m: Optional[re.Match]) -> Optional[float]:
            if not m:
                return None
            raw = m.group(1).replace(",", "")
            try:
                return float(raw)
            except ValueError:
                return None

        result: Dict[str, Any] = {
            "employee_name": employee_match.group(1).strip() if employee_match else None,
            "employer_name": employer_match.group(1).strip() if employer_match else None,
            "gross_income": _to_float(gross_match),
            "net_income": _to_float(net_match),
            "pay_period": period_match.group(1).strip() if period_match else None,
        }
        return result


# ─────────────────────────────────────────────
# Backwards-compatible module-level helpers
# ─────────────────────────────────────────────
def extract_payslip_data(input_source: str) -> Dict[str, Any]:
    """
    Backwards-compatible function used by tests.

    Delegates to DocumentService().extract_payslip_data but keeps the same interface:
    - When called with raw text, parses it directly.
    - When called with a string ending in '.pdf', goes through read_pdf().
      This allows tests to monkeypatch `snug.services.document_service.read_pdf`.
    """
    service = DocumentService()
    return service.extract_payslip_data(input_source)


def read_pdf(file_path: str) -> str:
    """
    Read text from a PDF.

    - In production: uses pdfminer.high_level.extract_text if available.
    - If file doesn't exist: raises FileNotFoundError.
    - On other failures: logs and returns empty string.

    NOTE: tests monkeypatch this function to raise RuntimeError for the OCR failure test.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")

    try:
        if extract_text:
            return extract_text(file_path)
        # If pdfminer isn't available, this is where you’d hook in OCR instead.
        raise RuntimeError("OCR/PDF text extraction not available")
    except Exception as e:
        # This branch is *not* hit in the OCR test, because they monkeypatch read_pdf directly.
        log.error("pdf_read_error", file=file_path, error=str(e))
        return ""
