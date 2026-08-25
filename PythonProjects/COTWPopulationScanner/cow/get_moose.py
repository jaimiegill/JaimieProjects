import io
import json
import sys
import zlib
from collections import Counter
from pathlib import Path

BASE_DIR = Path(r"C:\Users\gills\cow\data")
sys.path.insert(0, str(BASE_DIR))

try:
    from deca.ff_adf import Adf
    from deca.file import ArchiveFile
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

POP_FILE = BASE_DIR / "animal_population_2"

EXPLICIT_FUR_MAP_MALE = {
    0: "Brown",
    1: "Dark Brown",
    2: "Tan",
    3: "Piebald (Rare)",
    4: "Albino (V.Rare)",
    5: "Melanistic (V.Rare)",
}

EXPLICIT_FUR_MAP_FEMALE = {
    0: "Brown",
    1: "Dark Brown",
    2: "Tan",
    3: "Piebald (Rare)",
    4: "Albino (V.Rare)",
    5: "Melanistic (V.Rare)",
}

GO_FUR_NAMES = [
    "Ashen",
    "Birch",
    "Mocha",
    "Oak",
    "Speckled",
    "Spruce",
    "Timber",
    "Two-Tone",
]

ZONE_TYPE_MAP = {
    0: "Zone",
    1: "Feeding",
    2: "Drinking",
    3: "Resting",
}


def apex_seed_to_float(seed: int) -> float:
    """Simulates Apex engine PRNG seed normalization to extract [0.0, 1.0) float."""
    seed = int(seed) & 0xFFFFFFFF
    state = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
    return (state >> 8) / 16777216.0


def resolve_moose_fur_from_seed(
    seed: int, gender: str = "Male", is_great_one: bool = False
) -> str:
    if seed is None:
        return "Unknown"

    u = apex_seed_to_float(seed)

    if is_great_one:
        idx = min(int(u * len(GO_FUR_NAMES)), len(GO_FUR_NAMES) - 1)
        return f"{GO_FUR_NAMES[idx]} (Fabled)"

    if u >= 0.9997:
        return "Melanistic (V.Rare)"
    elif u >= 0.9992:
        return "Albino (V.Rare)"
    elif u >= 0.9980:
        return "Piebald (Rare)"

    norm_u = u / 0.9980

    if gender == "Male":
        if norm_u < 0.40:
            return "Brown"
        elif norm_u < 0.75:
            return "Dark Brown"
        else:
            return "Tan"
    else:
        if norm_u < 0.45:
            return "Brown"
        elif norm_u < 0.80:
            return "Dark Brown"
        else:
            return "Tan"


def get_fur_info(
    anim: dict, gender: str = "Male", is_great_one: bool = False
) -> str:
    for key in ["VisualVariation", "Variation", "FurId"]:
        val = anim.get(key)
        if isinstance(val, int) and val >= 0:
            if is_great_one and val < len(GO_FUR_NAMES):
                return f"{GO_FUR_NAMES[val]} (Fabled)"

            fur_map = (
                EXPLICIT_FUR_MAP_MALE
                if gender == "Male"
                else EXPLICIT_FUR_MAP_FEMALE
            )
            if val in fur_map:
                return fur_map[val]
            return f"Index {val}"

    seed = anim.get("VisualVariationSeed")
    if seed is not None:
        resolved = resolve_moose_fur_from_seed(
            seed, gender=gender, is_great_one=is_great_one
        )
        return f"{resolved} (Seed)"

    return "Unknown"


def extract_animal_level(anim: dict, is_great_one: bool = False) -> int:
    if is_great_one:
        return 10

    for key in ["Difficulty", "DifficultyLevel", "Level", "AnimalLevel"]:
        val = anim.get(key)
        if val is not None:
            return int(val)

    score = float(anim.get("Score", anim.get("TrophyScore", 0.0)))
    gender = "Male" if anim.get("Gender", 0) == 1 else "Female"

    if gender == "Female":
        return 1
    if score >= 274.9:
        return 5
    elif score >= 220.0:
        return 4
    elif score >= 160.0:
        return 3
    elif score >= 100.0:
        return 2
    return 1


def load_adf_file(file_path: Path):
    if not file_path.exists():
        return None
    try:
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
        decompressed = zlib.decompress(
            raw_bytes[32:] if raw_bytes.startswith(b"SAVE") else raw_bytes
        )
        stream = ArchiveFile(io.BytesIO(decompressed[5:]))
        adf = Adf()
        adf.deserialize(stream)
        return adf
    except Exception as e:
        print(f"[-] Warning: Could not parse {file_path.name}: {e}")
        return None


