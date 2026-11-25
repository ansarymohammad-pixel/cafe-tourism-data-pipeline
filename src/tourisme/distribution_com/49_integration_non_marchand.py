"""CAFÉ - 49 : préparation et allocation des nuitées non marchandes.

2022-2025. Les données DS_SUIVI_DDE_TOUR / TRAVEL_DEST=_T sont conservées
comme références non répartissables. Pour répartir des nuitées en métropole,
il faut une source distincte validée par année et par catégorie.
"""
from pathlib import Path
import argparse
import csv
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "tourisme"
PROCESSED = ROOT / "data" / "processed" / "tourisme"
YEARS = (2022, 2023, 2024, 2025)
METRO = {f"{i:02d}" for i in range(1, 96) if i != 20} | {"2A", "2B"}
CATEGORIES = ("famille_amis", "residences_secondaires")


def cli():
    p = argparse.ArgumentParser(description="CAFÉ 49 - répartition non marchande")
    p.add_argument("--year", type=int, choices=YEARS)
    p.add_argument("--strict", action="store_true",
                   help="Arrêter sur une source manquante ou non validée")
    return p.parse_args()


def code_commune(v):
    if pd.isna(v):
        return None
    v = str(v).strip().upper()
    if "-COM-" in v:
        v = v.rsplit("-COM-", 1)[-1]
    elif v.startswith("COM-"):
        v = v[4:]
    return v if re.fullmatch(r"(?:\d{5}|2[AB]\d{3})", v) else None


def departement(v):
    if not v:
        return None
    return v[:2]


def numeric(series):
    return pd.to_numeric(
        series.astype("string").str.strip()
        .str.replace("\u00a0", "", regex=False)
        .str.replace("\u202f", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce"
    )


def separator(path):
    with path.open(encoding="utf-8-sig") as f:
        first = f.readline()
    try:
        return csv.Sniffer().sniff(first, delimiters=";,\t").delimiter
    except csv.Error:
        return ";" if first.count(";") > first.count(",") else ","


def population_source(year):
    candidates = [
        RAW / f"population_{year}.csv",
        RAW / f"population_brute_{year}.csv",
        RAW / "population_brute.csv",
        ROOT / "population_brute.csv"
    ]
    return next((p for p in candidates if p.is_file()), None)


def population_communes(year):
    path = population_source(year)
    if path is None:
        print(f"  [INFO] population municipale {year} : fichier absent")
        return None

    sep = separator(path)
    header = pd.read_csv(path, sep=sep, nrows=0, encoding="utf-8-sig").columns
    names = {str(x).strip().upper(): x for x in header}

    def column(*candidates):
        return next((names[c] for c in candidates if c in names), None)

    geo = column("GEO", "CODGEO", "CODE_COMMUNE")
    year_col = column("TIME_PERIOD", "ANNEE")
    value = column("OBS_VALUE_NIVEAU", "OBS_VALUE", "PMUN")
    measure = column("POPREF_MEASURE", "POP_MEASURE", "POPULATION_MEASURE")
    mult = column("UNIT_MULT")

    if not geo or not value or (year_col is None and str(year) not in path.name):
        raise ValueError(f"Population : schéma ou année non vérifiable dans {path.name}")
    if measure is None and value.upper() != "PMUN":
        raise ValueError("Population : mesure PMUN non identifiable")

    use = list(dict.fromkeys(x for x in (geo, year_col, value, measure, mult) if x))
    parts = []
    for chunk in pd.read_csv(path, sep=sep, usecols=use, dtype=str,
                             chunksize=150_000, encoding="utf-8-sig"):
        mask = pd.Series(True, index=chunk.index)
        if year_col:
            mask &= chunk[year_col].eq(str(year))
        if measure:
            mask &= chunk[measure].eq("PMUN")
        d = chunk.loc[mask].copy()
        if d.empty:
            continue
        d["code_commune"] = d[geo].map(code_commune)
        d = d.dropna(subset=["code_commune"])
        if d.empty:
            continue
        d["population_municipale"] = numeric(d[value])
        if mult:
            d["population_municipale"] *= 10 ** numeric(d[mult])
        parts.append(d[["code_commune", "population_municipale"]])

    if not parts:
        print(f"  [INFO] aucune population municipale PMUN pour {year} dans {path.name}")
        return None
    result = pd.concat(parts, ignore_index=True)
    if result.code_commune.duplicated().any():
        raise ValueError("Population : doublons communaux - autres dimensions à filtrer")
    if result.population_municipale.isna().any() or (result.population_municipale < 0).any():
        raise ValueError("Population : valeurs manquantes ou négatives")
    return result


def logements_communes(year):
    path = PROCESSED / str(year) / f"residences_secondaires_occasionnelles_{year}_communes.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Script 47 : logements {year} absents : {path}")

    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    required = {
        "annee_logement", "code_commune",
        "residences_secondaires_occasionnelles", "indicateur_insee"
    }
    if missing := (required - set(df.columns)):
        raise ValueError(f"Logements : colonnes absentes {sorted(missing)}")
    if not df["annee_logement"].eq(str(year)).all():
        raise ValueError(f"Logements : millésime différent de {year}")
    if not df["indicateur_insee"].eq("DW_SEC_DW_OCC").all():
        raise ValueError("Logements : indicateur inattendu, DW_SEC_DW_OCC requis")
    df["code_commune"] = df["code_commune"].map(code_commune)
    df = df.dropna(subset=["code_commune"]).copy()
    df["code_departement"] = df["code_commune"].map(departement)
    df = df[df["code_departement"].isin(METRO)].copy()
    df["residences_secondaires_occasionnelles"] = numeric(
        df["residences_secondaires_occasionnelles"]
    )
    if df.empty or df.code_commune.duplicated().any():
        raise ValueError("Logements : communes absentes ou en double")
    if (df["residences_secondaires_occasionnelles"].isna().any()
            or df["residences_secondaires_occasionnelles"].lt(0).any()):
        raise ValueError("Logements : valeur manquante ou négative")
    # Garder la provenance effective des logements (observation/proxy).
    for key, default in (("annee_reference_logements", str(year)),
                         ("statut_donnee", "OBSERVEE_INSEE")):
        if key not in df.columns:
            df[key] = default
    return df[["code_commune", "code_departement",
               "residences_secondaires_occasionnelles",
               "annee_reference_logements", "statut_donnee"]].rename(
                   columns={"statut_donnee": "statut_logements"})


