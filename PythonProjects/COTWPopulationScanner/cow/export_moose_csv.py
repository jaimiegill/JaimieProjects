import csv
import io
import sys
import zlib
from pathlib import Path

BASE_DIR = Path(r"C:\Users\gills\cow")
sys.path.insert(0, str(BASE_DIR))

try:
    from deca.ff_adf import Adf
    from deca.file import ArchiveFile
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

POP_FILE = BASE_DIR / "animal_population_2"
CSV_FILE = BASE_DIR / "moose_population.csv"


def export_moose_csv():
    if not POP_FILE.exists():
        print(f"Error: File not found at {POP_FILE}")
        return

    with open(POP_FILE, "rb") as f:
        raw_bytes = f.read()

    decompressed = zlib.decompress(
        raw_bytes[32:] if raw_bytes.startswith(b"SAVE") else raw_bytes
    )

    stream = ArchiveFile(io.BytesIO(decompressed[5:]))
    adf = Adf()
    adf.deserialize(stream)

    pops = adf.table_instance_values[0].get("Populations", [])

    moose_entries = []

    # Identify Moose population group by weight signature (>500kg max weight)
    for pop in pops:
        hash_id = pop.get("NameHashId")
        groups = pop.get("Groups", [])

        species_animals = []
        for g in groups:
            spawn_area = g.get("SpawnAreaId")
            for anim in g.get("Animals", []):
                species_animals.append((anim, spawn_area, hash_id))

        weights = [
            a[0].get("Weight", 0.0) for a in species_animals if "Weight" in a[0]
        ]
        if (
            weights
            and max(weights) > 500
            and (sum(weights) / len(weights)) > 300
        ):
            moose_entries = species_animals
            break

    if not moose_entries:
        print("[-] Could not identify Moose species group.")
        return

    csv_rows = []
    for anim, spawn_area, hash_id in moose_entries:
        # Convert Gender integer (1 = Male, 2 = Female)
        raw_gender = anim.get("Gender")
        if raw_gender == 1:
            gender = "Male"
        elif raw_gender == 2:
            gender = "Female"
        else:
            gender = f"Unknown ({raw_gender})"

        # Extract Level / Difficulty
        level = anim.get(
            "Level", anim.get("Difficulty", anim.get("Rank", "N/A"))
        )

        # Flatten Map Position coordinates
        pos = anim.get("MapPosition", {})
        pos_x = pos.get("X", "N/A") if isinstance(pos, dict) else "N/A"
        pos_y = pos.get("Y", "N/A") if isinstance(pos, dict) else "N/A"
        pos_z = pos.get("Z", "N/A") if isinstance(pos, dict) else "N/A"

        row = {
            "Species": "Moose",
            "Gender": gender,
            "Level": level,
            "Weight_kg": round(anim.get("Weight", 0.0), 2),
            "Trophy_Score": round(anim.get("Score", 0.0), 2),
            "Position_X": round(pos_x, 2)
            if isinstance(pos_x, (int, float))
            else pos_x,
            "Position_Y": round(pos_y, 2)
            if isinstance(pos_y, (int, float))
            else pos_y,
            "Position_Z": round(pos_z, 2)
            if isinstance(pos_z, (int, float))
            else pos_z,
            "VisualVariationSeed": anim.get("VisualVariationSeed", ""),
            "SpawnAreaId": spawn_area,
            "NameHashId": hash_id,
            "IsScripted": anim.get("IsScripted", 0),
            "ID": anim.get("Id", 0),
        }

        # Include any remaining extra raw attributes from the animal dictionary
        for k, v in anim.items():
            if k not in [
                "Gender",
                "Weight",
                "Score",
                "MapPosition",
                "VisualVariationSeed",
                "IsScripted",
                "Id",
                "Level",
                "Difficulty",
            ]:
                row[f"Raw_{k}"] = str(v)

        csv_rows.append(row)

    # Write output to CSV file
    if csv_rows:
        fieldnames = list(csv_rows[0].keys())
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)

        print(
            f"[+] Successfully exported {len(csv_rows)} Moose records to"
            f" CSV:\n    {CSV_FILE}\n"
        )

        print("--- FIRST 3 ROWS SAMPLE ---")
        for sample in csv_rows[:3]:
            print(sample)


if __name__ == "__main__":
    export_moose_csv()