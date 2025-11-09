import pdfplumber
import re
import os
from ..logging import log


class DocumentProcessor:
    """
    AI-powered Document Processor.
    Extracts structured fields from payslips or similar documents.
    Demonstrates automated verification capability.
    """

    def process_payslip(self, path: str) -> dict:
        """Extract salary, employer, and employee info from a payslip PDF."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Document not found: {path}")

        with pdfplumber.open(path) as pdf:
            text = "\n".join(
                page.extract_text() for page in pdf.pages if page.extract_text()
            )

        # Extract entities using regex
        salary = re.search(r"\$?\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", text)
        employer = re.search(r"Employer[:\-]?\s*(.*)", text)
        employee = re.search(r"Employee[:\-]?\s*(.*)", text)
        period = re.search(r"Pay Period[:\-]?\s*(.*)", text)

        result = {
            "employer": employer.group(1).strip() if employer else None,
            "employee": employee.group(1).strip() if employee else None,
            "salary": salary.group(1).strip() if salary else None,
            "period": period.group(1).strip() if period else None,
        }

        log.info("doc_parsed", file=os.path.basename(path), result=result)
        return result
