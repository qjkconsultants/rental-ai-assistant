import io
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from unittest.mock import patch
from snug.api.app import app


@pytest.fixture
def client():
    """Provide a FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture
def fake_files():
    """Prepare dummy in-memory file uploads."""
    return [
        ("documents", ("NSW_rental_form.pdf", io.BytesIO(b"PDFDATA1"), "application/pdf")),
        ("documents", ("NSW_bank_statement.pdf", io.BytesIO(b"PDFDATA2"), "application/pdf")),
        ("documents", ("NSW_reference_letter.pdf", io.BytesIO(b"PDFDATA3"), "application/pdf")),
    ]


@pytest.fixture
def fake_payload():
    """Minimal valid payload for a rental application."""
    return {
        "state": "NSW",
        "email": "nsw.tester@example.com",
        "first_name": "John",
        "middle_name": "",
        "last_name": "Doe",
        "dob": "1990-05-12",
        "phone_number": "0400000001",
        "current_address": "1 Sydney St",
        "previous_address": "2 Sydney St",
        "employment_status": "Full-Time",
        "employer_name": "ABC Pty Ltd",
        "employer_contact": "0400111222",
        "income": "95000",
    }


def make_fake_msg():
    """Return a fake MCPMessage-like object with payload."""
    class FakeMsg:
        def __init__(self):
            self.payload = {
                "final_response": {
                    "email": "nsw.tester@example.com",
                    "message": "All documents received.",
                    "profile": {"email": "nsw.tester@example.com"},
                    "state": "NSW",
                },
                "profile": {"email": "nsw.tester@example.com"},
            }
    return FakeMsg()


# ─────────────────────────────────────────────
# ✅ CORE SUCCESS TEST
# ─────────────────────────────────────────────
@patch("snug.api.app.db.save_application")
@patch("snug.api.app.audit.log_event")
@patch("snug.api.app.multi_graph.invoke")
@patch("snug.api.app.process_file_async")
@patch("snug.api.app.save_uploaded_file")
def test_submit_application_success(
    mock_save_file,
    mock_process_file,
    mock_invoke,
    mock_audit,
    mock_save_app,
    client,
    fake_payload,
    fake_files,
):
    """Should return 200 OK and structured JSON response."""
    # 1️⃣ Mock file save and extract
    mock_save_file.side_effect = lambda f: f"/tmp/{f.filename}"
    mock_process_file.side_effect = lambda p: {"employer": "ABC", "salary": "100000"}

    # 2️⃣ Mock multi_graph result
    mock_invoke.return_value = {"response": make_fake_msg()}

    # 3️⃣ Call endpoint
    response = client.post(
        "/applications",
        data=fake_payload,
        files=fake_files,
    )

    # 4️⃣ Validate response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["state"] == "NSW"
    assert "application" in data
    assert data["application"]["email"] == "nsw.tester@example.com"
    assert data["application"]["state"] == "NSW"
    assert "message" in data["application"]

    # 5️⃣ Verify persistence & audit calls
    mock_save_app.assert_called_once()
    mock_audit.assert_called_once()


# ─────────────────────────────────────────────
# ❌ FAILURE TEST – Missing email
# ─────────────────────────────────────────────


@patch("snug.api.app.save_uploaded_file", side_effect=lambda f: f"/tmp/{f.filename}")
@patch("snug.api.app.process_file_async", side_effect=lambda p: {"employer": "ABC", "salary": "100000"})
@patch("snug.api.app.multi_graph.invoke")
def test_submit_application_missing_email(mock_invoke, mock_process, mock_save, client, fake_payload, fake_files):
    """Email recovery via profile should still succeed with 200 OK."""
    fake_msg = make_fake_msg()
    # Remove email only from final_response but keep in profile to test fallback
    del fake_msg.payload["final_response"]["email"]
    mock_invoke.return_value = {"response": fake_msg}

    bad_payload = {**fake_payload}
    bad_payload["email"] = ""  # simulate missing email in form

    response = client.post("/applications", data=bad_payload, files=fake_files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["application"]["email"] == "nsw.tester@example.com"



# ─────────────────────────────────────────────
# 🧾 FAILURE TEST – Empty multi_agent result
# ─────────────────────────────────────────────
@patch("snug.api.app.save_uploaded_file", side_effect=lambda f: f"/tmp/{f.filename}")
@patch("snug.api.app.process_file_async", side_effect=lambda p: {"employer": "ABC", "salary": "100000"})
@patch("snug.api.app.multi_graph.invoke", return_value=None)
def test_submit_application_empty_result(mock_invoke, mock_process, mock_save, client, fake_payload, fake_files):
    """Should raise 500 when no message is returned by LangGraph."""
    response = client.post("/applications", data=fake_payload, files=fake_files)
    assert response.status_code == 500
    assert "Multi-agent graph returned no final message" in response.json()["detail"]