def parse_position(pos):
    """Extracts 2D/3D map coordinates from raw position objects."""
    if pos is None:
        return None

    x, y, z = 0.0, 0.0, 0.0

    if isinstance(pos, (list, tuple)):
        if len(pos) >= 3:
            x, y, z = float(pos[0]), float(pos[1]), float(pos[2])
        elif len(pos) == 2:
            x, z = float(pos[0]), float(pos[1])
    elif isinstance(pos, dict):
        x = float(pos.get("X", pos.get("x", pos.get("m_X", 0.0))))
        y = float(pos.get("Y", pos.get("y", pos.get("m_Y", 0.0))))
        z = float(pos.get("Z", pos.get("z", pos.get("m_Z", 0.0))))

    if x != 0.0 or z != 0.0:
        return round(x, 2), round(y, 2), round(z, 2)
    return None


def build_spatial_map():
    """Builds the spatial dictionary using discovered NeedZoneData keys."""
    spatial_map = {}
    target_path = BASE_DIR / "found_need_zones_adf"
    if not target_path.exists():
        return spatial_map

    adf = load_adf_file(target_path)
    if not adf or not adf.table_instance_values:
        return spatial_map

    root_node = adf.table_instance_values[0]
    nz_data_list = root_node.get("NZData", [])

    for reserve_entry in nz_data_list:
        if not isinstance(reserve_entry, dict):
            continue

        need_zones = reserve_entry.get("NeedZoneData", [])
        for zone in need_zones:
            if not isinstance(zone, dict):
                continue

            guid = zone.get("NeedZoneId")
            pos_raw = zone.get("Position")
            z_type_id = zone.get("NeedType", 0)

            if guid is not None and pos_raw is not None:
                coords = parse_position(pos_raw)
                if coords:
                    z_str = ZONE_TYPE_MAP.get(int(z_type_id), "Zone")
                    for key_var in [guid, str(guid)]:
                        try:
                            key_var = int(key_var)
                        except (ValueError, TypeError):
                            pass
                        spatial_map[key_var] = {
                            "coords": (coords[0], coords[2]),  # X, Z
                            "type": z_str,
                        }

    print(f"[+] Discovered {len(spatial_map)} spatial node mappings.")
    return spatial_map


def sanitize(data):
    if isinstance(data, dict):
        return {
            k: sanitize(v) for k, v in data.items() if k != "HuntingPressureMap"
        }
    elif isinstance(data, list):
        return [sanitize(x) for x in data]
    elif isinstance(data, bytes):
        return data.decode("utf-8", errors="ignore").replace("\x00", "")
    elif isinstance(data, str):
        return data.replace("\x00", "")
    return data


