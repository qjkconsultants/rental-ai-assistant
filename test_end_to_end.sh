#!/usr/bin/env bash
BASE="http://127.0.0.1:8000"

echo "1) Health"
curl -s "$BASE/health"
echo -e "\n\n2) DB seed"
curl -s -X POST "$BASE/db/seed"
echo -e "\n\n3) NSW application with docs"
curl -s -X POST "$BASE/applications" \
  -F state=NSW \
  -F email="nsw.tester@example.com" \
  -F first_name="John" \
  -F last_name="Doe" \
  -F dob="1990-05-12" \
  -F phone_number="0400000001" \
  -F current_address="1 Sydney St" \
  -F employment_status="Full-Time" \
  -F employer_name="ABC Pty Ltd" \
  -F employer_contact="0400111222" \
  -F income=95000 \
  -F drivers_license="NSW999999" \
  -F documents=@"/Users/qaisar/Documents/Resume/20250927_Resume/AI_Engineer/Snug_Proof_Of_Concept/snug-rental-ai/tests/fixtures/forms/NSW_rental_form.pdf" \
  -F documents=@"/Users/qaisar/Documents/Resume/20250927_Resume/AI_Engineer/Snug_Proof_Of_Concept/snug-rental-ai/tests/fixtures/forms/NSW_bank_statement.pdf" \
  -F documents=@"/Users/qaisar/Documents/Resume/20250927_Resume/AI_Engineer/Snug_Proof_Of_Concept/snug-rental-ai/tests/fixtures/forms/NSW_reference_letter.pdf"

echo -e "\n\n4) Fetch profile"
curl -s "$BASE/profiles/nsw.tester@example.com"

echo -e "\n\n5) VIC application reuse profile"
curl -s -X POST "$BASE/applications" \
  -F state=VIC \
  -F email="nsw.tester@example.com" \
  -F first_name="John" \
  -F last_name="Doe" \
  -F dob="1990-05-12" \
  -F phone_number="0400000001" \
  -F current_address="1 Sydney St" \
  -F employment_status="Full-Time" \
  -F employer_name="ABC Pty Ltd" \
  -F employer_contact="0400111222" \
  -F income=95000

echo -e "\n\n6) List applications"
curl -s "$BASE/applications"

echo -e "\n\n7) Affordability check NSW"
curl -s -X POST "$BASE/apply/nsw" \
  -H "Content-Type: application/json" \
  -d '{"state":"NSW","income":90000,"rent":450}'

echo -e "\n\n8) Compliance check"
curl -s -X POST "$BASE/compliance/check" \
  -H "Content-Type: application/json" \
  -d '{"state":"NSW","profile":{"email":"nsw.tester@example.com","income":95000,"drivers_license":"NSW999999"},"extracted":{"payslip.pdf":{"income_verified":true}}}'

echo -e "\n\n9) RAG query"
curl -s -X POST "$BASE/rag/query" \
  -H "Content-Type: application/json" \
  -d '{"query":"What documents do I need for an NSW rental application?"}'

echo -e "\n\n10) Memory status"
curl -s "$BASE/memory/status"
echo -e "\n\nDone."
