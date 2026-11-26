"""CAFÉ — Script 54 : un classeur par année, exactement 2 onglets.

Commande :
    python src/tourisme/54_assembler_cafe_2022_2025.py

Dépendance : python -m pip install XlsxWriter
Sorties : data/final/tourisme/CAFE_TOURISME_{annee}.xlsx
         data/final/tourisme/{annee}/CAFE_TOURISME_{annee}_{TYPE}_V2.csv

MARCHAND : résultats du script 53.
NON_MARCHAND : s'il existe un ancien CSV V2 contenant réellement des
valeurs, les afficher dans l'onglet (statut NON VALIDÉ, indiqué dans Excel).
Sinon conserver les cases de nuitées vides : aucune allocation inventée.
"""
from pathlib import Path
import csv
import math

import pandas as pd

try:
    import xlsxwriter
except ImportError:
    raise SystemExit("Installe XlsxWriter : python -m pip install XlsxWriter")

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed" / "tourisme"
LEGACY = ROOT / "src" / "data" / "processed" / "tourisme"
FINAL = ROOT / "data" / "final" / "tourisme"
YEARS = (2022, 2023, 2024, 2025)
MONTHS = ("january", "february", "march", "april", "may", "june",
          "july", "august", "september", "october", "november", "december")


def expected_columns(types):
    fields = ["geocode", "admin_level"]
    for label in types:
        prefix = f"{label}_nights" if label != "secondary_residence" else label
        fields.extend([f"{prefix}_year"] +
                      [f"{prefix}_{m}" for m in MONTHS])
    return fields


M_COLS = expected_columns(("hotel", "camping", "other"))
N_COLS = expected_columns(("family", "secondary_residence"))
ANNUAL = {
    "hotel_nights_year": "nuites_hotels_estimees",
    "camping_nights_year": "nuites_campings_estimees",
    "other_nights_year": "nuites_autres_estimees",
}


def read_csv_auto(path):
    # Le séparateur est déterminé par l'EN-TÊTE, jamais par csv.Sniffer.
    # csv.Sniffer échoue sur certains fichiers CSV INSEE volumineux.
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        header = f.readline()
        if not header.strip():
            raise ValueError(f"En-tête CSV vide : {path}")
        delimiter = ";" if header.count(";") > header.count(",") else ","
        f.seek(0)
        rd = csv.DictReader(f, delimiter=delimiter)
        columns = list(rd.fieldnames or [])
        if len(columns) < 2:
            raise ValueError(f"CSV mal séparé : {path} (séparateur {delimiter!r})")
        rows = list(rd)
        if any(None in r for r in rows):
            raise ValueError(f"CSV : certaines lignes ont trop de colonnes : {path}")
        return columns, rows


def number(value):
    s = str(value if value is not None else "").strip()
    if not s or s.lower() in ("nan", "null", "none", "<na>"):
        return None
    try:
        n = float(s.replace(",", "."))
        return n if math.isfinite(n) else None
    except ValueError:
        return None


def geo(value, level):
    code = str(value).strip().upper()
    if level == "COM" and code.isdigit():
        return code.zfill(5)
    if level == "DEP" and code.isdigit():
        return code.zfill(2)
    if level == "REG" and code.isdigit():
        return code.zfill(2)
    return code


def normalise(rows, cols):
    result = []
    seen = set()
    for r in rows:
        level = str(r.get("admin_level", "")).strip().upper()
        if level not in ("COM", "DEP", "REG"):
            raise ValueError(f"admin_level incorrect : {level}")
        code = geo(r.get("geocode", ""), level)
        if not code:
            raise ValueError("geocode manquant")
        key = (level, code)
        if key in seen:
            raise ValueError(f"Doublon : {key}")
        seen.add(key)
        clean = {"geocode": code, "admin_level": level}
        for col in cols[2:]:
            raw = r.get(col, "")
            n = number(raw)
            if raw is not None and str(raw).strip() not in ("", "nan") and n is None:
                raise ValueError(f"Valeur non numérique : {col} = {raw!r}")
            clean[col] = n
        result.append(clean)
    rank = {"COM": 0, "DEP": 1, "REG": 2}
    result.sort(key=lambda x: (rank[x["admin_level"]], x["geocode"]))
    return result



