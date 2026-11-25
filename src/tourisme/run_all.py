"""CAFÉ - orchestrateur tourisme 2022-2025.

À placer dans src/tourisme/run_all.py.
Les sources INSEE brutes doivent déjà être présentes. L'extraction via 09
n'est pas relancée automatiquement (réseau et téléchargements volumineux).
Les fichiers CAFE_TOURISME_*_V2.csv restent intacts par cet orchestrateur.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOURISME = ROOT / "src" / "tourisme"
RAW = ROOT / "data" / "raw" / "tourisme"
PROCESSED = ROOT / "data" / "processed" / "tourisme"
FINAL = ROOT / "data" / "final" / "tourisme"
YEARS = (2022, 2023, 2024, 2025)
DELIVERABLE_YEARS = (2023, 2024, 2025)
DELIVERABLE_TYPES = ("MARCHAND", "NON_MARCHAND")

# Une étape = un script existant et les fichiers qui prouvent son exécution.
# 49 et 50 génèrent des CLÉS ; les nuitées non marchandes restent bloquées
# jusqu'à validation du périmètre géographique des totaux.
STAGES = (
    ("13", "download/13_nuitees_2022_2025.py",
     "{year}/nuites_{year}.csv"),
    ("18", "distribution_com/18_capacites_communales.py",
     "{year}/capacites_communales_{year}.csv"),
    ("20", "distribution_com/20_estimation_nuitees_communales.py",
     "{year}/nuites_communales_estimees_{year}.csv"),
    ("46", "distribution_com/46_nonmarche.py",
     "{year}/nuites_non_marchandes_{year}.csv"),
    ("47", "distribution_com/47_logements_2022.py",
     "{year}/residences_secondaires_occasionnelles_{year}_communes.csv"),
    ("49", "distribution_com/49_integration_non_marchand.py",
     "{year}/cles_repartition_non_marchand_{year}.csv"),
    ("50", "distribution_com/50_non_marchand_com_dep_reg.py",
     "{year}/cles_non_marchandes_com_dep_reg_{year}.csv"),
    ("51", "distribution_com/51_tourisme_marchand_2022.py",
     "{year}/tourisme_marchand_com_dep_reg_{year}.csv"),
    ("53", "distribution_com/53_ventilation_mensuelle_2022.py",
     "{year}/tourisme_marchand_mensuel_com_dep_reg_{year}.csv"),
)


def args_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--from-stage", choices=[s[0] for s in STAGES], metavar="N",
        help="Reprendre depuis une étape (ex. --from-stage 51)",
    )
    group.add_argument(
        "--only-stage", choices=[s[0] for s in STAGES], metavar="N",
        help="Exécuter une seule étape (ex. --only-stage 53)",
    )
    parser.add_argument(
        "--visualize", action="store_true",
        help="Créer le classeur Excel V2 2023-2025 à partir des six CSV V2 existants",
    )
    parser.add_argument(
        "--verify-only", action="store_true",
        help="Vérifier les sorties produites sans exécuter les scripts",
    )
    return parser.parse_args()


def choose_stages(args: argparse.Namespace):
    if args.only_stage:
        return [s for s in STAGES if s[0] == args.only_stage]
    if args.from_stage:
        start = next(i for i, s in enumerate(STAGES) if s[0] == args.from_stage)
        return STAGES[start:]
    return STAGES


def check_raw_sources(selected) -> None:
    required = {}
    ids = {s[0] for s in selected}
    if "13" in ids:
        required["fréquentation INSEE (script 09)"] = RAW / "frequentation_brut.csv"
    if "46" in ids:
        required["suivi de la demande touristique (script 09)"] = (
            RAW / "tourisme_national_brut.csv"
        )
    missing = [f"{label} : {path}" for label, path in required.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Sources brutes manquantes :\n" + "\n".join(missing)
            + "\nExécuter d'abord le script 09 pour les jeux concernés."
        )


def expected_files(stage) -> list[Path]:
    template = stage[2]
    return [PROCESSED / template.format(year=year) for year in YEARS]


def verify_step(stage) -> None:
    missing = [p for p in expected_files(stage) if not p.is_file() or p.stat().st_size == 0]
    if missing:
        raise FileNotFoundError(
            f"Sortie de l'étape {stage[0]} absente ou vide :\n"
            + "\n".join(str(path) for path in missing)
        )
    print(f"  [OK] 4 fichiers annuels présents et non vides (étape {stage[0]})", flush=True)


def run_step(stage) -> None:
    name, relative_path, _ = stage
    script = TOURISME / relative_path
    if not script.is_file():
        raise FileNotFoundError(f"Script {name} introuvable : {script}")
    print(f"\n{'=' * 66}\nÉTAPE {name} : {script.name}\n{'=' * 66}", flush=True)
    started = time.perf_counter()
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)
    verify_step(stage)
    print(f"  Durée : {time.perf_counter() - started:.1f} secondes", flush=True)


def verify_v2() -> list[Path]:
    missing = []
    print("\n=== Livraison V2 existante (2023-2025) ===")
    for year in DELIVERABLE_YEARS:
        for kind in DELIVERABLE_TYPES:
            path = PROCESSED / str(year) / f"CAFE_TOURISME_{year}_{kind}_V2.csv"
            if path.is_file() and path.stat().st_size > 0:
                print(f"  [OK] {year} {kind}")
            else:
                print(f"  [ABSENT] {path}")
                missing.append(path)
    return missing


def visualize_v2() -> None:
    missing = verify_v2()
    if missing:
        raise FileNotFoundError(
            "Visualisation V2 impossible : " + str(len(missing))
            + " fichier(s) V2 manquant(s). Les sorties 51/53 ne remplacent "
              "pas automatiquement les livrables V2."
        )
    script = TOURISME / "analysis" / "57_organiser_visualiser_cafe_2023_2025.py"
    if not script.is_file():
        raise FileNotFoundError(f"Script 57 introuvable : {script}")
    FINAL.mkdir(parents=True, exist_ok=True)
    # --no-copy évite toute copie susceptible de modifier les CSV V2.
    subprocess.run(
        [sys.executable, str(script),
         "--input-dir", str(PROCESSED),
         "--output-dir", str(FINAL),
         "--no-copy"],
        cwd=ROOT, check=True,
    )
    outfile = FINAL / "CAFE_TOURISME_2023_2025.xlsx"
    if not outfile.is_file() or outfile.stat().st_size == 0:
        raise FileNotFoundError(f"Classeur Excel non produit : {outfile}")
    print(f"  [OK] Classeur V2 : {outfile}", flush=True)


def main() -> None:
    args = args_parser()
    selected = choose_stages(args)
    print("=== CAFÉ : orchestration tourisme 2022-2025 ===", flush=True)
    print("Étapes :", " -> ".join(s[0] for s in selected), flush=True)
    if not args.verify_only:
        check_raw_sources(selected)
    try:
        for stage in selected:
            if args.verify_only:
                verify_step(stage)
            else:
                run_step(stage)
        if args.visualize:
            visualize_v2()
        else:
            print("\nVisualisation V2 inchangée (option : --visualize).")
        print("\n=== EXÉCUTION TERMINÉE ===")
        print("Marchand : sorties 13, 18, 20, 51 et 53 disponibles.")
        print("Non marchand : 46 observé toutes destinations ; 47, 49, 50 fournissent des clés.")
        print("Les nuitées non marchandes communales restent NON calculées sans totaux métropolitains validés.")
        print("Les fichiers CAFE_TOURISME_*_V2.csv ne sont pas générés ni modifiés par ce pipeline.")
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        print(f"\n[ARRÊT] {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
