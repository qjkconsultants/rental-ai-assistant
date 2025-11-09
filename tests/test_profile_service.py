from snug.services.profile_service import ProfileService

def test_reuse_profile():
    service = ProfileService()
    renter = {"name": "John Doe", "state": "NSW", "income": 85000}
    renter["email"] = "john@example.com"
    service.create_or_update(renter)
    profile = service.load("john@example.com")
    assert profile["name"] == "John Doe"
    assert profile["state"] == "NSW"