def camping_profiles():
    """Profils INSEE de camping avril-septembre par région et année."""
    source = ROOT / "data" / "raw" / "tourisme" / "frequentation_brut.csv"
    if not source.is_file():
        raise FileNotFoundError(f"Source INSEE introuvable : {source}")
    cols = ["GEO", "FREQ", "TIME_PERIOD", "ACTIVITY", "TOUR_MEASURE",
            "TOUR_RESID", "UNIT_LOC_RANKING", "HOTEL_STA", "EQUIP",
            "OBS_VALUE_NIVEAU", "OBS_STATUS", "UNIT_MULT", "SEASONALITY"]
    raw = pd.read_csv(source, usecols=cols, dtype=str, low_memory=False)
    mask = (raw["FREQ"].eq("M") & raw["ACTIVITY"].eq("I553") &
            raw["TOUR_MEASURE"].eq("NIGHT_SPENT") &
            raw["TOUR_RESID"].eq("_T") &
            raw["UNIT_LOC_RANKING"].eq("_T") &
            raw["HOTEL_STA"].eq("_T") & raw["EQUIP"].eq("_Z") &
            raw["SEASONALITY"].eq("_Z") &
            raw["OBS_STATUS"].isin(["A", "P"]) &
            raw["TIME_PERIOD"].str.fullmatch(r"202[2-5]-(0[4-9])", na=False) &
            raw["GEO"].str.contains(r"-REG-", na=False))
    raw = raw.loc[mask].copy()
    raw["region"] = raw["GEO"].str.extract(r"-REG-(\d{2})$", expand=False)
    raw["annee"] = raw["TIME_PERIOD"].str[:4].astype(int)
    raw["mois"] = raw["TIME_PERIOD"].str[-2:].astype(int)
    raw["valeur"] = (pd.to_numeric(raw["OBS_VALUE_NIVEAU"], errors="coerce") *
                     10 ** pd.to_numeric(raw["UNIT_MULT"], errors="coerce"))
    profiles = {}
    for (year, region), group in raw.groupby(["annee", "region"]):
        if (set(group["mois"]) != set(range(4, 10)) or
                group["mois"].duplicated().any() or
                group["valeur"].isna().any() or
                (group["valeur"] < 0).any() or group["valeur"].sum() <= 0):
            continue
        weights = group.set_index("mois")["valeur"] / group["valeur"].sum()
        profiles[(year, region)] = {month: float(weights[month])
                                    for month in range(4, 10)}
    return profiles


def marchand(year, profiles):
    path = PROCESSED / str(year) / f"tourisme_marchand_mensuel_com_dep_reg_{year}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Exécuter le script 53 : {path}")
    columns, src = read_csv_auto(path)
    required = {"geocode", "admin_level", "code_departement", "code_region", *ANNUAL.values()}
    required.update(c for c in M_COLS[2:] if c not in ANNUAL and not c.startswith("camping_nights_"))
    if not required.issubset(columns):
        raise ValueError(f"Colonnes marchandes manquantes : {sorted(required - set(columns))}")

    # Lire l'annuel et les autres profils de 53. Recalculer indépendamment
    # les 12 mois camping depuis les observations régionales INSEE.
    data = []
    for r in src:
        row = {"geocode": r["geocode"], "admin_level": r["admin_level"],
               **{col: r.get(ANNUAL.get(col, col), "") for col in M_COLS[2:]}}
        data.append((row, r))
    rows = normalise([r for r, original in data], M_COLS)
    originals = {(str(x.get("admin_level", "")).strip().upper(),
                  geo(x.get("geocode", ""), str(x.get("admin_level", "")).strip().upper())): x
                 for _, x in data}
    for row in rows:
        if row["admin_level"] != "COM":
            continue
        orig = originals[("COM", row["geocode"])]
        annual = row["camping_nights_year"]
        monthcols = [f"camping_nights_{m}" for m in MONTHS]
        if annual is None:
            for col in monthcols:
                row[col] = None  # Information INSEE manquante, jamais zéro inventé
            continue
        if annual < 0:
            raise ValueError(f"Camping négatif : {row['geocode']}")
        region = geo(orig["code_region"], "REG")
        weights = profiles.get((year, region))
        if not weights:
            raise ValueError(f"Profil INSEE camping absent : {year} région {region}")
        # 0 hors avril-septembre = montant non alloué, PAS zéro observé.
        for i, col in enumerate(monthcols, start=1):
            row[col] = annual * weights[i] if 4 <= i <= 9 else 0.0

    # Reconstruction des mois camping DEP et REG depuis les COMMUNES,
    # en préservant les valeurs manquantes si un territoire est incomplet.
    com = [r for r in rows if r["admin_level"] == "COM"]
    maps = {}
    for level in ("DEP", "REG"):
        group = {}
        geo_column = "code_departement" if level == "DEP" else "code_region"
        for row in com:
            orig = originals[("COM", row["geocode"])]
            key = geo(orig[geo_column], level)
            group.setdefault(key, []).append(row)
        maps[level] = group

    monthcols = [f"camping_nights_{m}" for m in MONTHS]
    for row in rows:
        level = row["admin_level"]
        if level == "COM":
            continue
        members = maps[level].get(row["geocode"], [])
        for col in monthcols:
            if not members or any(member[col] is None for member in members):
                row[col] = None
            else:
                row[col] = sum(member[col] for member in members)
        if row["camping_nights_year"] is not None and all(row[col] is not None for col in monthcols):
            if abs(sum(row[col] for col in monthcols) - row["camping_nights_year"]) > 0.01:
                raise ValueError(f"Conservation camping impossible : {year} {level} {row['geocode']}")

    count = sum(1 for r in rows if r["admin_level"] == "COM" and r["camping_nights_april"] is not None)
    print(f"  [OK] Camping : {count:,} communes renseignées ; COM -> DEP -> REG")
    return rows


