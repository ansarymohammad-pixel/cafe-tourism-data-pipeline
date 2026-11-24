
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TOURISME = ROOT / "src" / "tourisme"
PROCESSED = ROOT / "data" / "processed" / "tourisme"

YEARS = (2023, 2024, 2025)
TYPES = ("MARCHAND", "NON_MARCHAND")


def verify_files():
    print("\n=== Verification des donnees CAFÉ ===")

    missing = []

    for year in YEARS:
        for kind in TYPES:
            path = (
                PROCESSED
                / str(year)
                / f"CAFE_TOURISME_{year}_{kind}_V2.csv"
            )

            if path.is_file():
                print(f"[OK] {year} {kind}")
            else:
                print(f"[MANQUANT] {path}")
                missing.append(path)

    if missing:
        raise FileNotFoundError(
            f"{len(missing)} fichier(s) manquant(s)."
        )


def main():
    verify_files()

    script = (
        TOURISME
        / "analysis"
        / "57_organiser_visualiser_cafe_2023_2025.py"
    )

    print("\n=== Visualisation et synthese ===")

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-dir",
            str(PROCESSED),
            "--output-dir",
            str(ROOT / "data" / "final" / "tourisme"),
        ],
        cwd=ROOT,
        check=True,
    )

    print("\nPipeline CAFÉ termine avec succes.")


if __name__ == "__main__":
    main()
