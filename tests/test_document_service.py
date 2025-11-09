import pytest
from snug.services.document_service import DocumentService


@pytest.fixture
def document_service():
    """Fixture to create a new instance of DocumentService for each test."""
    return DocumentService()


def test_extract_payslip_data_from_text(document_service):
    sample_text = "Employer: ABC Pty Ltd\nGross Income: 5000\nDate: 01/11/2025"
    result = document_service.extract_payslip_data(sample_text)
    assert "ABC Pty Ltd" in result["employer_name"]
    assert result["gross_income"] == 5000


def test_ocr_failure(monkeypatch, document_service):
    # Force _load_text to raise RuntimeError
    monkeypatch.setattr(
        document_service,
        "_load_text",
        lambda *_: (_ for _ in ()).throw(RuntimeError("OCR failed"))
    )

    with pytest.raises(RuntimeError):
        document_service.extract_payslip_data("dummy.pdf")
