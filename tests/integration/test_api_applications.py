from fastapi.testclient import TestClient
from snug.api.app import app

client = TestClient(app)

def test_submit_application_ok(tmp_payslip):
    files = [("documents", (tmp_payslip.name, open(tmp_payslip, "rb"), "application/pdf"))]
    data = {
        "state":"VIC", "email":"t@example.com",
        "first_name":"T","middle_name":"","last_name":"User","dob":"1990-01-01",
        "phone_number":"0400","current_address":"addr1","previous_address":"",
        "employment_status":"Full-time","employer_name":"Acme","employer_contact":"0400",
        "income":"0","drivers_license":"","passport_number":"P1"
    }
    r = client.post("/applications", data=data, files=files)
    assert r.status_code == 200
    body = r.json()
    assert "application" in body
    assert "missing" in body["application"]
    assert isinstance(body["application"]["missing"], list)
