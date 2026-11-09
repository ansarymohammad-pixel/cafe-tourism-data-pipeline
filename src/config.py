
from pathlib import Path

# Racine du projet CAFÉ
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Dossiers des données
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW = DATA_DIR / "raw"
DATA_INTERIM = DATA_DIR / "interim"
DATA_PROCESSED = DATA_DIR / "processed"

# Dossiers de travail
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
DOCS_DIR = PROJECT_ROOT / "docs"

# Fichiers tourisme 2022
TOURISME_DIR = DATA_PROCESSED / "tourisme"
NUITEES_2022 = TOURISME_DIR / "nuites_2022.csv"
CAPACITES_2022 = TOURISME_DIR / "capacites_metro_2022.csv"
