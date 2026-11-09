
import pandas as pd

fichier = (
    "data/processed/tourisme/"
    "capacites_geo_corrigees_2022.csv"
)

df = pd.read_csv(
    fichier,
    dtype={"geocode": str}
)

villes = {
    "Paris": ("75056", "751"),
    "Lyon": ("69123", "6938"),
    "Marseille": ("13055", "132")
}

colonnes = [
    "places_hotels",
    "places_campings",
    "places_autres"
]

for ville, (code_mere, prefixe) in villes.items():

    mere = df[df["geocode"] == code_mere]

    if ville == "Paris":
        arr = df[df["geocode"].str.match(r"^751\d{2}$")]
    elif ville == "Lyon":
        arr = df[df["geocode"].str.match(r"^6938[1-9]$")]
    else:
        arr = df[df["geocode"].str.match(r"^132(0[1-9]|1[0-6])$")]

    print(f"\n===== {ville} =====")
    print("Nombre d'arrondissements :", len(arr))

    if mere.empty:
        print("Commune mère absente")
        continue

    for col in colonnes:
        valeur_mere = mere[col].sum()
        valeur_arr = arr[col].sum()

        print(
            f"{col}: mère={valeur_mere}, "
            f"arrondissements={valeur_arr}, "
            f"écart={valeur_mere - valeur_arr}"
        )
