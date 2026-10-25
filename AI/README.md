# SmartMed — Module IA

Ce dossier contient tout ce qui concerne l'intelligence artificielle du projet : données, préparation des données et futurs modèles.

> **Sprint 1 (actuel)** : définir les données et les variables (features), créer des données simulées, les nettoyer, préparer l'architecture.
> **Sprint 6** : entraîner et intégrer les modèles dans le backend FastAPI.

---

## 1. Structure du dossier

```
AI/
├── data/
│   ├── generate_data.py   # génère les données simulées (version brute + version de référence)
│   ├── raw/               # données BRUTES simulées, avec anomalies : point de départ du pipeline
│   ├── clean/             # données NETTOYÉES + rapport : sortie du pipeline
│   └── reference/         # version parfaite (vérité terrain), pour vérifier le nettoyage
├── preprocessing/
│   ├── clean_data.py      # nettoyage + création de variables + rapport
│   └── verify_cleaning.py # vérifie le nettoyage en le comparant à reference/
├── variables_study.ipynb  # étude des variables : graphiques, corrélations, conclusions par module
├── recommendation/        # module de recommandation de médecins (Sprint 6)
├── waiting_time/          # module de prédiction du temps d'attente (Sprint 6)
├── sentiment/             # module d'analyse des avis (Sprint 6)
├── requirements.txt       # bibliothèques Python nécessaires
└── README.md              # ce document
```

| Dossier          | Rôle                                                                                 |
| ---------------- | ------------------------------------------------------------------------------------ |
| `data`           | Génère et stocke les jeux de données (brut, propre, référence).                      |
| `preprocessing`  | Transforme les données brutes en données propres et utilisables par les modèles.     |
| `recommendation` | Calcule un score pour proposer les meilleurs médecins à un patient.                  |
| `waiting_time`   | Estime combien de minutes un patient va attendre.                                    |
| `sentiment`      | Détermine si un avis est positif, neutre ou négatif et repère les thèmes récurrents. |

---

## 2. Le pipeline de données

```
generate_data.py ──► raw/ (données brutes, avec anomalies)
                       │
                clean_data.py ──► clean/ (données propres + cleaning_report.txt)
                       │
              verify_cleaning.py ──► comparaison avec reference/ (vérité terrain)
```

### Commandes (depuis le dossier `AI/`, environnement virtuel actif)

```bash
python data/generate_data.py              # 1. crée raw/ et reference/
python preprocessing/clean_data.py        # 2. nettoie raw/ -> clean/ et affiche le rapport
python preprocessing/verify_cleaning.py   # 3. vérifie le résultat
```

### Pourquoi trois dossiers de données ?

- **`raw/`** simule ce que produiront de vrais utilisateurs : des données imparfaites. C'est l'entrée du pipeline.
- **`clean/`** est le résultat du nettoyage. C'est ce que les modèles utiliseront.
- **`reference/`** contient la version parfaite, avant l'injection des anomalies. Elle ne sert **qu'à vérifier** que le nettoyage remet bien les données en état. Elle n'est jamais utilisée pour entraîner un modèle.

### Anomalies injectées volontairement (dans `raw/`)

Le détail exact est dans `data/raw/anomalies_injected.json`. Résumé :

| Fichier                   | Anomalies injectées                                                                                                                                                              |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `doctors_raw.csv`         | 3 doublons, 4 textes avec espaces superflus                                                                                                                                      |
| `reviews_raw.csv`         | 20 doublons, 10 notes hors de 1 à 5, 10 notes manquantes, 8 commentaires vides, 6 avis sur un médecin inexistant, 15 commentaires avec espaces superflus, 8 sentiments invalides |
| `waiting_history_raw.csv` | 25 doublons, 12 attentes négatives, 8 nombres de patients négatifs, 10 heures impossibles, 5 jours impossibles, 15 valeurs manquantes                                            |

### Résultat du nettoyage

| Fichier         | Lignes brutes | Lignes propres |
| --------------- | ------------- | -------------- |
| doctors         | 53            | 50             |
| reviews         | 1 222         | 1 168          |
| waiting_history | 4 025         | 3 950          |

`clean_data.py` affiche, pour chaque type d'anomalie, le nombre détecté à côté du nombre injecté. `verify_cleaning.py` confirme ensuite que les valeurs conservées sont identiques à la référence.

---

## 3. Vocabulaire

