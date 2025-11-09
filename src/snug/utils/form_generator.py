from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from faker import Faker
import random, sys, os
from datetime import datetime, timedelta

fake = Faker("en_AU")


# ------------------------------------------------------------
# 1️⃣ Rental Application Form
# ------------------------------------------------------------
def generate_rental_form(state: str, path: str):
    c = canvas.Canvas(path, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(72, 800, f"Rental Application - {state}")
    c.drawString(72, 780, f"First Name: {fake.first_name()}")
    c.drawString(72, 760, f"Last Name: {fake.last_name()}")
    c.drawString(72, 740, f"DOB: {fake.date_of_birth(minimum_age=18, maximum_age=65)}")
    c.drawString(72, 720, f"Address: {fake.address()}")
    if state.upper() == "NSW":
        c.drawString(72, 700, f"Driver License: {fake.bothify(text='DL#######')}")
    elif state.upper() == "VIC":
        c.drawString(72, 700, f"Passport Number: {fake.bothify(text='P########')}")
    c.drawString(72, 680, f"Employer: {fake.company()}")
    c.drawString(72, 660, f"Income: ${fake.random_int(min=50000, max=150000)}")
    c.drawString(72, 640, f"References: {fake.name()}, {fake.phone_number()}")
    c.save()
    print(f"✅ Rental Form generated: {path}")


# ------------------------------------------------------------
# 2️⃣ Bank Statement (synthetic)
# ------------------------------------------------------------
def generate_bank_statement(path: str, months: int = 3):
    c = canvas.Canvas(path, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(72, 800, f"Bank Statement - {fake.company()}")
    start_date = datetime.now() - timedelta(days=30 * months)
    y = 780
    balance = random.uniform(1000, 5000)

    for i in range(months * 10):
        y -= 20
        date = (start_date + timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d")
        desc = random.choice(["Salary", "Groceries", "Rent Payment", "Utilities", "Dining", "Transfer"])
        amount = round(random.uniform(-300, 3000), 2)
        balance += amount
        c.drawString(72, y, f"{date}  {desc:<20} {'$'+str(amount):>10}  {'$'+str(round(balance,2)):>10}")
        if y < 100:
            c.showPage()
            y = 800
            c.setFont("Helvetica", 12)
    c.save()
    print(f"✅ Bank Statement generated: {path}")


# ------------------------------------------------------------
# 3️⃣ Reference Letter
# ------------------------------------------------------------
def generate_reference_letter(path: str):
    c = canvas.Canvas(path, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(72, 800, "Employment Reference Letter")
    c.drawString(72, 780, f"To Whom It May Concern,")
    c.drawString(72, 760, f"This letter is to confirm that {fake.name()} has been employed at {fake.company()}.")
    c.drawString(72, 740, f"They have worked in the role of {fake.job()} since {fake.date_between(start_date='-5y')}.")
    c.drawString(72, 720, f"Throughout their employment, they have demonstrated reliability and professionalism.")
    c.drawString(72, 700, f"For any further information, please contact {fake.name()} at {fake.phone_number()}.")
    c.drawString(72, 660, f"Sincerely,")
    c.drawString(72, 640, f"{fake.name()}, {fake.job()}")
    c.drawString(72, 620, f"{fake.company()}")
    c.save()
    print(f"✅ Reference Letter generated: {path}")


# ------------------------------------------------------------
# 4️⃣ Command-line interface
# ------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs("tests/fixtures/forms", exist_ok=True)
    if len(sys.argv) < 2:
        print("Usage: poetry run python -m src.snug.utils.form_generator <STATE>")
        sys.exit(1)
    state = sys.argv[1]
    rental_path = f"tests/fixtures/forms/{state}_rental_form.pdf"
    bank_path = f"tests/fixtures/forms/{state}_bank_statement.pdf"
    ref_path = f"tests/fixtures/forms/{state}_reference_letter.pdf"

    generate_rental_form(state, rental_path)
    generate_bank_statement(bank_path)
    generate_reference_letter(ref_path)

    print("✅ All synthetic documents created in tests/fixtures/forms/")
