import pytest

@pytest.mark.asyncio
async def test_nsw_application_fields(client):
    payload = {"state": "NSW", "income": 90000, "rent": 400}
    response = await client.post("/apply/nsw", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "state" in data
    assert data["state"] == "NSW"
