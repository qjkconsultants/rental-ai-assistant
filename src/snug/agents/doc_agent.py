from ..ai.extractor import PayslipExtractor
from ..core.audit import Audit

class DocumentAgent:
    def __init__(self, extractor: PayslipExtractor, audit: Audit):
        self.extractor, self.audit = extractor, audit

    def run(self, ctx: dict) -> dict:
        email = ctx["profile"]["email"]
        payslips = [p for p in ctx.get("documents", []) if p.lower().endswith(".pdf")]
        ctx.setdefault("extracted", {})
        for path in payslips:
            data = self.extractor.extract(path)
            ctx["extracted"]["payslip"] = data
            self.audit.info(email, "payslip_extracted", f"fields={list(data.keys())}")
        return ctx
