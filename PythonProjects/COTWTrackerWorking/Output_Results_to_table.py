#!/usr/bin/env python3
"""
json_to_table_ascii.py

Reads parsed JSON produced by ADF_Reader.py and writes a fixed-width ASCII table
to Results_readable/animals_table.txt. Columns are separated with | and header
is underlined with dashes. Long fields are truncated to column width.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

INPUT_DIR = Path(r"C:\Users\gills\JaimieProjects\PythonProjects\COTWTrackerWorking\DecodedADFJSONFormat")
OUTPUT_FILE = INPUT_DIR / "animals_table.txt"

# Columns and their fixed widths (adjust widths as needed)
COLUMNS = [
    ("name_hash_id", 10),
    ("species", 20),
    ("species_confidence", 6),
    ("spawn_area_id", 10),
    ("need_zone_guids", 28),
    ("gender", 6),
    ("weight_kg", 8),
    ("score", 8),
    ("visual_variation_seed", 10),
    ("animal_id", 8),
    ("map_x", 8),
    ("map_y", 8),
]

ELLIPSIS = "…"

def load_all_records(input_dir: Path) -> List[Dict[str, Any]]:
    combined = input_dir / "all_animals.json"
    records: List[Dict[str, Any]] = []
    if combined.exists():
        with combined.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                records.extend(data)
            elif isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list):
                        records.extend(v)
    else:
        for p in sorted(input_dir.glob("*_parsed.json")):
            try:
                with p.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        records.extend(data)
            except Exception:
                continue
    return records

def fmt_list_field(val: Any, maxlen: int) -> str:
    if not val:
        return ""
    if isinstance(val, (list, tuple)):
        s = ";".join(str(x) for x in val)
    else:
        s = str(val)
    return truncate(s, maxlen)

def fmt_number(val: Any, maxlen: int) -> str:
    if val is None or val == "":
        return ""
    if isinstance(val, float):
        s = f"{val:.3f}".rstrip("0").rstrip(".")
    else:
        s = str(val)
    return truncate(s, maxlen)

def truncate(s: str, width: int) -> str:
    s = str(s)
    if len(s) <= width:
        return s
    if width <= 1:
        return s[:width]
    return s[: max(0, width - 1)] + ELLIPSIS

def extract_row(rec: Dict[str, Any]) -> List[str]:
    mp = rec.get("map_position") or {}
    map_x = mp.get("x") if isinstance(mp, dict) else None
    map_y = mp.get("y") if isinstance(mp, dict) else None

    row_map = {
        "name_hash_id": rec.get("name_hash_id") or "",
        "species": rec.get("species") or "",
        "species_confidence": rec.get("species_confidence") or "",
        "spawn_area_id": rec.get("spawn_area_id") or "",
        "need_zone_guids": rec.get("need_zone_guids") or [],
        "gender": rec.get("gender") or "",
        "weight_kg": rec.get("weight_kg") or "",
        "score": rec.get("score") or "",
        "visual_variation_seed": rec.get("visual_variation_seed") or "",
        "animal_id": rec.get("animal_id") or "",
        "map_x": map_x,
        "map_y": map_y,
    }

    out: List[str] = []
    for key, width in COLUMNS:
        val = row_map.get(key)
        if key == "need_zone_guids":
            out.append(fmt_list_field(val, width))
        elif key in ("weight_kg", "score", "map_x", "map_y"):
            out.append(fmt_number(val, width))
        else:
            out.append(truncate(val, width))
    return out

def build_separator(col_widths: List[int]) -> str:
    parts = ["+" + "-" * (w + 2) for w in col_widths]
    return "".join(parts) + "+\n"

def build_header(col_names: List[str], col_widths: List[int]) -> str:
    header_cells = []
    for name, w in zip(col_names, col_widths):
        header_cells.append(" " + name.center(w) + " ")
    return "|" + "|".join(header_cells) + "|\n"

def write_table(records: List[Dict[str, Any]], out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    col_names = [k for k, _ in COLUMNS]
    col_widths = [w for _, w in COLUMNS]

    sep = build_separator(col_widths)
    header = build_header(col_names, col_widths)

    with out_path.open("w", encoding="utf-8") as f:
        f.write(sep)
        f.write(header)
        f.write(sep)
        for rec in records:
            row = extract_row(rec)
            # format each cell to width and left-align (numbers right-align)
            cells = []
            for (col, width), cell in zip(COLUMNS, row):
                if col in ("weight_kg", "score", "map_x", "map_y", "spawn_area_id", "visual_variation_seed", "animal_id"):
                    cell_str = cell.rjust(width)
                else:
                    cell_str = cell.ljust(width)
                cells.append(" " + cell_str + " ")
            f.write("|" + "|".join(cells) + "|\n")
        f.write(sep)

def main():
    records = load_all_records(INPUT_DIR)
    if not records:
        print("No parsed JSON records found in", INPUT_DIR)
        return
    write_table(records, OUTPUT_FILE)
    print(f"Wrote {len(records)} rows to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
