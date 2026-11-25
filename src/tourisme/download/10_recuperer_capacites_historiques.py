
from pathlib import Path
from urllib.request import urlopen, Request
from zipfile import ZipFile
import shutil
import subprocess
import sys

# Racine du projet CAFÉ
ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "tourisme"

# Archives officielles INSEE
URLS = {
    2023: (
        "https://www.insee.fr/fr/statistiques/fichier/"
        "2021703/base-cc-tourisme-2023-geo2023-CSV.zip"
    ),
    2024: (
        "https://www.insee.fr/fr/statistiques/fichier/"
        "2021703/DS_TOUR_CAP_CSV_2024.zip"
    ),
    2025: (
        "https://www.insee.fr/fr/statistiques/fichier/"
        "2021703/DS_TOUR_CAP_CSV_2025_geo25.zip"
    ),
}


def telecharger_archive(year, url):
    archive = RAW / f"capacites_{year}.zip"

    if archive.exists():
        print(f"[EXISTANT] Archive {year}")
        return archive

    print(f"[DOWNLOAD] Capacités INSEE {year}")

    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    temporaire = archive.with_suffix(".zip.tmp")

    try:
        with urlopen(request, timeout=120) as response:
            with open(temporaire, "wb") as fichier:
                shutil.copyfileobj(response, fichier)
        temporaire.replace(archive)
    finally:
        temporaire.unlink(missing_ok=True)

    print(f"[OK] Archive téléchargée : {archive}")
    return archive


def extraire_csv(year, archive):
    destination = RAW / f"capacites_{year}.csv"

    if destination.exists():
        print(f"[EXISTANT] CSV {year}")
        return destination

    with ZipFile(archive) as zip_file:
        candidats = []

        for nom in zip_file.namelist():
            if not nom.lower().endswith(".csv"):
                continue

            if "metadata" in nom.lower() or "meta_" in nom.lower():
                continue

            with zip_file.open(nom) as fichier:
                entete = fichier.readline().decode(
                    "utf-8-sig", errors="replace"
                ).upper()

            # Format historique ou format Melodi
            score = 0

            if "CODGEO" in entete:
                score += 2
            if "HTCH" in entete:
                score += 2
            if "GEO" in entete and "ACTIVITY" in entete:
                score += 2
            if "TOUR_MEASURE" in entete:
                score += 2

            if score:
                candidats.append((score, nom))

        if not candidats:
            raise ValueError(
                f"Aucun CSV de capacités reconnu dans {archive}"
            )

        candidats.sort(reverse=True)
        nom_csv = candidats[0][1]

        print(f"[EXTRACTION] {nom_csv}")

        temporaire = destination.with_suffix(".csv.tmp")

        try:
            with zip_file.open(nom_csv) as source:
                with open(temporaire, "wb") as sortie:
                    shutil.copyfileobj(source, sortie)
            temporaire.replace(destination)
        finally:
            temporaire.unlink(missing_ok=True)

    print(f"[OK] CSV créé : {destination}")
    return destination


def main():
    RAW.mkdir(parents=True, exist_ok=True)

    # Utiliser la base 2022 déjà présente
    source_2022 = (
        RAW / "base-cc-tourisme-2022-geo2022.csv"
    )
    destination_2022 = RAW / "capacites_2022.csv"

    if not destination_2022.exists():
        if not source_2022.exists():
            raise FileNotFoundError(
                f"Source 2022 introuvable : {source_2022}"
            )
        shutil.copy2(source_2022, destination_2022)

    print("[OK] Capacités 2022 disponibles")

    # Télécharger et extraire les autres années
    for year, url in URLS.items():
        destination = RAW / f"capacites_{year}.csv"

        if destination.exists():
            print(f"[OK] Capacités {year} déjà disponibles")
            continue

        archive = telecharger_archive(year, url)
        extraire_csv(year, archive)

    print("\n=== SOURCES 2022-2025 DISPONIBLES ===")

    # Lancer le traitement de préparation multi-années
    script_18 = (
        ROOT / "src" / "tourisme"
        / "distribution_com"
        / "18_capacites_communales.py"
    )

    subprocess.run(
        [sys.executable, str(script_18)],
        cwd=ROOT,
        check=True,
    )

    print("\n=== PIPELINE CAPACITÉS TERMINÉ ===")


if __name__ == "__main__":
    main()
