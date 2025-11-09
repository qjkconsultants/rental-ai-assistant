from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Literal, Dict, Any

class Reference(BaseModel):
    name: str
    relationship: str
    contact: str

class RentalHistory(BaseModel):
    address: str
    duration_months: int

class Profile(BaseModel):
    email: EmailStr
    first_name: str
    middle_name: str = ""
    last_name: str
    dob: str
    drivers_license: Optional[str] = None
    passport_number: Optional[str] = None
    phone_number: str
    current_address: str
    previous_address: str
    employment_status: str
    employer_name: str
    employer_contact: str
    income: float
    rental_history: List[RentalHistory] = Field(default_factory=list)
    references: List[Reference] = Field(default_factory=list)

class Application(BaseModel):
    state: Literal["NSW","VIC"]
    profile: Dict[str, Any]
    documents: List[str] = Field(default_factory=list)

class ExtractedPayslip(BaseModel):
    employer_name: Optional[str] = None
    gross_income: Optional[float] = None
    net_income: Optional[float] = None
    pay_period_start: Optional[str] = None
    pay_period_end: Optional[str] = None
    pay_date: Optional[str] = None
    abn: Optional[str] = None
