from ..core.audit import Audit
from ..validation.state_validator import StateValidator

class ReasonAgent:
    def __init__(self, validator: StateValidator, audit: Audit):
        self.validator, self.audit = validator, audit

    def run(self, ctx: dict) -> dict:
        state = ctx["state"]
        profile = ctx["profile"].copy()
        # Merge extracted facts into profile if present
        ps = ctx.get("extracted", {}).get("payslip") or {}
        if ps.get("gross_income") and not profile.get("income"):
            profile["income"] = float(ps["gross_income"])
        ctx["profile"] = profile
        missing = self.validator.validate(state, profile)
        ctx["missing"] = missing
        msg = "ok" if not missing else f"missing={missing}"
        self.audit.info(profile["email"], "state_validate", msg)
        return ctx
