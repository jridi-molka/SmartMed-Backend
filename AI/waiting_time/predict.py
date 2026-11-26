"""Prédiction du temps d'attente d'un patient (version simple : une formule).

Même logique que celle utilisée pour fabriquer les données simulées :
attente = patients devant soi x durée d'une consultation + retard du médecin
          + petit supplément aux heures de pointe et le lundi.
Plus tard, un modèle de ML pourra remplacer le calcul, avec la même signature.
"""

HEURES_DE_POINTE = (10, 11, 14, 15)
SUPPLEMENT_POINTE_MIN = 6   # minutes ajoutées aux heures de pointe
SUPPLEMENT_LUNDI_MIN = 2    # minutes ajoutées le lundi (0 = lundi)


def predict_wait_time(
    patients_before: int,
    avg_consultation_min: float,
    hour_of_day: int,
    day_of_week: int,
    doctor_avg_delay_min: float,
) -> int:
    """Renvoie l'attente estimée, en minutes."""
    wait = patients_before * avg_consultation_min + doctor_avg_delay_min
    if hour_of_day in HEURES_DE_POINTE:
        wait += SUPPLEMENT_POINTE_MIN
    if day_of_week == 0:
        wait += SUPPLEMENT_LUNDI_MIN
    return round(max(wait, 0))


if __name__ == "__main__":
    # Exemple : 3 patients devant, consultation de 15 min, 10h, lundi, médecin en retard de 5 min
    print(predict_wait_time(3, 15, 10, 0, 5), "minutes")