import json
import pandas as pd
import gerda

OUTPUT_FILE = "ergebnisse.json"

DATASETS = {
    "bundestag": "federal_muni_harm_25",
    "landtag": "state_harm_25",
    "kommunal": "municipal_harm_25",
}

# Zuordnung: GERDA-Spaltenname -> sauberer Schluessel fuer deine Karte
PARTY_COLUMNS = {
    "cdu": "CDU",
    "csu": "CSU",
    "cdu_csu": "CDU/CSU",
    "spd": "SPD",
    "gruene": "Grüne",
    "grune": "Grüne",
    "fdp": "FDP",
    "linke_pds": "Linke",
    "linke": "Linke",
    "afd": "AfD",
    "bsw": "BSW",
    "freie_waehler": "Freie Wähler",
    "freie_wahler": "Freie Wähler",
}


def extract_latest(dataset_name: str) -> dict:
    df = gerda.load(dataset_name, refresh=True)

    ags_col = next((c for c in ("ags", "ags_25", "ags_21") if c in df.columns), None)
    year_col = next((c for c in ("election_year", "year") if c in df.columns), None)
    if not ags_col or not year_col:
        raise ValueError(f"Unerwartete Spalten in {dataset_name}: {list(df.columns)}")

    # AGS als 8-stelligen Text mit fuehrender Null sichern (wichtig z. B. fuer SH/HH/NI)
    df[ags_col] = df[ags_col].astype(str).str.replace(r"\.0$", "", regex=True).str.strip().str.zfill(8)
    df = df.dropna(subset=[ags_col, year_col])

    # Pro Gemeinde nur die jeweils neueste Wahl behalten
    df = df.sort_values(year_col).groupby(ags_col, as_index=False).last()

    available_parties = [c for c in PARTY_COLUMNS if c in df.columns]
    result = {}

    for row in df.to_dict(orient="records"):
        ags = row[ags_col]
        entry = {"jahr": int(row[year_col])}

        if "turnout" in row and pd.notna(row["turnout"]):
            entry["wahlbeteiligung"] = round(float(row["turnout"]) * 100, 1)

        parteien = {}
        for col in available_parties:
            val = row.get(col)
            if pd.notna(val) and float(val) > 0:
                label = PARTY_COLUMNS[col]
                parteien[label] = round(float(val) * 100, 1)

        if parteien:
            entry["parteien"] = parteien
            entry["staerkste"] = max(parteien, key=parteien.get)

        result[ags] = entry

    return result


def main():
    combined = {}
    for key, dataset_name in DATASETS.items():
        print(f"Lade {key} ({dataset_name})...")
        combined[key] = extract_latest(dataset_name)
        print(f"  -> {len(combined[key])} Gemeinden verarbeitet.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Fertig: {OUTPUT_FILE} wurde aktualisiert.")


if __name__ == "__main__":
    main()
