"""
clean_data.py
-------------
Nettoie les 3 jeux de données BRUTS du module IA de SmartMed, affiche un
rapport détaillé et crée de nouvelles variables (features).

    Entrée  : AI/data/raw/doctors_raw.csv, reviews_raw.csv, waiting_history_raw.csv
    Sortie  : AI/data/clean/doctors_clean.csv, reviews_clean.csv,
              waiting_history_clean.csv, cleaning_report.txt

Les fichiers bruts sont créés par data/generate_data.py (avec des anomalies
injectées volontairement). Si le fichier anomalies_injected.json est présent,
le rapport compare ce qui a été injecté et ce qui a été détecté.

Utilisation (depuis le dossier AI/) :
    python data/generate_data.py            # une seule fois
    python preprocessing/clean_data.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 1. RÉGLAGES : où lire, où écrire
# ---------------------------------------------------------------------------

AI_DIR = Path(__file__).resolve().parent.parent   # le dossier AI/
DATA_DIR = AI_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"

# Pour chaque type de problème : le texte affiché dans le rapport
LABELS = {
    "doctors": {
        "doublons": "doublons supprimés",
        "valeur_manquante": "lignes incomplètes supprimées",
        "gps_invalide": "coordonnées GPS impossibles supprimées",
        "duree_invalide": "durées de consultation impossibles supprimées",
        "textes_corriges": "textes corrigés (espaces)",
    },
    "reviews": {
        "doublons": "doublons supprimés",
        "note_manquante": "notes manquantes supprimées",
        "commentaire_vide": "commentaires vides supprimés",
        "note_invalide": "notes hors de 1 à 5 supprimées",
        "medecin_inconnu": "avis sur un médecin inexistant supprimés",
        "textes_corriges": "commentaires corrigés (espaces)",
        "sentiments_corriges": "sentiments invalides recalculés",
    },
    "waiting_history": {
        "doublons": "doublons supprimés",
        "valeur_manquante": "lignes incomplètes supprimées",
        "patients_negatifs": "nombres de patients négatifs supprimés",
        "attente_negative": "temps d'attente négatifs supprimés",
        "duree_invalide": "durées de consultation impossibles supprimées",
        "heure_invalide": "heures impossibles supprimées",
        "jour_invalide": "jours impossibles supprimés",
    },
}


# ---------------------------------------------------------------------------
# 2. NETTOYAGE DES MÉDECINS
# ---------------------------------------------------------------------------
# Chaque fonction reçoit le tableau ET un compteur "log" : à chaque étape,
# on note combien de lignes ont été supprimées (ou de textes corrigés).

def clean_doctors(df, log):
    """Supprime les doublons, les lignes incomplètes ou impossibles."""
    df = df.copy()

    # Un même médecin ne doit apparaître qu'une fois (identifiant unique)
    n = len(df)
    df = df.drop_duplicates(subset="doctor_id")
    log["doublons"] += n - len(df)

    # On supprime les lignes où une information essentielle manque
    essentials = ["doctor_id", "name", "specialty",
                  "latitude", "longitude", "avg_consultation_min"]
    n = len(df)
    df = df.dropna(subset=essentials)
    log["valeur_manquante"] += n - len(df)

    # Texte : on enlève les espaces au début et à la fin
    for col in ["name", "specialty"]:
        cleaned = df[col].str.strip()
        log["textes_corriges"] += int((cleaned != df[col]).sum())
        df[col] = cleaned

    # Valeurs impossibles : coordonnées GPS hors du globe, durée <= 0
    n = len(df)
    df = df[df["latitude"].between(-90, 90) & df["longitude"].between(-180, 180)]
    log["gps_invalide"] += n - len(df)

    n = len(df)
    df = df[df["avg_consultation_min"] > 0]
    log["duree_invalide"] += n - len(df)

    return df


# ---------------------------------------------------------------------------
# 3. NETTOYAGE DES AVIS
# ---------------------------------------------------------------------------

def rating_to_sentiment(rating):
    """Convertit une note (1 à 5) en sentiment."""
    if rating >= 4:
        return "positive"
    if rating == 3:
        return "neutral"
    return "negative"


def clean_reviews(df, valid_doctor_ids, log):
    """Nettoie les avis : doublons, notes, texte, médecin inexistant."""
    df = df.copy()

    # Doublon = ligne strictement identique (même review_id compris).
    # On ne compare PAS seulement le commentaire : deux patients différents
    # peuvent très bien écrire la même phrase.
    n = len(df)
    df = df.drop_duplicates()
    log["doublons"] += n - len(df)

    # Il nous faut une note et un commentaire
    n = len(df)
    df = df.dropna(subset=["rating"])
    log["note_manquante"] += n - len(df)

    n = len(df)
    df = df.dropna(subset=["comment"])
    log["commentaire_vide"] += n - len(df)

    # La note doit être un nombre entier entre 1 et 5
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    n = len(df)
    df = df[df["rating"].between(1, 5)]
    log["note_invalide"] += n - len(df)
    df["rating"] = df["rating"].astype(int)

    # Texte : plusieurs espaces -> un seul, puis on enlève les bords
    cleaned = (
        df["comment"].astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    log["textes_corriges"] += int(((cleaned != df["comment"]) & (cleaned != "")).sum())
    df["comment"] = cleaned

    # Un commentaire qui ne contenait que des espaces est maintenant vide
    n = len(df)
    df = df[df["comment"] != ""]
    log["commentaire_vide"] += n - len(df)

    # Un avis doit parler d'un médecin qui existe
    n = len(df)
    df = df[df["doctor_id"].isin(valid_doctor_ids)]
    log["medecin_inconnu"] += n - len(df)

    # Le sentiment doit être l'une des 3 valeurs connues, sinon on le
    # recalcule à partir de la note
    valid_sentiments = ["positive", "neutral", "negative"]
    invalid = ~df["sentiment"].isin(valid_sentiments)
    log["sentiments_corriges"] += int(invalid.sum())
    df.loc[invalid, "sentiment"] = df.loc[invalid, "rating"].apply(rating_to_sentiment)

    return df


# ---------------------------------------------------------------------------
# 4. NETTOYAGE DE L'HISTORIQUE D'ATTENTE
# ---------------------------------------------------------------------------

def clean_waiting(df, valid_doctor_ids, log):
    """Nettoie l'historique d'attente : valeurs manquantes ou impossibles."""
    df = df.copy()

    n = len(df)
    df = df.drop_duplicates()
    log["doublons"] += n - len(df)

    n = len(df)
    df = df.dropna()
    log["valeur_manquante"] += n - len(df)

    df = df[df["doctor_id"].isin(valid_doctor_ids)]

    # (étiquette, condition à respecter pour GARDER la ligne)
    rules = [
        ("patients_negatifs", df["patients_before"] >= 0),
        ("attente_negative", df["actual_wait_min"] >= 0),
        ("duree_invalide", df["avg_consultation_min"] > 0),
        ("heure_invalide", df["hour_of_day"].between(0, 23)),
        ("jour_invalide", df["day_of_week"].between(0, 6)),   # 0 = lundi
    ]
    for label, keep in rules:
        n = len(df)
        df = df[keep.loc[df.index]]
        log[label] += n - len(df)

    return df


# ---------------------------------------------------------------------------
# 5. CRÉATION DES NOUVELLES VARIABLES (features)
# ---------------------------------------------------------------------------

def add_features(doctors, reviews, waiting):
    """
    Crée des variables à partir des données nettoyées :

        avg_rating, reviews_count : recalculés depuis les avis propres
        avg_wait_minutes          : attente moyenne réelle de chaque médecin
        doctor_avg_delay_min      : retard moyen du médecin, c'est-à-dire
                                    l'attente réelle MOINS l'attente "théorique"
                                    (patients devant x durée de consultation)
    """
    doctors = doctors.copy()
    waiting = waiting.copy()

    # --- Note moyenne et nombre d'avis, recalculés sur les avis propres
    rating_stats = (
        reviews.groupby("doctor_id")["rating"]
        .agg(avg_rating="mean", reviews_count="count")
        .reset_index()
    )
    rating_stats["avg_rating"] = rating_stats["avg_rating"].round(1)
    doctors = doctors.drop(columns=["avg_rating", "reviews_count"], errors="ignore")
    doctors = doctors.merge(rating_stats, on="doctor_id", how="left")
    doctors["reviews_count"] = doctors["reviews_count"].fillna(0).astype(int)

    # --- Retard : attente réelle - attente théorique
    waiting["extra_delay_min"] = (
        waiting["actual_wait_min"]
        - waiting["patients_before"] * waiting["avg_consultation_min"]
    )
    delay_stats = (
        waiting.groupby("doctor_id")
        .agg(doctor_avg_delay_min=("extra_delay_min", "mean"),
             avg_wait_minutes=("actual_wait_min", "mean"))
        .round(1)
        .reset_index()
    )

    doctors = doctors.merge(delay_stats, on="doctor_id", how="left")
    waiting = waiting.drop(columns=["extra_delay_min"])
    waiting = waiting.merge(delay_stats[["doctor_id", "doctor_avg_delay_min"]],
                            on="doctor_id", how="left")

    return doctors, waiting


# ---------------------------------------------------------------------------
# 6. RAPPORT
# ---------------------------------------------------------------------------

def build_report(name, raw_len, clean_len, log, injected):
    """Fabrique les lignes du rapport pour un jeu de données."""
    lines = [f"{name} : {raw_len} lignes brutes -> {clean_len} lignes propres"]
    for label, text in LABELS[name].items():
        found = log[label]
        expected = injected.get(name, {}).get(label) if injected else None
        if found == 0 and not expected:
            continue
        line = f"   - {text:<50} {found:>4}"
        if expected is not None:
            status = "OK" if found == expected else "ECART"
            line += f"   (injectées : {expected:>3})  {status}"
        lines.append(line)
    return lines


# ---------------------------------------------------------------------------
# 7. PROGRAMME PRINCIPAL
# ---------------------------------------------------------------------------

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # accents lisibles dans Git Bash

    if not (RAW_DIR / "doctors_raw.csv").exists():
        print("Fichiers bruts introuvables. Lance d'abord :")
        print("    python data/generate_data.py")
        return

    CLEAN_DIR.mkdir(exist_ok=True)

    # Lecture des fichiers bruts
    doctors_raw = pd.read_csv(RAW_DIR / "doctors_raw.csv")
    reviews_raw = pd.read_csv(RAW_DIR / "reviews_raw.csv")
    waiting_raw = pd.read_csv(RAW_DIR / "waiting_history_raw.csv")

    # Anomalies injectées (si le fichier existe) pour comparer
    injected_file = RAW_DIR / "anomalies_injected.json"
    injected = None
    if injected_file.exists():
        with open(injected_file, encoding="utf-8") as f:
            injected = json.load(f)

    # Nettoyage (les médecins d'abord : les autres fichiers en dépendent)
    logs = {"doctors": Counter(), "reviews": Counter(), "waiting_history": Counter()}
    doctors = clean_doctors(doctors_raw, logs["doctors"])
    valid_ids = set(doctors["doctor_id"])
    reviews = clean_reviews(reviews_raw, valid_ids, logs["reviews"])
    waiting = clean_waiting(waiting_raw, valid_ids, logs["waiting_history"])

    # Rapport
    report = ["RAPPORT DE NETTOYAGE", "=" * 60]
    for name, raw_df, clean_df in [("doctors", doctors_raw, doctors),
                                   ("reviews", reviews_raw, reviews),
                                   ("waiting_history", waiting_raw, waiting)]:
        report += build_report(name, len(raw_df), len(clean_df), logs[name], injected)
        report.append("")
    for line in report:
        print(line)

    # Nouvelles variables
    doctors, waiting = add_features(doctors, reviews, waiting)

    # Sauvegarde des fichiers propres et du rapport
    doctors.to_csv(CLEAN_DIR / "doctors_clean.csv", index=False, encoding="utf-8")
    reviews.to_csv(CLEAN_DIR / "reviews_clean.csv", index=False, encoding="utf-8")
    waiting.to_csv(CLEAN_DIR / "waiting_history_clean.csv", index=False, encoding="utf-8")
    (CLEAN_DIR / "cleaning_report.txt").write_text("\n".join(report), encoding="utf-8")
    print(f"Fichiers propres écrits dans : {CLEAN_DIR}")


if __name__ == "__main__":
    main()
