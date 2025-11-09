EXTRACT_PAYSLIP_JSON = """You extract fields from a payslip.
Return ONLY compact JSON with keys:
employer_name, gross_income, net_income, pay_period_start, pay_period_end, pay_date, abn
- Numbers as floats
- Dates as YYYY-MM-DD
Text:
{payslip_text}
"""
