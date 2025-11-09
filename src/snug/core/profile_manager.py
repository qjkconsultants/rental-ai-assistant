import json
import os
from datetime import datetime
from ..logging import log


class ProfileManager:
    """
    Lightweight renter profile storage for reuse across applications.
    Stores verified identity, employment, and rental history.
    """

    def __init__(self, path="data/profiles.json"):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                self.data = json.load(f)
        else:
            self.data = {}

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)
        log.info("profile_saved", count=len(self.data))

    def create_profile(self, user_id: str, info: dict):
        profile = {
            **info,
            "updated": datetime.now().isoformat(),
        }
        self.data[user_id] = profile
        self.save()
        return profile

    def get_profile(self, user_id: str):
        return self.data.get(user_id)

    def all_profiles(self):
        return list(self.data.values())
