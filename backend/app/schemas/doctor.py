from pydantic import BaseModel, ConfigDict, Field


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

class DoctorCreate(BaseModel):
    """Données envoyées par un médecin pour créer son profil."""

    model_config = ConfigDict(str_strip_whitespace=True)

    specialty: str = Field(min_length=2, max_length=100)
    bio: str | None = Field(default=None, max_length=1000)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    consultation_duration_min: int = Field(default=20, ge=5, le=120)


class DoctorUpdate(BaseModel):
    """Données envoyées pour modifier son profil : tout est facultatif."""

    model_config = ConfigDict(str_strip_whitespace=True)

    specialty: str | None = Field(default=None, min_length=2, max_length=100)
    bio: str | None = Field(default=None, max_length=1000)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    consultation_duration_min: int | None = Field(default=None, ge=5, le=120)    