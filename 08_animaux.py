
import pandas as pd
from pathlib import Path

dossier = Path("data/raw")

fichiers = list(dossier.glob("*Cheptel*.xlsx"))

print("Fichiers trouvés :")
for fichier in fichiers:
    print(fichier.name)

if not fichiers:
    raise FileNotFoundError(
        "Télécharge d'abord le fichier Excel des cheptels."
    )

fichier = fichiers[0]

excel = pd.ExcelFile(fichier)

print("\nFeuilles disponibles :")
print(excel.sheet_names)

for feuille in excel.sheet_names:
    apercu = pd.read_excel(
        fichier,
        sheet_name=feuille,
        header=None,
        nrows=8
    )

    print(f"\n--- {feuille} ---")
    print(apercu.to_string(index=False, header=False))
