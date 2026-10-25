"""
verify_cleaning.py
------------------
Vérifie que le nettoyage a bien remis les données en état, en comparant
AI/data/clean/ (résultat du nettoyage) avec AI/data/reference/ (la version
parfaite, avant l'injection des anomalies).

Contrôles :
  1. Nombre de lignes : référence moins les lignes irrécupérables injectées.
  2. Aucun identifiant en double, aucune valeur manquante.
  3. Les valeurs conservées (et les textes/sentiments corrigés) sont
     IDENTIQUES à celles de la référence.

Utilisation (depuis le dossier AI/), après clean_data.py :
    python preprocessing/verify_cleaning.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

AI_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = AI_DIR / "data"
REF_DIR = DATA_DIR / "reference"
CLEAN_DIR = DATA_DIR / "clean"
RAW_DIR = DATA_DIR / "raw"

# Anomalies qui NE font PAS perdre de ligne : doublons (copies) et corrections
NO_LOSS = {"doublons", "textes_corriges", "sentiments_corriges"}

results = []


def check(label, ok):
    """Affiche un contrôle et l'enregistre."""
    results.append(ok)
    print(f"  [{'OK' if ok else 'ECHEC'}] {label}")


def expected_loss(injected, name):
    """Nombre de lignes irrécupérables injectées pour un fichier."""
    return sum(n for key, n in injected[name].items() if key not in NO_LOSS)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    needed = [REF_DIR / "doctors.csv", CLEAN_DIR / "doctors_clean.csv",
              RAW_DIR / "anomalies_injected.json"]
    if not all(path.exists() for path in needed):
        print("Fichiers manquants. Lance d'abord, dans l'ordre :")
        print("    python data/generate_data.py")
        print("    python preprocessing/clean_data.py")
        return

    with open(RAW_DIR / "anomalies_injected.json", encoding="utf-8") as f:
        injected = json.load(f)

    ref = {
        "doctors": pd.read_csv(REF_DIR / "doctors.csv"),
        "reviews": pd.read_csv(REF_DIR / "reviews.csv"),
        "waiting_history": pd.read_csv(REF_DIR / "waiting_history.csv"),
    }
    clean = {
        "doctors": pd.read_csv(CLEAN_DIR / "doctors_clean.csv"),
        "reviews": pd.read_csv(CLEAN_DIR / "reviews_clean.csv"),
        "waiting_history": pd.read_csv(CLEAN_DIR / "waiting_history_clean.csv"),
    }
    id_col = {"doctors": "doctor_id", "reviews": "review_id",
              "waiting_history": "record_id"}
    # colonnes dont les valeurs doivent être identiques à la référence
    # (avg_rating et reviews_count sont recalculés : ils peuvent légitimement changer)
    compare_cols = {
        "doctors": ["name", "specialty", "latitude", "longitude", "avg_consultation_min"],
        "reviews": ["doctor_id", "rating", "comment", "sentiment"],
        "waiting_history": ["doctor_id", "patients_before", "avg_consultation_min",
                            "hour_of_day", "day_of_week", "actual_wait_min"],
    }

    print("VÉRIFICATION DU NETTOYAGE (clean/ comparé à reference/)")
    print("=" * 60)
    for name in ["doctors", "reviews", "waiting_history"]:
        r, c, key = ref[name], clean[name], id_col[name]
        print(f"\n{name}")

        expected = len(r) - expected_loss(injected, name)
        check(f"nombre de lignes : {len(c)} (attendu {expected})", len(c) == expected)
        check("aucun identifiant en double", c[key].is_unique)
        check("aucune valeur manquante", int(c.isna().sum().sum()) == 0)
        check("toutes les lignes propres existent dans la référence",
              set(c[key]) <= set(r[key]))

        merged = c.merge(r, on=key, suffixes=("", "_ref"))
        same = all((merged[col] == merged[f"{col}_ref"]).all()
                   for col in compare_cols[name] if col != key)
        check("valeurs identiques à la référence (textes corrigés compris)", same)

    print()
    if all(results):
        print(f"RÉSULTAT : {len(results)}/{len(results)} contrôles réussis.")
    else:
        print(f"RÉSULTAT : {sum(results)}/{len(results)} contrôles réussis, "
              "des différences sont à examiner.")


if __name__ == "__main__":
    main()
