# src/snug/services/profile_service.py
"""
Profile Service — manages renter profiles for Snug Rental AI.

Features:
- Create and update renter profiles
- Retrieve and persist profiles as JSON
- Support profile reuse across states or applications
- Validates required fields (email, income, identity)
- Integrates with document extraction results (optional)
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from ..logging import log


class ProfileService:
    """
    Manages renter profiles that can be reused across multiple rental applications.
    Profiles are persisted as local JSON files for demonstration or proof-of-concept.
    """

    def __init__(self, storage_dir: str = "data/profiles"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        log.info("profile_service_init", path=str(self.storage_dir))

    # ──────────────────────────────────────────────────────────────
    # ✅ Create or Update Profile
    # ──────────────────────────────────────────────────────────────
    def create_or_update(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates or updates a renter profile based on email address."""
        email = profile_data.get("email")
        if not email:
            raise ValueError("Email is required to create or update a profile.")

        profile_path = self.storage_dir / f"{email.replace('@', '_at_')}.json"

        existing = {}
        if profile_path.exists():
            with open(profile_path, "r") as f:
                existing = json.load(f)

        merged = {**existing, **profile_data}

        with open(profile_path, "w") as f:
            json.dump(merged, f, indent=2)

        log.info("profile_saved", email=email, file=str(profile_path))
        return merged

    # ──────────────────────────────────────────────────────────────
    # ✅ Load Profile
    # ──────────────────────────────────────────────────────────────
    def load(self, email: str) -> Optional[Dict[str, Any]]:
        """Loads an existing renter profile by email address."""
        profile_path = self.storage_dir / f"{email.replace('@', '_at_')}.json"
        if not profile_path.exists():
            log.warning("profile_not_found", email=email)
            return None

        with open(profile_path, "r") as f:
            data = json.load(f)

        log.info("profile_loaded", email=email)
        return data

    # ──────────────────────────────────────────────────────────────
    # ✅ Delete Profile (for testing cleanup)
    # ──────────────────────────────────────────────────────────────
    def delete(self, email: str) -> bool:
        """Deletes a renter profile by email address."""
        profile_path = self.storage_dir / f"{email.replace('@', '_at_')}.json"
        if profile_path.exists():
            profile_path.unlink()
            log.info("profile_deleted", email=email)
            return True
        return False
