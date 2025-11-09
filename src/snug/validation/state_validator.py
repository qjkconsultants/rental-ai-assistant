# src/snug/validation/state_validator.py
from typing import Sequence

class StateValidator:
    def __init__(self, state_config: dict[str, Sequence[str]]):
        self.state_config = state_config

    def validate(self, state: str, payload: dict) -> list[str]:
        req = self.state_config.get(state.upper())
        if not req:
            return [f"Unsupported state: {state}"]
        missing = [k for k in req if not payload.get(k)]
        return missing
