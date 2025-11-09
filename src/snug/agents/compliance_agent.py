import os
import json
import re
from typing import Dict, Any, List, Optional
from ..core.db import DB
from ..core.audit import Audit
from ..validation.state_validator import StateValidator
from ..mcp.schema import MCPMessage
from ..logging import log
from ..agents.doc_processor import DocumentProcessor


class ComplianceAgent:
    """
    Multi-state Compliance Agent for rental applications.

    Responsibilities:
    ───────────────────────────────────────────────────────
    • Load rules from DB and/or JSON per state (NSW, VIC, etc.)
    • Merge extracted AI data (e.g., from payslips)
    • Validate renter profiles against required documents
    • Return structured compliance summary

    Snug Values:
    - Integrity: Full audit trail of compliance checks
    - Customer First: Graceful handling of missing data
    - Excellence: Clean modular structure
    - Inclusivity: Human-readable structured responses
    """

    def __init__(
        self,
        db: DB,
        validator: StateValidator,
        audit: Audit,
        rules_path: str = "config/state_rules.json",
    ):
        self.db = db
        self.validator = validator
        self.audit = audit
        self.doc_processor = DocumentProcessor()
        self.rules_path = rules_path
        self.rules = self._load_state_rules()

    # ─────────────────────────────────────────────
    # 📘 LOAD MULTI-STATE RULES
    # ─────────────────────────────────────────────
    def _load_state_rules(self) -> dict:
        """Load fallback JSON rule definitions per state."""
        if os.path.exists(self.rules_path):
            try:
                with open(self.rules_path, "r") as f:
                    rules = json.load(f)
                    log.info("state_rules_loaded", count=len(rules))
                    return rules
            except Exception as e:
                log.error("state_rules_load_failed", error=str(e))
        return {}

    # ─────────────────────────────────────────────
    # ⚙️ RULE EVALUATION
    # ─────────────────────────────────────────────
    def _evaluate_rules(self, state: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate compliance rules for a given state.
        Merges rules from DB + static config file.
        """
        db_rules = self.db.conn.execute(
            "SELECT rule_name, rule_text FROM compliance_rules WHERE state=?",
            (state,),
        ).fetchall()
        static_rules = self.rules.get(state, [])
        all_rules = db_rules or [(r, "") for r in static_rules]

        failed = []
        for rule_name, _ in all_rules:
            if "income" in rule_name and not profile.get("income"):
                failed.append(rule_name)
            elif "identity" in rule_name and not (
                profile.get("drivers_license") or profile.get("passport_number")
            ):
                failed.append(rule_name)
            elif "reference" in rule_name and not profile.get("references"):
                failed.append(rule_name)
            elif "rental_history" in rule_name and not profile.get("rental_history"):
                failed.append(rule_name)

        passed = [r[0] for r in all_rules if r[0] not in failed]

        self.audit.log_event("compliance", "checked", f"{state}: failed={failed}")
        return {"passed": passed, "failed": failed, "total_rules": len(all_rules)}

    # ─────────────────────────────────────────────
    # 📄 AI DOCUMENT MERGING
    # ─────────────────────────────────────────────
    def _merge_extracted_data(
        self, profile: Dict[str, Any], extracted: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge AI-extracted document data into renter profile."""
        if not extracted:
            return profile

        payslip = extracted.get("payslip", extracted)
        if payslip.get("salary") and not profile.get("income"):
            try:
                profile["income"] = float(
                    payslip["salary"].replace(",", "").replace("$", "")
                )
            except Exception:
                log.warn("invalid_income_value", value=payslip.get("salary"))

        if payslip.get("employer") and not profile.get("employer"):
            profile["employer"] = payslip["employer"]

        return profile

    # ─────────────────────────────────────────────
    # 🧩 MAIN COMPLIANCE PIPELINE
    # ─────────────────────────────────────────────
    def check_application(
        self,
        state: str,
        profile: Dict[str, Any],
        extracted: Optional[Dict[str, Any]] = None,
        payslip_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full compliance pipeline:
        1️⃣ Extracts data from payslip (if path provided)
        2️⃣ Merges with renter profile
        3️⃣ Validates required fields (via StateValidator)
        4️⃣ Evaluates rules for that state
        """
        # Step 1 – AI document extraction
        if payslip_path and os.path.exists(payslip_path):
            extracted = {"payslip": self.doc_processor.process_payslip(payslip_path)}

        # Step 2 – Merge extracted AI data into profile
        profile = self._merge_extracted_data(profile, extracted)

        # Step 3 – Validate state-specific required fields
        missing = self.validator.validate(state, profile)

        # Step 4 – Evaluate compliance rules
        rule_eval = self._evaluate_rules(state, profile)

        return {
            "missing": missing,
            "compliance_summary": rule_eval,
            "profile": profile,
        }

    # ─────────────────────────────────────────────
    # 🧠 LANGGRAPH NODE HANDLER
    # ─────────────────────────────────────────────
    def handle(self, msg: MCPMessage) -> MCPMessage:
        """LangGraph-compatible message handler."""
        p = msg.payload
        result = self.check_application(
            state=p.get("state", ""),
            profile=p.get("profile", {}),
            extracted=p.get("extracted", {}),
            payslip_path=p.get("payslip_path"),
        )
        p.update(result)

        log.info(
            "compliance_agent",
            state=p.get("state"),
            missing=len(result["missing"]),
            failed=len(result["compliance_summary"]["failed"]),
        )

        return MCPMessage(
            sender="compliance_agent",
            receiver="guardrails_agent",
            type="guardrails",
            payload=p,
            context=msg.context,
        )
