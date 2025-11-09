# src/snug/ai/extractor.py
import json
from typing import Dict, Any
import pdfplumber
from ..settings import settings

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

class PayslipExtractor:
    def __init__(self, llm_client=None):
        self.llm = llm_client
        if self.llm is None and settings.openai_api_key and OpenAI is not None:
            self.llm = OpenAI(api_key=settings.openai_api_key)

    def _read_pdf_text(self, path: str) -> str:
        chunks = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                chunks.append(page.extract_text() or "")
        return "\n".join(chunks).strip()

    def _fallback_parse(self, text: str) -> Dict[str, Any]:
        # very light heuristics so tests don’t depend on LLM
        lines = [l for l in text.splitlines() if l.strip()]
        gross = next((l for l in lines if "Income:" in l or "Gross" in l), "")
        employer = next((l for l in lines if "Employer:" in l), "")
        return {
            "employee_name": "",
            "employer_name": employer.replace("Employer:", "").strip() if employer else "",
            "pay_date": "",
            "gross_income": float("".join(ch for ch in gross if ch.isdigit() or ch == ".")) if gross else 0.0,
            "source": "fallback"
        }

    def extract_from_pdf(self, path: str) -> Dict[str, Any]:
        text = self._read_pdf_text(path)
        if not text:
            return {"error": "empty_payslip"}
        if not self.llm:
            return {"payslip": self._fallback_parse(text)}

        prompt = (
            "Extract JSON with keys: employee_name, employer_name, pay_date, gross_income "
            "from the following payslip text. Return strictly JSON with those keys only.\n\n"
            f"{text}"
        )
        try:
            rsp = self.llm.chat.completions.create(
                model=settings.openai_model or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a precise information extractor."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            data = json.loads(rsp.choices[0].message.content)
            data["source"] = "llm"
            # coerce types
            if "gross_income" in data:
                try: data["gross_income"] = float(data["gross_income"])
                except: data["gross_income"] = 0.0
            return {"payslip": data}
        except Exception:
            # never fail hard in ingestion: fall back
            return {"payslip": self._fallback_parse(text)}