def totaux_metropole_valides(year):
    """Entrée indépendante, vérifiée : NE PAS utiliser la synthèse 46 (_T).

    Format CSV requis :
    annee,categorie,nuites,perimetre_destination,source_reference
    2023,famille_amis,<valeur>,FRANCE_METROPOLITAINE,<référence vérifiable>
    2023,residences_secondaires,<valeur>,FRANCE_METROPOLITAINE,<référence vérifiable>
    """
    path = PROCESSED / str(year) / f"nuites_non_marchandes_metropole_validees_{year}.csv"
    if not path.is_file():
        return None
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    required = {"annee", "categorie", "nuites",
                "perimetre_destination", "source_reference"}
    if missing := (required - set(df.columns)):
        raise ValueError(f"Totaux métropole : colonnes manquantes {sorted(missing)}")
    if len(df) != 2 or set(df["categorie"]) != set(CATEGORIES):
        raise ValueError("Totaux métropole : exactement deux catégories requises")
    if not df["annee"].eq(str(year)).all():
        raise ValueError("Totaux métropole : année incohérente")
    if not df["perimetre_destination"].eq("FRANCE_METROPOLITAINE").all():
        raise ValueError("Totaux métropole : destination non validée")
    if df["source_reference"].fillna("").str.strip().eq("").any():
        raise ValueError("Totaux métropole : références des sources obligatoires")
    df["nuites"] = numeric(df["nuites"])
    if df["nuites"].isna().any() or df["nuites"].lt(0).any():
        raise ValueError("Totaux métropole : valeurs invalides")
    return df.set_index("categorie")["nuites"].to_dict()


