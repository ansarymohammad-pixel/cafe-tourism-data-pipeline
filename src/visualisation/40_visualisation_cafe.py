
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent

fichier = (
    BASE / "data/processed/tourisme/"
    "livraison_cafe_2022/cafe_communes_2022.csv"
)

df = pd.read_csv(
    fichier,
    dtype={"geocode": str}
)

print("Dimensions :", df.shape)
print(df.head(10))

# Les 15 communes avec le plus de chambres
top15 = df.nlargest(
    15, "hotel_capacity"
).sort_values("hotel_capacity")

plt.figure(figsize=(11, 7))

plt.barh(
    top15["geocode"],
    top15["hotel_capacity"]
)

plt.xlabel("Nombre de chambres d'hôtel")
plt.ylabel("Code INSEE de la commune")
plt.title("CAFÉ — Top 15 des capacités hôtelières (2022)")
plt.tight_layout()
plt.show()
