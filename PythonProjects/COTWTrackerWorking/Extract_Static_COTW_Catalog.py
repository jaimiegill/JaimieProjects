"""Extract a static COTW reserve and animal catalog from the DECA index."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path


INDEX_ROOT = Path(os.environ.get("COTW_STATIC_INDEX", r"E:\COTWTrackerCache"))
CORE_DB = INDEX_ROOT / "db" / "core.db"
OUTPUT_FILE = INDEX_ROOT / "static_animal_catalog.json"

RESERVE_NAMES = {
    0: "Hirschfelden Hunting Reserve",
    1: "Layton Lake District",
    2: "Medved Taiga",
    3: "Vurhonga Savanna",
    4: "Parque Fernando",
    6: "Yukon Valley",
    8: "Cuatro Colinas Game Reserve",
    9: "Silver Ridge Peaks",
    10: "Te Awaroa National Park",
    11: "Rancho del Arroyo",
    12: "Mississippi Acres Preserve",
    13: "Revontuli Coast",
    14: "New England Mountains",
    16: "Emerald Coast",
    17: "Sundarpatan",
    18: "Salzwiesen Park",
    19: "Askiy Ridge Hunting Preserve",
    20: "Torr nan Sithean",
    21: "Intisuyu",
}

NAME_ALIASES = {
    "boar": "Wild Boar",
    "lynx": "Eurasian Lynx",
    "jackal": "Side-Striped Jackal",
    "peccary": "Collared Peccary",
    "puma": "Puma",
    "blacktail": "Blacktail Deer",
    "whitetail": "Whitetail Deer",
    "mule_deer": "Mule Deer",
    "mountain_goat": "Mountain Goat",
    "rockymountain_elk": "Rocky Mountain Elk",
    "plains_bison": "Plains Bison",
    "wild_yak": "Wild Yak",
    "blue_sheep": "Blue Sheep",
    "tahr": "Tahr",
    "alpine_goat": "Alpine Goat",
    "feral_pig": "Feral Pig",
    "feral_goat": "Feral Goat",
    "red_deer": "Red Deer",
    "reddeer": "Red Deer",
    "wildboar": "Wild Boar",
    "lesserkudu": "Lesser Kudu",
    "fallowdeer": "Fallow Deer",
    "sikadeer": "Sika Deer",
    "feralpig": "Feral Pig",
    "feralgoat": "Feral Goat",
    "whitetaildeer": "Whitetail Deer",
    "blacktaildeer": "Blacktail Deer",
    "muledeer": "Mule Deer",
    "roedeer": "Roe Deer",
    "rooseveltelk": "Roosevelt Elk",
    "rockymountainelk": "Rocky Mountain Elk",
    "mountaingoat": "Mountain Goat",
    "mountainlion": "Mountain Lion",
    "europeanrabbit": "European Rabbit",
    "europeanhare": "European Hare",
    "greylaggoose": "Greylag Goose",
    "canadagoose": "Canada Goose",
    "graywolf": "Gray Wolf",
    "redfox": "Red Fox",
    "blackbear": "Black Bear",
    "brownbear": "Brown Bear",
    "grizzlybear": "Grizzly Bear",
    "plainsbison": "Plains Bison",
    "capebuffalo": "Cape Buffalo",
    "waterbuffalo": "Water Buffalo",
    "eurasianlynx": "Eurasian Lynx",
    "siberianmuskdeer": "Siberian Musk Deer",
    "americanalligator": "American Alligator",
    "easterncottontailrabbit": "Eastern Cottontail Rabbit",
    "grayfox": "Gray Fox",
    "greenwingteal": "Green-winged Teal",
    "northernbobwhitequail": "Northern Bobwhite Quail",
    "mexicanbobcat": "Mexican Bobcat",
    "raccoondog": "Raccoon Dog",
    "pheasant": "Ring-Necked Pheasant",
    "gray_fox": "Gray Fox",
    "grey_fox": "Grey Fox",
    "eu_rabbit": "European Rabbit",
    "eu_wigeon": "Eurasian Wigeon",
    "eu_teal": "Eurasian Teal",
    "eu_lynx": "Eurasian Lynx",
    "wild_turkey": "Wild Turkey",
    "easternwildturkey": "Eastern Wild Turkey",
    "riograndeturkey": "Rio Grande Turkey",
    "magpiegoose": "Magpie Goose",
    "axisdeer": "Axis Deer",
    "easterngreykangaroo": "Eastern Grey Kangaroo",
    "hogdeer": "Hog Deer",
    "javanrusa": "Javan Rusa",
    "saltwatercrocodile": "Saltwater Crocodile",
    "stubblequail": "Stubble Quail",
    "easternwildturkey": "Eastern Wild Turkey",
    "easterngreyfox": "Grey Fox",
    "wildhog": "Wild Hog",
    "green_wing_teal": "Green-winged Teal",
    "rio_grande_turkey": "Rio Grande Turkey",
    "red_fox": "Red Fox",
    "blue_wildebeest": "Blue Wildebeest",
    "side_striped_jackal": "Side-Striped Jackal",
    "black_bear": "Black Bear",
    "gray_wolf": "Gray Wolf",
    "plains_bison": "Plains Bison",
    "water_buffalo": "Water Buffalo",
}


def key_to_species(key: str) -> str | None:
    if not key.startswith("animal_") or not key.endswith("_name"):
        return None
    raw_name = key[len("animal_"):-len("_name")]
    if not raw_name or "," in raw_name or " " in raw_name:
        return None
    return display_name(raw_name)


def display_name(raw_name: str) -> str:
    return NAME_ALIASES.get(
        raw_name,
        raw_name.replace("_", " ").title(),
    )


def main() -> int:
    if not CORE_DB.is_file():
        print(f"[ERROR] Static index database not found: {CORE_DB}", flush=True)
        return 1

    connection = sqlite3.connect(CORE_DB)
    try:
        paths = connection.execute(
            "SELECT DISTINCT v_path FROM core_nodes "
            "WHERE v_path LIKE 'settings/hp_settings/hp_ai_textures/"
            "spawn_maps/reserve_%_%.bmp_datac'"
        ).fetchall()
        name_hash_rows = connection.execute(
            "SELECT DISTINCT string, hash32 FROM core_strings "
            "WHERE string LIKE 'animal_%_name'"
        ).fetchall()
    finally:
        connection.close()

    animals_by_reserve: dict[str, list[dict[str, str]]] = {}
    pattern = re.compile(r"reserve_(\d+)_([^/]+)\.bmp_datac$")
    for (path_value,) in paths:
        match = pattern.search(path_value)
        if not match:
            continue
        reserve_id = int(match.group(1))
        raw_name = match.group(2)
        animals_by_reserve.setdefault(str(reserve_id), []).append(
            {
                "name": display_name(raw_name),
                "source_path": path_value,
            }
        )

    for animals in animals_by_reserve.values():
        animals.sort(key=lambda animal: animal["name"])

    animal_name_hashes = []
    for internal_key, hash32 in name_hash_rows:
        species = key_to_species(internal_key)
        if species is not None:
            animal_name_hashes.append(
                {
                    "species": species,
                    "internal_key": internal_key,
                    "hash32": int(hash32) & 0xFFFFFFFF,
                }
            )
    animal_name_hashes.sort(key=lambda item: (item["species"], item["hash32"]))

    catalog = {
        "source_database": str(CORE_DB),
        "reserve_count": len(animals_by_reserve),
        "animal_count": sum(len(animals) for animals in animals_by_reserve.values()),
        "animal_name_hash_count": len(animal_name_hashes),
        "animal_name_hashes": animal_name_hashes,
        "reserves": {
            reserve_id: {
                "name": RESERVE_NAMES.get(int(reserve_id), f"Reserve {reserve_id}"),
                "animals": animals,
            }
            for reserve_id, animals in sorted(animals_by_reserve.items(), key=lambda item: int(item[0]))
        },
    }
    OUTPUT_FILE.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(
        f"[OK] Static catalog created: {catalog['animal_count']} animal entries "
        f"across {catalog['reserve_count']} reserves -> {OUTPUT_FILE}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
