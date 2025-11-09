from snug.validation.state_validator import StateValidator
from snug.state_config import STATE_CONFIG

def test_vic_ok():
    v = StateValidator(STATE_CONFIG)
    payload = {k: "x" for k in STATE_CONFIG["VIC"]}
    assert v.validate("VIC", payload) == []

def test_nsw_missing():
    v = StateValidator(STATE_CONFIG)
    payload = {"first_name":"A","last_name":"B","dob":"1990-01-01"}  # incomplete
    missing = v.validate("NSW", payload)
    assert "drivers_license" in missing