def scan_and_extract_moose():
    adf = load_adf_file(POP_FILE)
    if not adf:
        print(f"Error: Population file not found at {POP_FILE}")
        return

    spatial_map = build_spatial_map()

    table_data = adf.table_instance_values[0]
    pops = table_data.get("Populations", [])
    species_data = {}

    for pop in pops:
        hash_id = pop.get("NameHashId")
        groups = pop.get("Groups", [])
        animals = []

        for herd_idx, g in enumerate(groups):
            spawn_area = g.get("SpawnAreadId", g.get("SpawnAreaId", "Unknown"))

            need_zone_guids = []
            for guid in g.get("NeedZonePathGuids", []):
                try:
                    need_zone_guids.append(int(guid))
                except (ValueError, TypeError):
                    need_zone_guids.append(str(guid))

            herd_coords = []
            for z_guid in need_zone_guids:
                if z_guid in spatial_map:
                    info = spatial_map[z_guid]
                    x, z = info["coords"]
                    herd_coords.append(f"{info['type']} ({x}, {z})")

            if not herd_coords and spawn_area in spatial_map:
                info = spatial_map[spawn_area]
                x, z = info["coords"]
                herd_coords.append(f"Spawn ({x}, {z})")

            herd_id = g.get("Id", herd_idx)

            for anim in g.get("Animals", []):
                clean_anim = sanitize(anim)
                clean_anim["NameHashId"] = hash_id
                clean_anim["HerdId"] = herd_id
                clean_anim["SpawnAreaId"] = spawn_area
                clean_anim["NeedZoneGuids"] = need_zone_guids
                clean_anim["ResolvedCoords"] = herd_coords
                animals.append(clean_anim)

        if animals:
            species_data[hash_id] = animals

    moose_hash = None
    for hash_id, animals in species_data.items():
        weights = [a.get("Weight", 0.0) for a in animals if "Weight" in a]
        if weights:
            max_w = max(weights)
            avg_w = sum(weights) / len(weights)
            if max_w > 500 and avg_w > 300:
                moose_hash = hash_id
                break

    if moose_hash is None:
        print("[-] Could not identify Moose population by weight range.")
        return

    raw_moose_list = species_data[moose_hash]
    formatted_moose = []
    level_counts = Counter()

    for m in raw_moose_list:
        raw_gender = m.get("Gender", m.get("gender", 0))
        gender_str = "Male" if raw_gender == 1 else "Female"

        weight = round(m.get("Weight", 0.0), 2)
        score = round(
            m.get("Score", m.get("TrophyScore", m.get("TrophyRating", 0.0))), 2
        )

        is_go = bool(
            m.get("IsGreatOne")
            or m.get("is_great_one")
            or m.get("IsFabled")
            or (weight >= 600.0 and score >= 300.0)
        )

        level = extract_animal_level(m, is_great_one=is_go)
        level_counts[level] += 1

        is_diamond = gender_str == "Male" and not is_go and (score >= 274.9)
        fur_info = get_fur_info(m, gender=gender_str, is_great_one=is_go)

        resolved = m.get("ResolvedCoords", [])
        coord_str = ", ".join(resolved[:2]) if resolved else "No Zone Data"
        if len(resolved) > 2:
            coord_str += f" (+{len(resolved)-2} more)"

        moose_record = {
            "Rank": 0,
            "Gender": gender_str,
            "Level": level,
            "Score": score,
            "Weight_kg": weight,
            "IsDiamond": "YES" if is_diamond else "No",
            "IsGreatOne": "YES" if is_go else "No",
            "FurInfo": fur_info,
            "NeedZoneCoords": coord_str,
            "AllHerdCoordsList": resolved,
            "Id": m.get("Id"),
            "VisualVariationSeed": m.get("VisualVariationSeed"),
        }
        formatted_moose.append(moose_record)

    formatted_moose.sort(
        key=lambda x: (
            1 if x.get("IsGreatOne") == "YES" else 0,
            1 if x.get("IsDiamond") == "YES" else 0,
            x.get("Score", 0.0),
            x.get("Weight_kg", 0.0),
        ),
        reverse=True,
    )

    for rank, item in enumerate(formatted_moose, 1):
        item["Rank"] = rank

    total_moose = len(formatted_moose)
    diamonds_count = sum(
        1 for x in formatted_moose if x.get("IsDiamond") == "YES"
    )
    go_count = sum(1 for x in formatted_moose if x.get("IsGreatOne") == "YES")

    print("=" * 145)
    print(
        "                                MEDVED-TAIGA MOOSE POPULATION EXTRACTION SCANNER                                "
    )
    print("=" * 145 + "\n")
    print(
        f"Total Moose: {total_moose} | Diamonds: {diamonds_count} | Great Ones: {go_count}\n"
    )

    # --- LEVEL BREAKDOWN TABLE ---
    print("LEVEL BREAKDOWN SUMMARY")
    print("-" * 40)
    print(f"{'Level':<12} | {'Count':<8} | {'Percentage':<10}")
    print("-" * 40)
    
    # Sort levels numerically (e.g., Level 1 to 10)
    for lvl in sorted(level_counts.keys()):
        count = level_counts[lvl]
        pct = (count / total_moose) * 100 if total_moose > 0 else 0.0
        lvl_label = f"Level {lvl}" if lvl != 10 else "Level 10 (G1)"
        print(f"{lvl_label:<12} | {count:<8} | {pct:>6.2f}%")
    print("-" * 40 + "\n")

    # --- INDIVIDUAL ANIMAL TABLE ---
    print(
        f"{'Rank':<5} | {'Gender':<7} | {'Level':<6} | {'Score':<7} | {'Weight':<8} | {'Diamond':<8} | {'Fur Info':<22} | {'Need Zone Coords (Type & Pos)':<40} | {'Visual Seed':<12}"
    )
    print("-" * 145)

    for m in formatted_moose:
        print(
            f"{m['Rank']:<5} | {m['Gender']:<7} | {str(m['Level']):<6} | {m['Score']:<7} | {m['Weight_kg']:<6}kg | {m['IsDiamond']:<8} | {m['FurInfo']:<22} | {m['NeedZoneCoords']:<40} | {str(m.get('VisualVariationSeed')):<12}"
        )

    out_file = BASE_DIR / "moose_all_binary_keys.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(formatted_moose, f, indent=2)

    print(f"\n[+] Full dataset saved to: {out_file}")


if __name__ == "__main__":
    scan_and_extract_moose()