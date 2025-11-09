import os
from snug.core.db import DB
import json

def test_save_and_retrieve_application(tmp_path, monkeypatch):
    """Test saving and retrieving an application end-to-end."""
    # Point the working directory to tmp_path so DB uses a clean snug.db
    monkeypatch.chdir(tmp_path)

    db = DB()  # uses default snug.db path internally
    payload = {"email": "demo@example.com", "state": "NSW", "amount": 1000}
    db.save_application(payload)

    apps = db.list_applications()
    assert any("demo@example.com" in json.dumps(a) for a in apps)


def test_save_profile_and_retrieve(tmp_path, monkeypatch):
    """Test saving and retrieving a renter profile."""
    monkeypatch.chdir(tmp_path)

    db = DB()
    profile = {"email": "user@example.com", "income": 50000}
    db.save_profile("user@example.com", profile)

    out = db.get_profile("user@example.com")
    assert out["income"] == 50000
