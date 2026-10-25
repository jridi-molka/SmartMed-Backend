"""
generate_data.py
----------------
Génère les 3 jeux de données simulés du module IA de SmartMed :
    - doctors.csv
    - reviews.csv
    - waiting_history.csv

Utilisation (depuis le dossier AI/) :
    python data/generate_data.py

Le script crée DEUX versions des mêmes données :

  - AI/data/reference/ : la version PARFAITE (vérité terrain). Elle ne sert
    qu'à vérifier, à la fin, que le nettoyage a bien remis les choses en état.
  - AI/data/raw/ : la version BRUTE, point de départ du pipeline, avec des
    anomalies injectées VOLONTAIREMENT (doublons, valeurs manquantes,
notes impossibles...) pour simuler les imperfections de vraies données
d'utilisateurs. Le nombre exact d'anomalies est noté dans
AI/data/raw/anomalies_injected.json, afin de pouvoir vérifier que le script de
nettoyage les retrouve toutes.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 1. RÉGLAGES
# ---------------------------------------------------------------------------

# La "graine" fixe le hasard : à chaque exécution, on obtient EXACTEMENT
# les mêmes données. Pratique pour que toute l'équipe travaille sur les mêmes.
SEED = 42
rng = np.random.default_rng(SEED)

NB_DOCTORS = 50              # nombre de médecins à créer
WAITING_RECORDS_PER_DOCTOR = 80   # nombre de lignes d'historique par médecin

# Dossier où écrire les CSV : le dossier de ce script (AI/data/)
OUTPUT_DIR = Path(__file__).resolve().parent

# Centre de Tunis : on place les médecins autour de ce point
TUNIS_LAT, TUNIS_LON = 36.8065, 10.1815

# Spécialités et durée moyenne typique d'une consultation (en minutes)
SPECIALTIES = {
    "Généraliste": 15,
    "Cardiologue": 25,
    "Dermatologue": 15,
    "Pédiatre": 20,
    "Gynécologue": 25,
    "Ophtalmologue": 20,
    "Dentiste": 30,
    "ORL": 20,
    "Orthopédiste": 25,
    "Psychiatre": 45,
}

FIRST_NAMES = ["Ahmed", "Mohamed", "Sami", "Karim", "Youssef", "Walid", "Hichem",
               "Sarra", "Mariem", "Ines", "Rim", "Amel", "Leila", "Nesrine", "Salma"]
LAST_NAMES = ["Ben Salah", "Trabelsi", "Jebali", "Gharbi", "Mansouri", "Bouazizi",
              "Chaabane", "Hammami", "Khelifi", "Mejri", "Sassi", "Zouari", "Ayari"]

# ---------------------------------------------------------------------------
# 2. PHRASES POUR LES AVIS (en français)
# ---------------------------------------------------------------------------

POSITIVE = [
    "Excellent médecin, très à l'écoute.",
    "Consultation très professionnelle, je recommande.",
    "Médecin sympathique et compétent.",
    "Très bon accueil et explications claires.",
    "Cabinet propre et personnel agréable.",
    "Il a pris le temps de bien m'examiner.",
    "Rendez-vous respecté, très satisfait.",
]
NEUTRAL = [
    "Consultation correcte, sans plus.",
    "Médecin compétent mais un peu pressé.",
    "Service moyen, rien de particulier à signaler.",
    "Le prix est correct, l'attente un peu longue.",
    "Ça va, j'ai eu ce que je venais chercher.",
]
NEGATIVE = [
    "Beaucoup trop d'attente, plus d'une heure.",
    "Médecin peu aimable, je ne reviendrai pas.",
    "Consultation très rapide, je n'ai rien compris.",
    "Accueil désagréable à la réception.",
    "Prix trop élevé pour la qualité du service.",
    "Cabinet sale et mal organisé.",
    "Rendez-vous en retard de presque deux heures.",
]


# ---------------------------------------------------------------------------
# 3. GÉNÉRATION DES MÉDECINS
# ---------------------------------------------------------------------------

def generate_doctors():
    """Crée la liste des médecins (sans la note moyenne, calculée plus tard)."""
    rows = []
    specialty_names = list(SPECIALTIES.keys())

    for doctor_id in range(1, NB_DOCTORS + 1):
        specialty = rng.choice(specialty_names)
        # Durée de consultation = durée typique de la spécialité +/- quelques minutes
        avg_consultation = SPECIALTIES[specialty] + rng.integers(-3, 4)

        rows.append({
            "doctor_id": doctor_id,
            "name": f"Dr. {rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
            "specialty": specialty,
            # Position : un petit décalage aléatoire autour de Tunis
            "latitude": round(TUNIS_LAT + rng.normal(0, 0.03), 5),
            "longitude": round(TUNIS_LON + rng.normal(0, 0.03), 5),
            "avg_consultation_min": int(avg_consultation),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4. GÉNÉRATION DES AVIS
# ---------------------------------------------------------------------------

def rating_to_sentiment(rating):
    """Convertit une note (1 à 5) en sentiment."""
    if rating >= 4:
        return "positive"
    if rating == 3:
        return "neutral"
    return "negative"


def make_comment(sentiment):
    """Fabrique un commentaire cohérent avec le sentiment."""
    pool = {"positive": POSITIVE, "neutral": NEUTRAL, "negative": NEGATIVE}[sentiment]
    comment = rng.choice(pool)
    # Une fois sur 3, on ajoute une 2e phrase du même ton pour varier
    # (on exclut la 1re phrase pour ne jamais la répéter)
    if rng.random() < 0.33:
        others = [phrase for phrase in pool if phrase != comment]
        comment += " " + rng.choice(others)
    return comment


def generate_reviews(doctors):
    """Crée des avis pour chaque médecin."""
    rows = []
    review_id = 1

    for doctor_id in doctors["doctor_id"]:
        # Chaque médecin a une "vraie qualité" cachée entre 2.5 et 5
        # Les patients ne la voient pas : ils donnent une note proche, avec du bruit.
        true_quality = rng.uniform(2.5, 5.0)
        nb_reviews = rng.integers(5, 41)   # entre 5 et 40 avis

        for _ in range(nb_reviews):
            rating = int(np.clip(round(true_quality + rng.normal(0, 0.9)), 1, 5))
            sentiment = rating_to_sentiment(rating)
            rows.append({
                "review_id": review_id,
                "doctor_id": int(doctor_id),
                "rating": rating,
                "comment": make_comment(sentiment),
                "sentiment": sentiment,
            })
            review_id += 1

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 5. GÉNÉRATION DE L'HISTORIQUE D'ATTENTE
# ---------------------------------------------------------------------------

def generate_waiting_history(doctors):
    """
    Crée l'historique du temps d'attente.

    LA LOGIQUE CACHÉE (ce que le futur modèle devra retrouver) :
        attente = (patients devant moi x durée d'une consultation)
                  + retard habituel du médecin
                  + effet des heures de pointe
                  + un peu de hasard
    """
    rows = []
    record_id = 1

    for _, doctor in doctors.iterrows():
        # Chaque médecin a un retard habituel caché (certains sont toujours en retard)
        usual_delay = rng.uniform(0, 15)

        for _ in range(WAITING_RECORDS_PER_DOCTOR):
            patients_before = int(rng.integers(0, 13))     # 0 à 12 patients devant
            hour_of_day = int(rng.integers(8, 18))          # de 8h à 17h
            day_of_week = int(rng.integers(0, 6))           # 0 = lundi ... 5 = samedi

            # Heures de pointe : fin de matinée et début d'après-midi
            rush_effect = 0
            if hour_of_day in (10, 11, 14, 15):
                rush_effect = rng.uniform(3, 10)
            # Le lundi est souvent plus chargé
            if day_of_week == 0:
                rush_effect += rng.uniform(0, 5)

            noise = rng.normal(0, 4)   # le hasard de la vraie vie

            actual_wait = (
                patients_before * doctor["avg_consultation_min"]
                + usual_delay
                + rush_effect
                + noise
            )
            # Un temps d'attente ne peut pas être négatif
            actual_wait = max(0, round(actual_wait, 1))

            rows.append({
                "record_id": record_id,
                "doctor_id": int(doctor["doctor_id"]),
                "patients_before": patients_before,
                "avg_consultation_min": int(doctor["avg_consultation_min"]),
                "hour_of_day": hour_of_day,
                "day_of_week": day_of_week,
                "actual_wait_min": actual_wait,
            })
            record_id += 1

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 6. ANOMALIES VOLONTAIRES (simulation de vraies données "sales")
# ---------------------------------------------------------------------------

# Générateur de hasard SÉPARÉ du premier : il ne modifie donc pas les données
# propres générées plus haut (elles restent identiques à chaque exécution).
rng_noise = np.random.default_rng(SEED + 1)


def pick(pool, n):
    """Choisit n lignes DIFFÉRENTES dans 'pool' et les retire du pool.
    Ainsi, une même ligne n'a jamais deux anomalies à la fois."""
    chosen = [int(i) for i in rng_noise.choice(pool, size=n, replace=False)]
    for i in chosen:
        pool.remove(i)
    return chosen


def messy(text):
    """Abîme un texte : espaces autour et double espace à l'intérieur."""
    return "  " + text.replace(" ", "  ", 1) + "   "


def inject_anomalies(doctors, reviews, waiting):
    """Renvoie 3 tableaux 'bruts' (avec anomalies) et le détail des anomalies."""
    log = {}

    # ---------------- médecins ----------------
    d = doctors.copy().reset_index(drop=True)
    pool = list(range(len(d)))
    for i in pick(pool, 4):
        d.loc[i, "name"] = "  " + d.loc[i, "name"] + " "
    dup = pick(pool, 3)
    d = pd.concat([d, d.loc[dup]], ignore_index=True)
    log["doctors"] = {"doublons": 3, "textes_corriges": 4}

    # ---------------- avis ----------------
    r = reviews.copy().reset_index(drop=True)
    r["rating"] = r["rating"].astype("Int64")      # entier qui accepte "vide"
    pool = list(range(len(r)))

    bad = pick(pool, 10)
    r.loc[bad, "rating"] = rng_noise.choice([0, 6, 7, 9], size=10)
    for i in pick(pool, 10):
        r.loc[i, "rating"] = pd.NA
    for k, i in enumerate(pick(pool, 8)):
        r.loc[i, "comment"] = np.nan if k % 2 == 0 else "   "
    for i in pick(pool, 6):
        r.loc[i, "doctor_id"] = 999                # médecin qui n'existe pas
    for i in pick(pool, 15):
        r.loc[i, "comment"] = messy(r.loc[i, "comment"])
    wrong = ["positif", "???", "POSITIVE", "bad"]
    for i in pick(pool, 8):
        r.loc[i, "sentiment"] = rng_noise.choice(wrong)
    dup = pick(pool, 20)
    r = pd.concat([r, r.loc[dup]], ignore_index=True)
    log["reviews"] = {
        "doublons": 20, "note_invalide": 10, "note_manquante": 10,
        "commentaire_vide": 8, "medecin_inconnu": 6,
        "textes_corriges": 15, "sentiments_corriges": 8,
    }

    # ---------------- historique d'attente ----------------
    w = waiting.copy().reset_index(drop=True)
    pool = list(range(len(w)))
    for i in pick(pool, 12):
        w.loc[i, "actual_wait_min"] = -float(rng_noise.integers(5, 31))
    for i in pick(pool, 8):
        w.loc[i, "patients_before"] = -int(rng_noise.integers(1, 4))
    for i in pick(pool, 10):
        w.loc[i, "hour_of_day"] = int(rng_noise.integers(24, 31))
    for i in pick(pool, 5):
        w.loc[i, "day_of_week"] = int(rng_noise.integers(7, 10))
    for i in pick(pool, 15):
        w.loc[i, "actual_wait_min"] = np.nan
    dup = pick(pool, 25)
    w = pd.concat([w, w.loc[dup]], ignore_index=True)
    log["waiting_history"] = {
        "doublons": 25, "attente_negative": 12, "patients_negatifs": 8,
        "heure_invalide": 10, "jour_invalide": 5, "valeur_manquante": 15,
    }

    return d, r, w, log


# ---------------------------------------------------------------------------
# 7. PROGRAMME PRINCIPAL
# ---------------------------------------------------------------------------

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # accents lisibles dans Git Bash

    doctors = generate_doctors()
    reviews = generate_reviews(doctors)
    waiting = generate_waiting_history(doctors)

    # La note moyenne et le nombre d'avis des médecins sont CALCULÉS à partir
    # des avis : ainsi les 3 fichiers sont cohérents entre eux.
    stats = (
        reviews.groupby("doctor_id")["rating"]
        .agg(avg_rating="mean", reviews_count="count")
        .reset_index()
    )
    stats["avg_rating"] = stats["avg_rating"].round(1)
    doctors = doctors.merge(stats, on="doctor_id", how="left")

    # On remet les colonnes dans l'ordre prévu dans le README
    doctors = doctors[[
        "doctor_id", "name", "specialty", "latitude", "longitude",
        "avg_rating", "reviews_count", "avg_consultation_min",
    ]]

    # Version PARFAITE (vérité terrain) : AI/data/reference/
    ref_dir = OUTPUT_DIR / "reference"
    ref_dir.mkdir(exist_ok=True)
    doctors.to_csv(ref_dir / "doctors.csv", index=False, encoding="utf-8")
    reviews.to_csv(ref_dir / "reviews.csv", index=False, encoding="utf-8")
    waiting.to_csv(ref_dir / "waiting_history.csv", index=False, encoding="utf-8")

    print("Version parfaite (référence) :")
    print(f"  doctors.csv         : {len(doctors)} lignes")
    print(f"  reviews.csv         : {len(reviews)} lignes")
    print(f"  waiting_history.csv : {len(waiting)} lignes")

    # Version BRUTE avec anomalies volontaires (pour tester le nettoyage)
    raw_doctors, raw_reviews, raw_waiting, log = inject_anomalies(doctors, reviews, waiting)
    raw_dir = OUTPUT_DIR / "raw"
    raw_dir.mkdir(exist_ok=True)
    raw_doctors.to_csv(raw_dir / "doctors_raw.csv", index=False, encoding="utf-8")
    raw_reviews.to_csv(raw_dir / "reviews_raw.csv", index=False, encoding="utf-8")
    raw_waiting.to_csv(raw_dir / "waiting_history_raw.csv", index=False, encoding="utf-8")
    with open(raw_dir / "anomalies_injected.json", "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print()
    print("Version brute (avec anomalies volontaires) :")
    print(f"  doctors_raw.csv         : {len(raw_doctors)} lignes")
    print(f"  reviews_raw.csv         : {len(raw_reviews)} lignes")
    print(f"  waiting_history_raw.csv : {len(raw_waiting)} lignes")
    print(f"  Détail des anomalies    : {raw_dir / 'anomalies_injected.json'}")


if __name__ == "__main__":
    main()
