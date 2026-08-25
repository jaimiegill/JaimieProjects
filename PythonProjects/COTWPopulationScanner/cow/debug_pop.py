import io
import json
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


def sanitize(data):
    if isinstance(data, dict):
        return {
            k: sanitize(v)
            for k, v in data.items()
            if k != "HuntingPressureMap"
        }
    elif isinstance(data, list):
        return [sanitize(x) for x in data]
    elif isinstance(data, bytes):
        return data.decode("utf-8", errors="ignore").replace("\x00", "")
    elif isinstance(data, str):
        return data.replace("\x00", "")
    return data


def scan_population():
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

    print("==================================================")
    print("           SPECIES POPULATION BREAKDOWN           ")
    print("==================================================\n")

    all_moose = []

    for idx, pop in enumerate(pops):
        hash_id = pop.get("NameHashId")
        groups = pop.get("Groups", [])

        # Extract all animals across all subgroups/herds for this species
        species_animals = []
        for g in groups:
            for anim in g.get("Animals", []):
                clean_anim = sanitize(anim)
                clean_anim["SpawnAreaId"] = g.get("SpawnAreaId")
                species_animals.append(clean_anim)

        print(
            f"Species Slot {idx} | NameHashId: {hash_id} | Herds: {len(groups)} | Total Animals: {len(species_animals)}"
        )

        # Append to moose list if matched or dump all if filtering
        # Moose is typically identified by species ID/Hash in slot data
        all_moose.extend(species_animals)

    print("\n--------------------------------------------------")
    print(f"Total Combined Animals Found Across Map: {len(all_moose)}")

    # Export first non-empty species group sample to JSON
    out_file = BASE_DIR / "all_extracted_animals.json"
    with open(out_file, "w", encoding="utf-8") as out:
        json.dump(all_moose, out, indent=2)

    print(f"Exported full dataset to: {out_file}")


if __name__ == "__main__":
    scan_population()