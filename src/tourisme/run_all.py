"""CAFÉ — orchestrateur simplifié, 2022–2025.

Depuis la racine du dépôt :
  python src/tourisme/run_all.py --finalize   # 52 puis 54, sans relancer le reste
  python src/tourisme/run_all.py              # chaîne complète 13 à 54
  python src/tourisme/run_all.py --verify-only # uniquement présence des sorties
  python src/tourisme/run_all.py --only-stage 53
  python src/tourisme/run_all.py --from-stage 51

Le script 09 reste volontairement manuel (téléchargements lourds).
Les contrôles de conservation COM/DEP/REG et mensuels restent dans les
scripts de calcul. Le bilan détaillé des valeurs manquantes n'est pas affiché.
Le non-marchand reste un scénario exploratoire (solution B, France + DOM).
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

# (Identifiant, script, modèle du fichier attendu sous processed/tourisme)
STAGES = (
    ("13", "download/13_nuitees_2022_2025.py", "nuites_{year}.csv"),
    ("18", "distribution_com/18_capacites_communales.py", "capacites_communales_{year}.csv"),
    ("20", "distribution_com/20_estimation_nuitees_communales.py", "nuites_communales_estimees_{year}.csv"),
    ("46", "distribution_com/46_nonmarche.py", "nuites_non_marchandes_{year}.csv"),
    ("47", "distribution_com/47_logements_2022.py", "residences_secondaires_occasionnelles_{year}_communes.csv"),
    ("49", "distribution_com/49_integration_non_marchand.py", "cles_repartition_non_marchand_{year}.csv"),
    ("50", "distribution_com/50_non_marchand_com_dep_reg.py", "cles_non_marchandes_com_dep_reg_{year}.csv"),
    ("51", "distribution_com/51_tourisme_marchand_2022.py", "tourisme_marchand_com_dep_reg_{year}.csv"),
    ("52", "distribution_com/52_scenario_non_marchand_2022_2025.py", "scenario_non_marchand_com_dep_reg_{year}.csv"),
    ("53", "distribution_com/53_ventilation_mensuelle_2022.py", "tourisme_marchand_mensuel_com_dep_reg_{year}.csv"),
    ("54", "54_assembler_cafe_2022_2025.py", None),
)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--finalize", action="store_true", help="Exécuter seulement 52 puis 54")
    mode.add_argument("--only-stage", choices=[s[0] for s in STAGES], help="Exécuter une étape")
    mode.add_argument("--from-stage", choices=[s[0] for s in STAGES], help="Reprendre à une étape")
    mode.add_argument("--verify-only", action="store_true", help="Vérifier les fichiers, sans calcul")
    p.add_argument("--verbose", action="store_true", help="Afficher toutes les sorties des scripts")
    return p.parse_args()


def select_stages(a):
    if a.finalize:
        return [s for s in STAGES if s[0] in ("52", "54")]
    if a.only_stage:
        return [s for s in STAGES if s[0] == a.only_stage]
    if a.from_stage:
        n = next(i for i, s in enumerate(STAGES) if s[0] == a.from_stage)
        return STAGES[n:]
    return STAGES


def outputs(stage):
    id_, _, template = stage
    if id_ == "54":
        result = []
        for year in YEARS:
            result += [
                FINAL / f"CAFE_TOURISME_{year}.xlsx",
                FINAL / str(year) / f"CAFE_TOURISME_{year}_MARCHAND_V2.csv",
                FINAL / str(year) / f"CAFE_TOURISME_{year}_NON_MARCHAND_V2.csv",
            ]
        return result
    return [PROCESSED / str(y) / template.format(year=y) for y in YEARS]


def check_outputs(stage):
    missing = [str(p) for p in outputs(stage) if not p.is_file() or p.stat().st_size == 0]
    if missing:
        raise FileNotFoundError("Sorties de l'étape " + stage[0] + " absentes ou vides :\n" + "\n".join(missing))


def check_raw(stages):
    ids = {s[0] for s in stages}
    required = {}
    if ids & {"13", "53", "54"}:
        required["fréquentation INSEE"] = RAW / "frequentation_brut.csv"
    if ids & {"46", "52"}:
        required["tourisme national INSEE"] = RAW / "tourisme_national_brut.csv"
    absent = [f"{label}: {path}" for label, path in required.items() if not path.is_file()]
    if absent:
        raise FileNotFoundError("Sources INSEE introuvables :\n" + "\n".join(absent))


def run_stage(stage, verbose):
    ident, rel_path, _ = stage
    script = TOURISME / rel_path
    if not script.is_file():
        raise FileNotFoundError(f"Script {ident} absent : {script}")
    t0 = time.perf_counter()
    print(f"  [{ident}] {script.name}...", flush=True)
    if verbose:
        subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)
    else:
        completed = subprocess.run(
            [sys.executable, str(script)], cwd=ROOT,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            errors="replace", check=False,
        )
        if completed.returncode:
            print(completed.stdout, file=sys.stderr, flush=True)
            raise RuntimeError(f"Étape {ident} en échec (code {completed.returncode})")
    check_outputs(stage)
    print(f"       [OK] {len(outputs(stage))} sortie(s) présentes ({time.perf_counter() - t0:.1f}s)", flush=True)


def main():
    args = parse_args()
    selected = select_stages(args)
    print("\n=== CAFÉ 2022–2025 ===", flush=True)
    print("Étapes : " + " -> ".join(s[0] for s in selected), flush=True)
    try:
        if not args.verify_only:
            check_raw(selected)
        for stage in selected:
            if args.verify_only:
                check_outputs(stage)
                print(f"  [{stage[0]}] OK : {len(outputs(stage))} fichier(s) présents", flush=True)
            else:
                run_stage(stage, args.verbose)
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"\n[ÉCHEC] {exc}", file=sys.stderr, flush=True)
        return 1
    print("\n=== PIPELINE TERMINÉ ===", flush=True)
    if any(s[0] == "54" for s in selected):
        print("4 classeurs Excel : 2022, 2023, 2024, 2025", flush=True)
        print("2 onglets par classeur : MARCHAND et NON_MARCHAND", flush=True)
        print("Non marchand : scénario exploratoire (hypothèses documentées dans les sorties).", flush=True)
    print("Les contrôles de sommes restent exécutés dans les scripts de calcul.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