def source_non_marchand(year):
    filename = f"CAFE_TOURISME_{year}_NON_MARCHAND_V2.csv"
    # Priorité aux anciennes sorties réellement remplies ; le script 54
    # précédent a créé des fichiers entièrement vides.
    candidates = [
        LEGACY / str(year) / filename,
        PROCESSED / str(year) / filename,
    ]
    for path in candidates:
        if not path.is_file():
            continue
        columns, rows = read_csv_auto(path)
        if {"geocode", "admin_level", *N_COLS[2:]}.issubset(columns):
            if any(number(r.get("family_nights_year")) is not None or
                   number(r.get("secondary_residence_year")) is not None
                   for r in rows):
                return normalise(rows, N_COLS), True, path
    # Pas de valeurs non marchandes validées disponibles :
    # préserver seulement les territoires issus du script 50.
    path = PROCESSED / str(year) / f"cles_non_marchandes_com_dep_reg_{year}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Clés non marchandes absentes : {path}")
    _, rows = read_csv_auto(path)
    return normalise(rows, N_COLS), False, path


def export_csv(year, kind, cols, rows):
    dest = FINAL / str(year) / f"CAFE_TOURISME_{year}_{kind}_V2.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", newline="", encoding="utf-8-sig") as f:
        wr = csv.DictWriter(f, fieldnames=cols, delimiter=";")
        wr.writeheader()
        wr.writerows(rows)
    return dest


def add_sheet(wb, name, cols, rows, unvalidated=False):
    ws = wb.add_worksheet(name)
    ws.set_tab_color("#D97706" if unvalidated else "#177E89")
    ws.freeze_panes(1, 2)
    ws.set_row(0, 38)
    ws.set_column(0, 0, 15)
    ws.set_column(1, 1, 14)
    ws.set_column(2, len(cols) - 1, 20)
    h = wb.add_format({"bold": True, "font_color": "#FFFFFF",
                       "bg_color": "#92400E" if unvalidated else "#16324F",
                       "text_wrap": True, "valign": "vcenter",
                       "border": 1, "border_color": "#CBD5E1"})
    code_fmt = wb.add_format({"num_format": "@"})
    num_fmt = wb.add_format({"num_format": "#,##0.00"})
    label_fmt = wb.add_format({})
    for c, name in enumerate(cols):
        ws.write_string(0, c, name, h)
    if unvalidated:
        ws.write_comment(
            0, 2,
            "ATTENTION : nuitées non marchandes reprises d'un ancien CSV V2 ; "
            "leur allocation géographique et leur profil mensuel ne sont pas validés. "
            "Données à usage exploratoire uniquement."
        )
    for idx, row in enumerate(rows, start=1):
        ws.write_string(idx, 0, row["geocode"], code_fmt)
        ws.write_string(idx, 1, row["admin_level"], label_fmt)
        for c, col in enumerate(cols[2:], start=2):
            v = row.get(col)
            if v is not None:
                ws.write_number(idx, c, v, num_fmt)
    ws.autofilter(0, 0, len(rows), len(cols) - 1)


def main():
    FINAL.mkdir(parents=True, exist_ok=True)
    profiles = camping_profiles()
    for year in YEARS:
        print(f"\n=== CAFÉ {year} ===")
        m = marchand(year, profiles)
        nm, unvalidated, source = source_non_marchand(year)
        if unvalidated:
            print(f"  [ATTENTION] NON_MARCHAND : valeurs historiques NON VALIDÉES : {source}")
        else:
            print("  [ATTENTE] NON_MARCHAND : pas de nuitées allouables ; colonnes vides.")
        dest = FINAL / f"CAFE_TOURISME_{year}.xlsx"
        with xlsxwriter.Workbook(str(dest), {"constant_memory": True}) as wb:
            add_sheet(wb, "MARCHAND", M_COLS, m)
            add_sheet(wb, "NON_MARCHAND", N_COLS, nm, unvalidated)
        export_csv(year, "MARCHAND", M_COLS, m)
        export_csv(year, "NON_MARCHAND", N_COLS, nm)
        print(f"  [OK] {dest} | MARCHAND {len(m):,} lignes | NON_MARCHAND {len(nm):,} lignes")
    print("\nTerminé : exactement deux onglets par classeur.")


if __name__ == "__main__":
    main()