- **Feature (variable)** : une information donnée au modèle pour qu'il prenne sa décision (ex. : nombre de patients dans la file).
- **Cible (target)** : ce que le modèle doit deviner (ex. : le temps d'attente réel en minutes).
- **Dataset** : un tableau de données (un fichier CSV) dont chaque ligne est un exemple.
- **Données simulées (synthétiques)** : données générées par du code, car les vraies données médicales sont confidentielles.
- **Anomalie injectée** : défaut ajouté volontairement aux données simulées pour tester le nettoyage.

---

## 4. Les trois modules et leurs variables

### 4.1 Recommandation de médecins (BF24)

**Question** : quel médecin proposer à ce patient ?

| Feature                | Description                             | Type      | Origine                                              |
| ---------------------- | --------------------------------------- | --------- | ---------------------------------------------------- |
| `specialty`            | Spécialité du médecin                   | catégorie | `doctors`                                            |
| `distance_km`          | Distance entre le patient et le médecin | nombre    | calculée à partir des positions GPS (Sprint suivant) |
| `avg_rating`           | Note moyenne (1 à 5)                    | nombre    | recalculée sur les avis propres                      |
| `reviews_count`        | Nombre d'avis reçus                     | entier    | recalculée sur les avis propres                      |
| `next_available_hours` | Délai avant le prochain créneau libre   | nombre    | fournie par le backend (rendez-vous)                 |
| `avg_wait_minutes`     | Temps d'attente moyen réel du médecin   | nombre    | **créée** par `clean_data.py`                        |

**Sortie** : un score entre 0 et 1 pour chaque médecin. Le plus haut score est proposé en premier.

### 4.2 Prédiction du temps d'attente (BF26)

**Question** : combien de temps vais-je attendre ?

| Feature                | Description                                                                              | Type   | Origine                       |
| ---------------------- | ---------------------------------------------------------------------------------------- | ------ | ----------------------------- |
| `patients_before`      | Nombre de patients avant moi dans la file                                                | entier | `waiting_history`             |
| `avg_consultation_min` | Durée moyenne d'une consultation du médecin                                              | nombre | `waiting_history`             |
| `hour_of_day`          | Heure de la journée (0 à 23)                                                             | entier | `waiting_history`             |
| `day_of_week`          | Jour de la semaine (0 = lundi)                                                           | entier | `waiting_history`             |
| `doctor_avg_delay_min` | Retard moyen du médecin : attente réelle moins (patients devant × durée de consultation) | nombre | **créée** par `clean_data.py` |

**Cible** : `actual_wait_min`, le temps d'attente réel en minutes.

### 4.3 Analyse des avis (BF25)

**Question** : cet avis est-il positif, neutre ou négatif ?

| Donnée    | Description                   | Type   |
| --------- | ----------------------------- | ------ |
| `comment` | Texte de l'avis (en français) | texte  |
| `rating`  | Note donnée (1 à 5)           | entier |

**Cible** : `sentiment` (`positive`, `neutral`, `negative`).
Thèmes à repérer : attente, accueil, prix, qualité des soins, propreté.

---

## 5. Jeux de données (fichiers propres, dans `clean/`)

Les noms de colonnes sont en `snake_case` et doivent rester **identiques** à ceux de la base PostgreSQL (ex. : `doctor_id`, pas `doctorId`).

### `doctors_clean.csv`

| Colonne                | Type           | Exemple          |
| ---------------------- | -------------- | ---------------- |
| `doctor_id`            | entier         | 12               |
| `name`                 | texte          | Dr. Hichem Sassi |
| `specialty`            | texte          | ORL              |
| `latitude`             | nombre         | 36.80650         |
| `longitude`            | nombre         | 10.18150         |
| `avg_consultation_min` | entier         | 20               |
| `avg_rating`           | nombre (1 à 5) | 4.3              |
| `reviews_count`        | entier         | 24               |
| `doctor_avg_delay_min` | nombre         | 12.8             |
| `avg_wait_minutes`     | nombre         | 103.8            |

### `reviews_clean.csv`

| Colonne     | Type           | Exemple                                    |
| ----------- | -------------- | ------------------------------------------ |
| `review_id` | entier         | 301                                        |
| `doctor_id` | entier         | 12                                         |
| `rating`    | entier (1 à 5) | 2                                          |
| `comment`   | texte          | Beaucoup trop d'attente, plus d'une heure. |
| `sentiment` | texte          | negative                                   |

### `waiting_history_clean.csv`

| Colonne                | Type   | Exemple |
| ---------------------- | ------ | ------- |
| `record_id`            | entier | 1050    |
| `doctor_id`            | entier | 12      |
| `patients_before`      | entier | 4       |
| `avg_consultation_min` | entier | 20      |
| `hour_of_day`          | entier | 10      |
| `day_of_week`          | entier | 2       |
| `actual_wait_min`      | nombre | 87.0    |
| `doctor_avg_delay_min` | nombre | 12.8    |

---

## 6. Règles de nettoyage appliquées (`clean_data.py`)

- Supprimer les doublons (ligne strictement identique ; identifiant unique pour les médecins).
- Supprimer les lignes avec valeur manquante essentielle.
- Supprimer les notes hors de 1 à 5, les attentes ou nombres de patients négatifs, les heures hors de 0 à 23, les jours hors de 0 à 6.
- Supprimer les avis sur un médecin qui n'existe pas.
- Corriger les textes (espaces superflus) et recalculer les sentiments invalides à partir de la note.
- Recalculer `avg_rating` et `reviews_count` à partir des avis propres.

---

## 7. Limites (à dire clairement)

- **Les données sont simulées.** Elles suivent des règles que nous avons écrites (ex. : l'attente augmente avec le nombre de patients). Un modèle entraîné dessus retrouvera ces règles : ses scores **ne mesurent pas une performance réelle**.
- **Les anomalies sont injectées volontairement** pour valider le pipeline. Ce ne sont pas de vraies erreurs d'utilisateurs.
- **Les données médicales réelles sont confidentielles** : aucune donnée de patient réel n'est utilisée.
- **Stratégie prévue** : entraîner d'abord sur les données simulées pour valider la chaîne technique, puis évaluer sur de vraies données (avis annotés, jeu public, données collectées par l'application).
- **Les temps d'attente simulés sont longs** (moyenne d'environ 156 min, et 57 % dépassent 2 h) : la simulation représente une file sans rendez-vous, avec jusqu'à 12 patients devant soi.
- **Le lien parfait entre la note et le sentiment est un artefact du générateur** (le sentiment est déduit de la note) : le modèle de sentiment devra être évalué sur de vrais avis.