def allocation(year, df, totaux, folder):
    if df["population_municipale"].isna().any():
        raise ValueError("Allocation impossible : population communale incomplète")
    if df["residences_secondaires_occasionnelles"].isna().any():
        raise ValueError("Allocation impossible : logements communaux incomplets")
    if df["population_municipale"].sum() <= 0 or df["residences_secondaires_occasionnelles"].sum() <= 0:
        raise ValueError("Allocation impossible : dénominateur nul")

    # Le nombre de communes de chaque millésime n'est pas fixé a priori,
    # mais une forte perte d'appariement bloque la répartition.
    df = df.copy()
    df["nuites_famille_amis_estimees"] = (
        df["poids_famille_amis"] * totaux["famille_amis"]
    )
    df["nuites_residences_secondaires_estimees"] = (
        df["poids_residences_secondaires"] * totaux["residences_secondaires"]
    )
    df["annee_nuitees"] = year
    df["type_donnee"] = "ESTIMATION_COMMUNALE"
    df["source_totaux"] = "nuitees_non_marchandes_metropole_validees"
    for key, output in (
        ("famille_amis", "nuites_famille_amis_estimees"),
        ("residences_secondaires", "nuites_residences_secondaires_estimees"),
    ):
        diff = abs(df[output].sum() - totaux[key])
        if diff > max(0.01, 1e-10 * totaux[key]):
            raise ValueError(f"Conservation des totaux non respectée : {key}")
    path = folder / f"nuites_non_marchandes_communales_estimees_{year}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  [OK] {len(df):,} communes, totaux conservés : {path}")


def main():
    args = cli()
    years = [args.year] if args.year else YEARS
    for year in years:
        print(f"\n=== SCRIPT 49 : {year} ===")
        folder = PROCESSED / str(year)
        folder.mkdir(parents=True, exist_ok=True)
        try:
            logements = logements_communes(year)
            df = logements.copy()

            # Priorité à l'année étudiée si sa population est disponible.
            # Sinon, utiliser *toute* la population PMUN 2023 comme proxy ;
            # ne jamais mélanger des années dans une même clé de répartition.
            pop = population_communes(year) if year != 2023 else None
            if pop is None:
                pop = population_communes(2023)
                annee_reference_population = 2023
                statut_population = (
                    "OBSERVEE_INSEE" if year == 2023 else "PROXY_2023"
                )
            else:
                annee_reference_population = year
                statut_population = "OBSERVEE_INSEE"

            if pop is None:
                df["population_municipale"] = float("nan")
                statut_population = "NON_DISPONIBLE"
            else:
                df = df.merge(pop, how="left", on="code_commune", validate="one_to_one")
                # Si une source de l'année étudiée n'apparie pas entièrement
                # les communes, revenir *intégralement* à PMUN 2023.
                if df["population_municipale"].isna().any() and year != 2023:
                    fallback = population_communes(2023)
                    if fallback is not None:
                        df = df.drop(columns="population_municipale").merge(
                            fallback, how="left", on="code_commune", validate="one_to_one"
                        )
                        annee_reference_population = 2023
                        statut_population = "PROXY_2023"

            df["annee_reference_population"] = (
                annee_reference_population if pop is not None else pd.NA
            )
            df["statut_population"] = statut_population
            df.insert(0, "annee", year)
            df["poids_residences_secondaires"] = (
                df["residences_secondaires_occasionnelles"]
                / df["residences_secondaires_occasionnelles"].sum()
            )

            # Ne pas répartir les nuitées des familles sur les seuls
            # codes appariés si la population de certaines communes manque.
            pop_complete = df["population_municipale"].notna().all()
            if pop_complete and df["population_municipale"].sum() > 0:
                df["poids_famille_amis"] = (
                    df["population_municipale"] / df["population_municipale"].sum()
                )
            else:
                df["poids_famille_amis"] = float("nan")

            path = folder / f"cles_repartition_non_marchand_{year}.csv"
            df.to_csv(path, index=False, encoding="utf-8-sig")
            print(f"  [OK] {len(df):,} communes, logements disponibles")
            print(f"  Population complète : {pop_complete}")
            print(f"  Population : {statut_population}, référence : "
                  f"{annee_reference_population if pop is not None else 'absente'}")
            print(f"  Clés communales : {path}")

            totals = totaux_metropole_valides(year)
            if totals is None:
                print("  [ATTENTE] Pas de totaux de nuitées validés pour les séjours")
                print("            en France métropolitaine : aucune allocation.")
                continue
            if not pop_complete:
                raise ValueError("Population manquante : allocation interdite")
            allocation(year, df, totals, folder)
        except (FileNotFoundError, ValueError) as exc:
            print(f"  [NON TRAITÉ] {exc}")
            if args.strict:
                raise
    print("\n=== SCRIPT 49 TERMINÉ ===")
    print("Les clés préparées ne sont pas des nuitées estimées.")
    print("TRAVEL_DEST=_T du script 46 n'est jamais alloué automatiquement.")


if __name__ == "__main__":
    main()
