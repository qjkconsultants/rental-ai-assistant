# tests/test_multiagent_integration.py
import io
import pytest
from fastapi.testclient import TestClient
from snug.api.app import app


@pytest.fixture
def client():
    """Provide a synchronous FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def fake_payload():
    """Default VIC payload for integration testing."""
    return {
        "state": "VIC",
        "email": "vic.tester@example.com",
        "first_name": "Alice",
        "last_name": "Brown",
        "dob": "1995-03-15",
        "phone_number": "0400000003",
        "current_address": "5 Melbourne Rd",
        "employment_status": "Casual",
        "employer_name": "XYZ",
        "employer_contact": "0400333444",
        "income": 62000,
    }


def make_fake_pdf_bytes(name="dummy.pdf"):
    """Generate minimal valid fake PDF content for uploads."""
    pdf_bytes = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\nxref\n0 2\n0000000000 65535 f \ntrailer << /Root 1 0 R >>\nstartxref\n0\n%%EOF"
    return (name, io.BytesIO(pdf_bytes), "application/pdf")


def test_application_returns_response_message(client, fake_payload):
    """Full multi-agent E2E test — should yield AI message and structured response."""
    fake_files = [
        ("documents", make_fake_pdf_bytes("rental_form.pdf")),
        ("documents", make_fake_pdf_bytes("bank_statement.pdf")),
        ("documents", make_fake_pdf_bytes("reference_letter.pdf")),
    ]

    response = client.post("/applications", data=fake_payload, files=fake_files)
    assert response.status_code == 200, response.text

    data = response.json()
    assert data["status"] == "ok"
    app_data = data["application"]

    # Validate structure
    assert "message" in app_data
    assert "VIC" in app_data["state"]
    assert "email" in app_data
    assert "profile" in app_data
    assert isinstance(app_data["profile"], dict)
    email_val = app_data["profile"]["email"]
    assert email_val in ("vic.tester@example.com", "[REDACTED]")
    assert "Please ensure" in app_data["message"] or "ensure" in app_data["message"].lower()


def test_guardrails_redacts_email_and_phone(client, fake_payload):
    """
    Guardrails integration test:
    - Email and phone should be redacted in the final profile
    - Guardrails findings should flag those fields
    """
    # Make sure we have PII in the incoming payload
    pii_payload = {
        **fake_payload,
        "email": "pii.user@example.com",
        "phone_number": "0400000999",
        "employer_contact": "0400111222",
    }

    fake_files = [
        ("documents", make_fake_pdf_bytes("rental_form.pdf")),
        ("documents", make_fake_pdf_bytes("bank_statement.pdf")),
        ("documents", make_fake_pdf_bytes("reference_letter.pdf")),
    ]

    response = client.post("/applications", data=pii_payload, files=fake_files)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["status"] == "ok"

    app_data = body["application"]
    profile = app_data["profile"]

    # 🔒 PII should be redacted in the final profile
    assert profile["email"] == "[REDACTED]"
    assert profile["phone_number"] == "[REDACTED]"
    # employer_contact is also flagged as PII and should be redacted
    assert profile["employer_contact"] == "[REDACTED]"

    # 🛡 Guardrails metadata should show which fields were flagged
    context_used = app_data.get("context_used", {})
    findings = context_used.get("guardrails_findings", [])
    fields_flagged = {f["field"] for f in findings}

    assert "email" in fields_flagged
    assert "phone_number" in fields_flagged
    assert "employer_contact" in fields_flagged