---

## 8. Datasets publics étudiés

Aucun jeu public ne correspond exactement à notre schéma. Pistes examinées :

| Jeu de données                                                                                           | Intérêt                                                    | Limite                                                                            |
| -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------- |
| TUNIZI (commentaires en dialecte tunisien, lettres latines, positif/négatif, environ 9 200 commentaires) | Test d'un modèle de sentiment sur du dialecte tunisien     | Commentaires YouTube, pas médicaux ; pas de classe neutre ; licence non précisée  |
| Medical Appointment No Shows (Kaggle)                                                                    | Vrais rendez-vous médicaux, délais de prise de rendez-vous | Ne contient pas le temps d'attente en salle d'attente (à vérifier avant de citer) |
| `doctor_review` (Hugging Face)                                                                           | Avis sur des médecins                                      | Moins de 1 000 lignes, description incomplète                                     |
| Temps d'attente des urgences (données ouvertes, ex. Irlande du Nord)                                     | Ordres de grandeur réels                                   | Statistiques agrégées, pas des patients individuels                               |

---

## 9. Livrables du Sprint 1

- [x] Features définies pour les 3 modules (ce document)
- [x] Données simulées générées (`data/generate_data.py`)
- [x] Script de nettoyage et rapport (`preprocessing/clean_data.py`)
- [x] Vérification du nettoyage (`preprocessing/verify_cleaning.py`)
- [x] Architecture du module IA (ce document)
- [x] Première étude des variables (`variables_study.ipynb`)
- [ ] Noms de colonnes validés avec l'équipe Backend

---

## 10. Installation

```bash
cd AI
python -m venv venv
source venv/Scripts/activate      # Git Bash sous Windows
# venv\Scripts\activate           # PowerShell / CMD sous Windows
pip install -r requirements.txt
```

## 11. Règles d'équipe

- Ne jamais commiter `venv/`, `.env`, clés ou mots de passe.
- Ne pas modifier un nom de colonne sans prévenir l'équipe Backend.
- Travailler sur la branche `feature/ai-foundation`, puis ouvrir une Pull Request.
