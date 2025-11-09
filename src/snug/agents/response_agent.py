# src/snug/agents/response_agent.py
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from ..mcp.schema import MCPMessage
from ..settings import settings
from ..logging import log

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


class ResponseAgent:
    """
    🧠 ResponseAgent — final step in the multi-agent workflow.
    Combines compliance, guardrail, and RAG outputs, producing
    a privacy-safe and structured final response.
    """

    def __init__(self, llm_client: Optional[Any] = None):
        self.llm = llm_client
        if self.llm is None and settings.openai_api_key and OpenAI is not None:
            self.llm = OpenAI(api_key=settings.openai_api_key)

    # ─────────────────────────────────────────────
    # 🔒 SAFE SUMMARIZATION HELPERS
    # ─────────────────────────────────────────────
    @staticmethod
    def _build_safe_profile_summary(profile: Dict[str, Any], state: Optional[str]) -> str:
        """Create a non-sensitive summary of renter data."""
        if not profile:
            return "No profile information provided."

        parts: List[str] = []
        if state:
            parts.append(f"State: {state}")
        if profile.get("employment_status"):
            parts.append(f"Employment: {profile['employment_status']}")
        if profile.get("income"):
            parts.append(f"Declared income: {profile['income']}")
        rh = profile.get("rental_history") or []
        if isinstance(rh, list) and rh:
            parts.append(f"Rental history entries: {len(rh)}")

        return " | ".join(parts) if parts else "Basic renter profile provided."

    @staticmethod
    def _summarize_rules(rules: List[Dict[str, Any]], label: str) -> str:
        if not rules:
            return f"No {label.lower()} rules recorded."
        lines = [f"{label} rules:"]
        for r in rules:
            lines.append(f"- {r.get('rule_name') or 'Unnamed rule'}: {r.get('rule_text') or ''}")
        return "\n".join(lines)

    @staticmethod
    def _summarize_guardrails(findings: List[Dict[str, Any]]) -> str:
        if not findings:
            return "No guardrails violations detected."
        lines = ["Guardrails findings:"]
        for f in findings:
            field = f.get("field", "unknown_field")
            sev = f.get("severity", "info")
            reason = f.get("reason", "")
            lines.append(f"- [{sev}] {field}: {reason}")
        return "\n".join(lines)

    @staticmethod
    def _summarize_memory_snippet(memory_snippet: List[Dict[str, Any]]) -> str:
        if not memory_snippet:
            return "No prior memory entries found."
        lines = ["Recent related context:"]
        for m in memory_snippet:
            q = m.get("query", "<no query>")
            docs = m.get("retrieved_docs", [])
            lines.append(f"* Query: {q}")
            if docs:
                lines.append(f"  - Example doc: {docs[0][:100]}...")
        return "\n".join(lines)

    # ─────────────────────────────────────────────
    # 🚀 MAIN HANDLER
    # ─────────────────────────────────────────────
    def handle(self, msg: MCPMessage) -> MCPMessage:
        """Generate a structured, final response."""
        p = msg.payload or {}

        state = p.get("state")
        profile = p.get("profile", {}) or {}
        email = profile.get("email") or p.get("email")  # ✅ fallback
        missing = p.get("missing", []) or []

        kb = p.get("kb", {}) or {}
        retrieved_docs = kb.get("retrieved_docs", [])
        compliance_rules = p.get("compliance_rules", []) or []
        guardrails_findings = p.get("guardrails_findings", []) or []
        memory_snippet = p.get("memory_snippet", []) or []

        user_query = p.get("query", "User submitted a rental application without a question.")

        # ───────────── Summarize context ─────────────
        safe_summary = self._build_safe_profile_summary(profile, state)
        rules_summary = self._summarize_rules(compliance_rules, "Compliance")
        guardrails_summary = self._summarize_guardrails(guardrails_findings)
        memory_summary = self._summarize_memory_snippet(memory_snippet)

        context_block = "\n\n".join(
            [
                f"Profile summary: {safe_summary}",
                f"Missing fields: {missing or 'None'}",
                rules_summary,
                guardrails_summary,
                "Retrieved guidance documents:",
                "\n".join(f"- {t}" for t in retrieved_docs) or "None.",
                memory_summary,
            ]
        )

        # ───────────── Prompt construction ─────────────
        system_prompt = (
            "You are an AI assistant helping Australian renters complete applications.\n"
            "Follow these rules:\n"
            "- Use only the provided context; do not invent details.\n"
            "- Do not reveal or guess personal identifiers (emails, IDs, DOBs).\n"
            "- Offer clear, concise, and polite guidance.\n"
        )

        user_prompt = (
            f"Renter query:\n{user_query}\n\n"
            f"Context:\n{context_block}\n\n"
            "Write a short, friendly, and informative response."
        )

        # ───────────── Generate or fallback ─────────────
        if self.llm:
            try:
                rsp = self.llm.chat.completions.create(
                    model=settings.openai_model or "gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    max_tokens=400,
                )
                message = rsp.choices[0].message.content.strip()
            except Exception as e:
                log.error("response_agent_llm_error", error=str(e))
                message = (
                    "Unable to generate a full answer now. "
                    "Please verify that required identity and income documents are provided."
                )
        else:
            message = (
                f"Please ensure all required ID, income, and rental history documents "
                f"are provided for {state or 'your state'}’s rental application."
            )

        # ───────────── Build structured result ─────────────
        final = {
            "state": state,
            "email": email,
            "query": user_query,
            "message": message,
            "missing": missing,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context_used": {
                "retrieved_docs": retrieved_docs,
                "compliance_rules": [r.get("rule_name") for r in compliance_rules],
                "guardrails_findings": guardrails_findings,
            },
        }

        # ✅ Always ensure `profile` and `email` exist
        if not profile.get("email") and email:
            profile["email"] = email
        final["profile"] = profile
        final["email"] = profile.get("email") or email

        if not final.get("email"):
            log.warning(
                "response_agent_missing_email",
                payload_keys=list(p.keys()),
                profile_keys=list(profile.keys()),
            )

        # Attach final structured response to message payload
        p["final_response"] = final
        # ✅ Ensure timestamp always present at top-level (redundant but explicit)
        if "timestamp" not in p:
            p["timestamp"] = datetime.now(timezone.utc).isoformat()        
        p["profile"] = profile
        p["email"] = final.get("email")

        log.info("response_agent_done", state=state, missing=len(missing), email=final.get("email"))
        return msg.model_copy(update={"payload": p})
