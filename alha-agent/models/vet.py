from pydantic import BaseModel


class Vet(BaseModel):
    vet_id: str
    name: str
    phone: str
    speciality: str
    lat: float
    lon: float
    district: str
    state: str
