from pydantic import BaseModel


class DoctorOut(BaseModel):
    """Ce que l'API renvoie pour un médecin (jamais d'e-mail ni de mot de passe)."""

    id: int
    user_id: int
    name: str
    specialty: str
    bio: str | None = None
    address: str | None = None
    city: str | None = None
    consultation_duration_min: int


class DoctorListOut(BaseModel):
    """Réponse de la recherche : la page demandée + le nombre total de résultats."""

    items: list[DoctorOut]
    total: int