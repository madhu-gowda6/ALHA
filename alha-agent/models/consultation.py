from typing import Optional
from pydantic import BaseModel


class Consultation(BaseModel):
    session_id: str
    farmer_phone: str
    animal_type: str
    disease_name: Optional[str] = None
    confidence_score: Optional[float] = None
    severity: Optional[str] = None
    vet_assigned: Optional[str] = None
    vet_phone: Optional[str] = None
    treatment_summary: Optional[str] = None
    timestamp: Optional[str] = None
    kb_citations: list[str] = []
