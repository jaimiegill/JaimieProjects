from collections import Counter
import io
import json
import os
from pathlib import Path
import re
import sys
import tkinter as tk
from tkinter import ttk
import urllib.request

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk,
)
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image, ImageDraw

from ADF_Reader import GLOBAL_SPECIES_PROFILES
from species_metadata import SPECIES_METADATA

# --- File Paths ---
ZONE_FILE = Path(r"C:\Users\gills\JaimieProjects\PythonProjects\COTWTrackerWorking\DecodedNeedZoneData\need_zones.csv")
ANIMAL_FILE = Path(r"C:\Users\gills\JaimieProjects\PythonProjects\COTWTrackerWorking\DecodedADFJSONFormat\all_animals.json")
SPECIES_HASH_REPORT = Path(r"C:\Users\gills\Results_readable\species_hash_report.json")
STATIC_ANIMAL_CATALOG = Path(
    os.environ.get("COTW_STATIC_INDEX", r"E:\COTWTrackerCache")
) / "static_animal_catalog.json"
MASTER_ZONE_FILE = Path(
    os.environ.get("COTW_STATIC_INDEX", r"E:\COTWTrackerCache")
) / "need_zone_master.csv"
MAP_CACHE_DIR = Path(r"C:\Users\gills\JaimieProjects\PythonProjects\COTWTrackerWorking\map_cache")
MAP_CACHE_DIR.mkdir(parents=True, exist_ok=True)

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
    20: "Tòrr nan Sithean",
    21: "Intisuyu",
}

RESERVE_SPECIES_NAMES = {
    0: {  # Hirschfelden Hunting Reserve
        0: "Red Deer",
        1: "Fallow Deer",
        2: "Roe Deer",
        3: "Wild Boar",
        4: "European Bison",
        5: "Red Fox",
    },

    1: {  # Layton Lake District
        0: "Roosevelt Elk",
        1: "Moose",
        2: "Grizzly Bear",
        3: "Blacktail Deer",
        4: "Whitetail Deer",
        5: "Coyote",
        6: "Mallard",
    },

    2: {  # Medved Taiga
        0: "Moose",
        1: "Reindeer",
        2: "Brown Bear",
        3: "Wild Boar",
        4: "Siberian Musk Deer",
        5: "Capercaillie",
        6: "Eurasian Lynx",
    },

    3: {  # Vurhonga Savanna
        0: "Scrub Hare",
        1: "Side-Striped Jackal",
        2: "Springbok",
        3: "Warthog",
        4: "Lesser Kudu",
        5: "Blue Wildebeest",
        6: "Gemsbok",
        7: "Cape Buffalo",
        8: "Lion",
    },

    4: {  # Parque Fernando (correct species)
        0: "Mule Deer",
        1: "Blackbuck",
        2: "Axis Deer",
        3: "Puma",
        4: "Water Buffalo",
        5: "Cinnamon Teal",
    },

    6: {  # Yukon Valley
        0: "Grizzly Bear",
        1: "Moose",
        2: "Caribou",
        3: "Gray Wolf",
        4: "Harlequin Duck",
        5: "Red Fox",
        6: "Plains Bison",
    },

    8: {  # Cuatro Colinas Game Reserve (correct species)
        0: "Red Deer",
        1: "Fallow Deer",
        2: "Roe Deer",
        3: "Wild Boar",
        4: "Red Fox",
        5: "European Rabbit",
        6: "Iberian Mouflon",
        7: "Ronda Ibex",
        8: "Beceite Ibex",
        9: "Gredos Ibex",
        10: "Southeastern Spanish Ibex",
        11: "Iberian Wolf",
    },

    9: {  # Silver Ridge Peaks
        0: "Elk",
        1: "Bighorn Sheep",
        2: "Mountain Goat",
        3: "Pronghorn",
        4: "Mule Deer",
        5: "White-tailed Jackrabbit",
        6: "Merriam's Turkey",
        7: "Black Bear",
        8: "Mountain Lion",
    },

    10: {  # Te Awaroa National Park (correct species)
        0: "Chamois",
        1: "Feral Goat",
        2: "Sika Deer",
        3: "Fallow Deer",
        4: "Red Deer",
        5: "Wild Boar",
        6: "Red Fox",
        7: "Turkey",
        8: "Canada Goose",
        9: "Mallard",
        10: "Paradise Shelduck",
        11: "Pukeko",
        12: "Weka",
        13: "Black Swan",
    },

    11: {  # Rancho del Arroyo (correct species)
        0: "Mule Deer",
        1: "Whitetail Deer",
        2: "Bighorn Sheep",
        3: "Collared Peccary",
        4: "Mexican Bobcat",
        5: "Rio Grande Turkey",
        6: "Cinnamon Teal",
        7: "Blackbuck",
        8: "Axis Deer",
    },

    12: {  # Mississippi Acres Preserve
        0: "Whitetail Deer",
        1: "Wild Turkey",
        2: "Bobwhite Quail",
        3: "Eastern Cottontail",
        4: "Common Raccoon",
        5: "Gray Fox",
        6: "Wild Hog",
        7: "American Alligator",
        8: "Black Bear",
        9: "Bobcat",
    },

    13: {  # Revontuli Coast (correct species)
        0: "Eurasian Wigeon",
        1: "Eurasian Teal",
        2: "Black Grouse",
        3: "Goldeneye",
        4: "Hazel Grouse",
        5: "Mallard",
        6: "Western Capercaillie",
        7: "Tufted Duck",
        8: "Rock Ptarmigan",
        9: "Canada Goose",
        10: "Willow Ptarmigan",
        11: "Tundra Bean Goose",
        12: "Mountain Hare",
        13: "Greylag Goose",
        14: "Raccoon Dog",
        15: "Eurasian Lynx",
        16: "Whitetail Deer",
        17: "Eurasian Brown Bear",
        18: "Moose",
    },

    14: {  # New England Mountains
        0: "Whitetail Deer",
        1: "Moose",
        2: "Black Bear",
        3: "Bobcat",
        4: "Coyote",
        5: "Red Fox",
        6: "Eastern Wild Turkey",
        7: "Green Wing Teal",
        8: "Canada Goose",
    },

    16: {  # Emerald Coast
        0: "Magpie Goose",
        1: "Stubble Quail",
        2: "Red Fox",
        3: "Hog Deer",
        4: "Axis Deer",
        5: "Feral Goat",
        6: "Eastern Grey Kangaroo",
        7: "Fallow Deer",
        8: "Feral Pig",
        9: "Red Deer",
        10: "Sambar Deer",
        11: "Javan Rusa",
        12: "Saltwater Crocodile",
        13: "Banteng",
    },

    17: {},  # Sundarpatan (not released yet)

    18: {},  # Salzwiesen Park (not released yet)

    19: {},  # Askiy Ridge Hunting Preserve (not released yet)

    20: {},  # Tòrr nan Sithean (not released yet)

    21: {},  # Intisuyu (not released yet)
}

# Hash-style AnimalTypeLocalizationName values used by need-zone data.
# These are separate from the reserve-local species indexes above.
ANIMAL_TYPE_HASH_NAMES = {
    0xFAADE638: "Moose",
    2119612362: "Banteng",
}

VERIFIED_HASH_SPECIES_OVERRIDES = {
    0x61D18658: "Warthog",
    0xB79E88B2: "Warthog",
    0x862B4FB0: "Blue Wildebeest",
    0x82770585: "Blue Wildebeest",
    0x92411D2A: "Scrub Hare",
    0x0520122F: "Scrub Hare",
    0x62F546BD: "Blue Wildebeest",
    0x0AF54EC2: "Blue Wildebeest",
    0x57703ADF: "Side-Striped Jackal",
    0x2FDCAF40: "Side-Striped Jackal",
}

RESERVE_HASH_SPECIES_OVERRIDES = {
    # Parque Fernando reuses hashes that the global report associates with
    # species from other reserves.
    4: {
        0xCB0DA701: "Axis Deer",
        0x68B2DEB2: "Cinnamon Teal",
        0x2C52E985: "Water Buffalo",
        0x671D4603: "Puma",
    },
    8: {
        0xA2E717D8: "Ring-Necked Pheasant",
        0xC5D0C033: "Ring-Necked Pheasant",
        0xE4746DB6: "Beceite Ibex",
        0x6E5A275A: "Beceite Ibex",
    },
    10: {
        0x4A0A4E9F: "Wild Turkey",
        0x81E18062: "Wild Turkey",
        0x80818794: "Feral Goat",
        0xC1784891: "Feral Goat",
        0x828D37E0: "Fallow Deer",
        0x2F9AC7B7: "Fallow Deer",
        0xD19E69E0: "Feral Pig",
        0x2D774864: "Feral Pig",
        0xE5BE7394: "Sika Deer",
        0xBA6F80F5: "Sika Deer",
        0x26FA9F96: "Red Deer",
        0x1998199C: "Red Deer",
    },
    12: {
        # The save links these green-winged teal records to an alligator zone.
        0xCCA8FDF2: "Green-winged Teal",
        0xBAF2D3A2: "American Alligator",
    },
    14: {
        0x6B7BBB47: "Eastern Wild Turkey",
        0x0F0E0C0D: "Goldeneye",
    },
    16: {
        0x78A83A54: "Magpie Goose",
        0x5A6BDC6E: "Magpie Goose",
        0x46DAB4DE: "Hog Deer",
        0x68A2CA: "Hog Deer",
        0x99155DEF: "Eastern Grey Kangaroo",
        0x739A4F18: "Eastern Grey Kangaroo",
        0xD19E69E0: "Feral Pig",
        0xED7CE362: "Sambar",
        0x8FF3825F: "Sambar",
        0xA2CBC896: "Saltwater Crocodile",
        0xBA302E00: "Saltwater Crocodile",
        0x7E56B7CA: "Banteng",
        0xA46DF63D: "Banteng",
        0x8527AFD1: "Red Fox",
        0xF08293A6: "Red Fox",
    },
    6: {
        0xD0B0397E: "Moose",
        0xA58D7467: "Caribou",
        0xD9CA14CA: "Plains Bison",
        0x8527AFD1: "Red Fox",
    },
}

RESERVE_STATIC_NAME_HASHES = {}

# Trophy-rating ranges from the COTW Rating table.  They are used together
# with weight ranges to identify otherwise unknown animal type hashes.
TROPHY_RATING_RANGES = {
    "Canada Goose": (3.2, 9.4),
    "Mallard": (0.7, 2.1),
    "Scrub Hare": (1.5, 5.9),
    "White-tailed Jackrabbit": (1.9, 7.0),
    "Side-Striped Jackal": (13.2, 32.3),
    "Red Fox": (2.0, 15.6),
    "Eurasian Lynx": (16.0, 30.7),
    "Coyote": (33.0, 63.1),
    "European Rabbit": (2.0, 7.2),
    "Harlequin Duck": (0.0, 8.0),
    "Cinnamon Teal": (0.0, 5.1),
    "Siberian Musk Deer": (0.0, 276.7),
    "Roe Deer": (0.0, 99.2),
    "Springbok": (57.0, 122.9),
    "Fallow Deer": (0.0, 279.7),
    "Blacktail Deer": (0.0, 197.2),
    "Whitetail Deer": (0.0, 283.3),
    "Javan Rusa": (0.0, 160.0),
    "Sambar Deer": (0.0, 180.0),
    "Sambar": (0.0, 180.0),
    "Red Deer": (0.0, 278.9),
    "Blue Wildebeest": (17.0, 41.8),
    "Roosevelt Elk": (0.0, 423.1),
    "Moose": (0.0, 305.4),
    "Reindeer": (65.0, 478.0),
    "Mountain Reindeer": (65.0, 478.0),
    "Grant Caribou": (0.0, 478.0),
    "Caribou": (0.0, 478.0),
    "Mule Deer": (0.0, 349.8),
    "Axis Deer": (0.0, 241.3),
    "Lesser Kudu": (0.0, 35.8),
    "Warthog": (15.0, 64.6),
    "Wild Boar": (7.0, 160.2),
    "Black Bear": (12.0, 25.2),
    "Brown Bear": (16.0, 30.8),
    "Grizzly Bear": (0.0, 74.3),
    "Puma": (30.0, 43.3),
    "Mountain Lion": (30.0, 43.3),
    "Lion": (35.0, 53.9),
    "Gray Wolf": (0.0, 43.3),
    "Iberian Wolf": (30.0, 43.3),
    "European Bison": (4.0, 300.3),
    "Plains Bison": (0.0, 245.7),
    "Cape Buffalo": (51.0, 168.1),
    "Water Buffalo": (154.0, 186.1),
    "Blackbuck": (17.5, 146.9),
    "Iberian Mouflon": (0.0, 199.4),
    "Gredos Ibex": (0.0, 112.1),
    "Beceite Ibex": (0.0, 212.9),
    "Ronda Ibex": (0.0, 119.9),
    "Southeastern Spanish Ibex": (0.0, 99.6),
    "Eastern Grey Kangaroo": (0.0, 530.0),
    "Saltwater Crocodile": (0.0, 168.1),
}

SPECIES_MAX_DIFFICULTY = {
    # Regular difficulty maximums. Great Ones are represented separately as 10.
    "Mallard": 3, "Teal": 3, "Cinnamon Teal": 3,
    "Scrub Hare": 3, "European Rabbit": 3,
    "Siberian Musk Deer": 3, "Roe Deer": 3,
    "Turkey": 3, "Wild Turkey": 3, "Eastern Wild Turkey": 3,
    "Rio Grande Turkey": 3, "Merriam's Turkey": 3,
    "Canada Goose": 3, "Greylag Goose": 3,
    "Harlequin Duck": 3, "Pheasant": 3, "Ring-Necked Pheasant": 3,
    "White-tailed Jackrabbit": 3, "Mountain Hare": 3,
    "Coyote": 5, "Red Fox": 5, "Side-Striped Jackal": 5,
    "European Hare": 5, "Blackbuck": 5, "Springbok": 5,
    "Lesser Kudu": 5, "Warthog": 5, "Blue Wildebeest": 5,
    "Mountain Goat": 5, "Pronghorn": 5, "Iberian Mouflon": 5,
    "Beceite Ibex": 5, "Ronda Ibex": 5, "Gredos Ibex": 5,
    "Southeastern Spanish Ibex": 5, "Feral Goat": 5,
    "Feral Pig": 5, "Wild Boar": 5, "Collared Peccary": 5,
    "Blacktail Deer": 5, "Whitetail Deer": 3, "Fallow Deer": 5,
    "Axis Deer": 5, "Javan Rusa": 5, "Sambar": 5, "Sambar Deer": 5,
    "Chamois": 5, "Hog Deer": 5, "Roe Deer": 3,
    "Eurasian Lynx": 9, "Puma": 9, "Mountain Lion": 9,
    "Black Bear": 9, "Brown Bear": 9, "Grizzly Bear": 9,
    "Gray Wolf": 9, "Iberian Wolf": 9, "Lion": 9,
    "Red Deer": 9, "Roosevelt Elk": 9, "Moose": 5,
    "European Bison": 9, "Plains Bison": 9, "Cape Buffalo": 9,
    "Water Buffalo": 9, "Saltwater Crocodile": 9,
}

GREAT_ONE_SPECIES = {
    "Whitetail Deer", "Red Deer", "Black Bear", "Fallow Deer",
    "Moose", "Red Fox", "Ring-Necked Pheasant",
}

DIFFICULTY_NAMES = {
    1: "Trivial",
    2: "Minor",
    3: "Very Easy",
    4: "Easy",
    5: "Medium",
    6: "Hard",
    7: "Very Hard",
    8: "Mythical",
    9: "Legendary",
    10: "Fabled",
}

SPECIES_ALIASES = {
    "Elk": "Rocky Mountain Elk",
    "Mountain Goat": "Mountain Goat",
    "Merriam's Turkey": "Merriam Turkey",
    "White-tailed Jackrabbit": "White-tailed Jackrabbit",
}

# Verified reserve/need-type corrections for AnimalTypeLocalizationName data.
RESERVE_NEED_SPECIES_OVERRIDES = {
    10: {2: "Red Deer"},
    16: {3: "Saltwater Crocodile"},
}



RESERVE_BOUNDS = {
    0: {"X_MIN": 0, "X_MAX": -16400, "Z_MIN": 16400, "Z_MAX": 0},
    1: {"X_MIN": 16400, "X_MAX": 0, "Z_MIN": 16400, "Z_MAX": 0},
    2: {"X_MIN": 0, "X_MAX": -16400, "Z_MIN": 0, "Z_MAX": -16400},
    3: {"X_MIN": 16400, "X_MAX": 0, "Z_MIN": 0, "Z_MAX": -16400},
    4: {"X_MIN": -16400, "X_MAX": 0, "Z_MIN": 16400, "Z_MAX": 0},
    6: {"X_MIN": -16400, "X_MAX": 0, "Z_MIN": 0, "Z_MAX": -16400},
    8: {"X_MIN": -16400, "X_MAX": 0, "Z_MIN": 16400, "Z_MAX": 0},
    9: {"X_MIN": -12980, "X_MAX": -0, "Z_MIN": -772, "Z_MAX": -17156},
    10: {"X_MIN": 0, "X_MAX": 16400, "Z_MIN": 16400, "Z_MAX": 0},
    11: {"X_MIN": -16400, "X_MAX": 0, "Z_MIN": 16400, "Z_MAX": 0},
    12: {"X_MIN": 0, "X_MAX": 16400, "Z_MIN": 16400, "Z_MAX": 0},
    13: {"X_MIN": -16400, "X_MAX": 0, "Z_MIN": 16400, "Z_MAX": 0},
    14: {"X_MIN": 0, "X_MAX": 16400, "Z_MIN": 16400, "Z_MAX": 0},
    16: {"X_MIN": -16400, "X_MAX": 0, "Z_MIN": 0, "Z_MAX": -16400},
}

NEED_TYPES = {
    1: {"name": "Feed", "color": "#2ca02c", "marker": "o"},
    2: {"name": "Drink", "color": "#1f77b4", "marker": "^"},
    3: {"name": "Rest", "color": "#ff7f0e", "marker": "s"},
}


def generate_fallback_grid(width=1024, height=1024):
    img = Image.new("RGB", (width, height), color=(40, 50, 60))
    draw = ImageDraw.Draw(img)
    step = 64
    for x in range(0, width, step):
        draw.line([(x, 0), (x, height)], fill=(60, 75, 90), width=1)
    for y in range(0, height, step):
        draw.line([(0, y), (width, y)], fill=(60, 75, 90), width=1)

    draw.text(
        (20, 20),
        "Map tiles unavailable — Using placeholder grid",
        fill=(220, 220, 220),
    )
    return img


def get_map_image(reserve_id):
    cached_file = MAP_CACHE_DIR / f"reserve_{reserve_id}_full.png"
    if cached_file.exists():
        try:
            return Image.open(cached_file)
        except Exception:
            pass

    local_file = (
        Path(r"C:\Users\gills\Results_need_zones\maps")
        / f"reserve_{reserve_id}.png"
    )
    if local_file.exists():
        try:
            return Image.open(local_file)
        except Exception:
            pass

    url = f"https://mathartbang.com/deca/hp/data/r{reserve_id}/t_topo/full.png"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            image_bytes = resp.read()
            img = Image.open(io.BytesIO(image_bytes))
            img.save(cached_file)
            return img
    except Exception as e:
        print(
            f"Notice: Could not fetch map for Reserve {reserve_id} from {url} ({e})"
        )

    return generate_fallback_grid()


def _range_score(value, bounds):
    if value is None or bounds is None:
        return None
    low, high = bounds
    if low <= value <= high:
        return 1.0
    width = max(high - low, 1.0)
    distance = low - value if value < low else value - high
    return max(0.0, 1.0 - (distance / width))


def estimate_trophy_status(
    species,
    trophy_value,
    weight_value,
    reserve_id=None,
    is_great_one=False,
):
    """Estimate species-capped difficulty level and medal from trophy value."""
    try:
        trophy_value = float(trophy_value) if trophy_value is not None else None
        weight_value = float(weight_value) if weight_value is not None else None
    except (TypeError, ValueError):
        return "Unknown", "No"

    metadata = SPECIES_METADATA.get(int(reserve_id), {}).get(species, {})
    trophy_range = TROPHY_RATING_RANGES.get(species)
    diamond_min = metadata.get("diamond_min")
    if diamond_min is None and trophy_range is not None:
        diamond_min = trophy_range[1] * 0.90
    if diamond_min is None:
        return "Unknown", "No"

    maximum = trophy_range[1] if trophy_range else diamond_min
    # Class-1 save scores are stored as grams, so weight is the useful signal.
    if trophy_value is not None and trophy_value > maximum * 3:
        ratio = (trophy_value / 1000.0) / max(maximum, 1.0)
    elif trophy_value is not None:
        ratio = trophy_value / max(maximum, 1.0)
    else:
        return "Unknown", "No"

    max_level = metadata.get(
        "max_level",
        SPECIES_MAX_DIFFICULTY.get(species, 9),
    )
    if is_great_one and metadata.get("great_one", False):
        return "10 (Fabled)", "No"
    estimated_level = max(
        1,
        min(max_level, int((trophy_value or 0) / max(diamond_min, 1) * max_level)),
    )
    if trophy_value is not None and trophy_value >= diamond_min:
        medal = "Diamond"
        diamond = "Yes"
    elif trophy_value is not None and trophy_value >= diamond_min * 0.667:
        medal = "Gold"
        diamond = "No"
    elif trophy_value is not None and trophy_value >= diamond_min * 0.333:
        medal = "Silver"
        diamond = "No"
    else:
        medal = "Bronze"
        diamond = "No"

    difficulty_name = DIFFICULTY_NAMES[estimated_level]
    return f"{estimated_level} ({difficulty_name}; max {max_level})", diamond


def apex_seed_to_float(seed):
    seed = int(seed) & 0xFFFFFFFF
    state = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
    return (state >> 8) / 16777216.0


def fur_type_from_record(record):
    """Resolve explicit fur fields, then apply the generic COTW rare seed bands."""
    for key, value in record.items():
        if "fur" not in str(key).lower() and "variation" not in str(key).lower():
            continue
        text = str(value).lower()
        if any(term in text for term in ("albino", "melanistic", "leucistic")):
            return str(value)
        if "piebald" in text:
            return str(value)

    seed = record.get("visual_variation_seed")
    if seed is None:
        seed = record.get("VisualVariationSeed")
    if seed is None:
        return "Unknown"
    try:
        normalized = apex_seed_to_float(seed)
    except (TypeError, ValueError, OverflowError):
        return "Unknown"
    if normalized >= 0.9997:
        return "Melanistic (V.Rare)"
    if normalized >= 0.9992:
        return "Albino (V.Rare)"
    if normalized >= 0.9980:
        return "Piebald (Rare)"
    return "Common/Unresolved"


def rare_fur_status(record):
    """Return a seed-backed rare-fur result for any species."""
    fur_type = fur_type_from_record(record)
    if "Rare" in fur_type or "Albino" in fur_type or "Melanistic" in fur_type:
        return fur_type
    if fur_type == "Common/Unresolved":
        return "No"
    return fur_type


def infer_species_from_attributes(matches, reserve_id):
    """Choose the reserve species best supported by linked weight/TR data."""
    candidates = list(RESERVE_SPECIES_NAMES.get(int(reserve_id), {}).values())
    if not candidates:
        candidates = list(GLOBAL_SPECIES_PROFILES)

    observations = []
    for rec in matches:
        weight = (
            rec.get("weight_kg") or rec.get("weight") or rec.get("Weight")
            or rec.get("body_weight")
        )
        rating = (
            rec.get("score") or rec.get("trophy_score")
            or rec.get("TrophyScore") or rec.get("Score")
        )
        try:
            observations.append((
                float(weight) if weight is not None else None,
                float(rating) if rating is not None else None,
            ))
        except (TypeError, ValueError):
            continue

    if not observations:
        return None

    ranked = []
    for species in candidates:
        profile_name = SPECIES_ALIASES.get(species, species)
        weight_profile = GLOBAL_SPECIES_PROFILES.get(profile_name)
        trophy_range = TROPHY_RATING_RANGES.get(species)
        if trophy_range is None:
            trophy_range = TROPHY_RATING_RANGES.get(profile_name)
        scores = []
        for weight, rating in observations:
            weight_score = _range_score(
                weight,
                (weight_profile["min_w"], weight_profile["max_w"])
                if weight_profile else None,
            )
            trophy_score = _range_score(rating, trophy_range)
            available = [value for value in (weight_score, trophy_score)
                         if value is not None]
            if available:
                scores.append(sum(available) / len(available))
        if scores:
            ranked.append((sum(scores) / len(scores), species))

    if not ranked:
        return None
    ranked.sort(reverse=True)
    best_score, best_species = ranked[0]
    second_score = ranked[1][0] if len(ranked) > 1 else 0.0
    if best_score < 0.55 or best_score - second_score < 0.05:
        return None
    return best_species


def resolve_zone_species(row, matches, reserve_id):
    """Translate the selected need zone's reserve-local species ID."""
    allowed_species = set(RESERVE_SPECIES_NAMES.get(int(reserve_id), {}).values())
    reserve_hashes = RESERVE_HASH_SPECIES_OVERRIDES.get(int(reserve_id), {})
    static_hashes = RESERVE_STATIC_NAME_HASHES.get(int(reserve_id), {})
    for rec in matches:
        record_hash = canonical_uint32(
            rec.get("name_hash_id") or rec.get("NameHashId")
        )
        if record_hash in reserve_hashes:
            return reserve_hashes[record_hash]
        if record_hash in static_hashes:
            return static_hashes[record_hash]

    need_type = canonical_uint32(row.get("NeedType"))
    override = RESERVE_NEED_SPECIES_OVERRIDES.get(int(reserve_id), {}).get(
        need_type
    )
    if override:
        animal_type_id = canonical_uint32(row.get("AnimalTypeLocalizationName"))
        if animal_type_id is not None:
            ANIMAL_TYPE_HASH_NAMES[animal_type_id] = override
        return override

    species_name = None
    animal_type_id = None

    # 1. Try resolving via CSV AnimalTypeLocalizationName hash
    animal_type = row.get("AnimalTypeLocalizationName")
    if animal_type is not None and pd.notna(animal_type):
        animal_type_id = canonical_uint32(animal_type)
        if animal_type_id is not None:
            resolved = reserve_hashes.get(animal_type_id)
            if resolved:
                return resolved
            resolved = static_hashes.get(animal_type_id)
            if resolved:
                return resolved
            resolved = ANIMAL_TYPE_HASH_NAMES.get(animal_type_id)
            if resolved and (not allowed_species or resolved in allowed_species):
                return resolved

            reserve_types = RESERVE_SPECIES_NAMES.get(int(reserve_id), {})
            resolved = reserve_types.get(animal_type_id)
            if resolved and not resolved.startswith("Animal Type"):
                species_name = resolved

            # Some reserves store this field as the animal name hash rather
            # than the reserve-local species index. Match that hash against
            # the linked animal records before showing the raw ID.
            if not species_name:
                hash_species = []
                for rec in matches:
                    record_hash = canonical_uint32(
                        rec.get("name_hash_id") or rec.get("NameHashId")
                    )
                    record_species = rec.get("species") or rec.get("species_name")
                    if record_hash == animal_type_id and record_species:
                        hash_species.append(str(record_species))
                if hash_species:
                    species_name = Counter(hash_species).most_common(1)[0][0]

    # 2. Fall back to linked animal records (matches) if CSV lookup fails
    if not species_name and matches:
        hash_species = []
        for rec in matches:
            record_hash = canonical_uint32(
                rec.get("name_hash_id") or rec.get("NameHashId")
            )
            resolved = ANIMAL_TYPE_HASH_NAMES.get(record_hash)
            if resolved and (not allowed_species or resolved in allowed_species):
                hash_species.append(resolved)
        if hash_species:
            species_name = Counter(hash_species).most_common(1)[0][0]

    if not species_name and matches:
        species_list = []
        for rec in matches:
            sp = (
                rec.get("species")
                or rec.get("species_name")
                or rec.get("name")
                or rec.get("animal_type")
            )
            if sp and not str(sp).startswith("Animal Type"):
                species_list.append(str(sp))
        if species_list:
            species_name = Counter(species_list).most_common(1)[0][0]

    # 3. Infer the species from linked weight and trophy-rating attributes.
    if not species_name and matches:
        species_name = infer_species_from_attributes(matches, reserve_id)

    # Cache only a resolution supported by the linked animal attributes.
    if species_name and animal_type_id is not None:
        ANIMAL_TYPE_HASH_NAMES[animal_type_id] = species_name

    # 4. Final fallback
    if not species_name:
        return "Unknown Species"

    return species_name


def extract_animals_from_json(data, default_reserve_id=None):
    """Recursively traverses JSON nodes to extract animal records and propagate

    group/herd level Need Zone IDs and Reserve IDs down to individual animals.
    """
    extracted = []

    def parse_node(node, parent_zones=None, parent_reserve=None):
        if parent_zones is None:
            parent_zones = []

        if isinstance(node, dict):
            node_res = (
                node.get("reserve_id")
                if node.get("reserve_id") is not None
                else node.get("reserve")
                if node.get("reserve") is not None
                else node.get("ReserveId")
            )
            try:
                current_res = (
                    int(node_res) if node_res is not None else parent_reserve
                )
            except (ValueError, TypeError):
                current_res = parent_reserve

            if current_res is None:
                current_res = default_reserve_id

            node_zones = []
            for zkey in [
                "need_zone_guids",
                "need_zones",
                "need_zone_ids",
                "NeedZoneIds",
                "need_zone_id",
                "need_zone",
                "zone_id",
                "zone_guids",
                "zones",
            ]:
                if zkey in node and node[zkey] is not None:
                    val = node[zkey]
                    if isinstance(val, (int, float)):
                        node_zones.append(val)
                    elif isinstance(val, str):
                        # Handle semicolon-separated strings or single numeric strings
                        parts = val.split(";") if ";" in val else [val]
                        for p in parts:
                            if p.strip():
                                node_zones.append(p.strip())
                    elif isinstance(val, list):
                        for item in val:
                            if isinstance(item, str) and ";" in item:
                                node_zones.extend(
                                    [p.strip() for p in item.split(";") if p.strip()]
                                )
                            else:
                                node_zones.append(item)

            combined_zones = list(set(parent_zones + node_zones))

            # Identify if this node represents an individual animal
            is_animal = any(
                k in node
                for k in [
                    "gender",
                    "gender_name",
                    "weight",
                    "weight_kg",
                    "body_weight",
                    "score",
                    "trophy_score",
                    "trophy_rating",
                ]
            )

            if is_animal:
                animal_rec = dict(node)
                animal_rec["_extracted_zones"] = combined_zones
                animal_rec["_reserve_id"] = current_res
                extracted.append(animal_rec)

            # Recurse into child groups / lists / dicts
            for k, v in node.items():
                if k in ["_extracted_zones", "_reserve_id"]:
                    continue
                if isinstance(v, (dict, list)):
                    parse_node(
                        v,
                        parent_zones=combined_zones,
                        parent_reserve=current_res,
                    )

        elif isinstance(node, list):
            for item in node:
                parse_node(
                    item, parent_zones=parent_zones, parent_reserve=parent_reserve
                )

    parse_node(data, parent_reserve=default_reserve_id)
    return extracted


class NeedZoneApp:

    def __init__(self, root, df, animal_lookup):
        self.root = root
        self.root.title("COTW Need Zone Viewer")
        self.root.geometry("1280x850")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.df = df
        self.animal_lookup = animal_lookup

        # Top Control Bar
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(
            control_frame, text="Select Reserve:", font=("Arial", 11, "bold")
        ).pack(side=tk.LEFT, padx=(0, 10))

        unique_rids = sorted(self.df["ReserveId"].unique().tolist())
        self.reserve_map = {
            RESERVE_NAMES.get(rid, f"Reserve {rid}"): rid for rid in unique_rids
        }

        self.dropdown = ttk.Combobox(
            control_frame,
            values=list(self.reserve_map.keys()),
            state="readonly",
            width=30,
        )
        self.dropdown.pack(side=tk.LEFT)
        self.dropdown.bind("<<ComboboxSelected>>", self.on_reserve_change)

        default_name = RESERVE_NAMES.get(2, "Medved Taiga")
        if default_name in self.reserve_map:
            self.dropdown.set(default_name)
        elif unique_rids:
            self.dropdown.current(0)

        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=3)

        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=left_frame)

        self.toolbar = NavigationToolbar2Tk(self.canvas, left_frame)
        self.toolbar.update()
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas.get_tk_widget().pack(
            side=tk.TOP, fill=tk.BOTH, expand=True
        )

        right_frame = ttk.LabelFrame(
            paned, text=" Zone Details ", padding=(10, 10)
        )
        paned.add(right_frame, weight=1)

        self.lbl_zone_info = ttk.Label(
            right_frame,
            text="Click a zone marker on the map to inspect.",
            font=("Arial", 10, "italic"),
        )
        self.lbl_zone_info.pack(side=tk.TOP, anchor="w", pady=(0, 5))

        self.lbl_pos_info = ttk.Label(
            right_frame, text="", font=("Consolas", 9)
        )
        self.lbl_pos_info.pack(side=tk.TOP, anchor="w", pady=(0, 10))

        self.lbl_zone_status = ttk.Label(
            right_frame, text="", font=("Arial", 9, "bold")
        )
        self.lbl_zone_status.pack(side=tk.TOP, anchor="w", pady=(0, 10))

        tree_frame = ttk.Frame(right_frame)
        tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        columns = ("species", "gender", "score", "weight", "level", "diamond", "rare")
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", selectmode="browse"
        )
        self.tree.heading("species", text="Species")
        self.tree.heading("gender", text="Gender")
        self.tree.heading("score", text="Score")
        self.tree.heading("weight", text="Weight (kg)")
        self.tree.heading("level", text="Level")
        self.tree.heading("diamond", text="Diamond")
        self.tree.heading("rare", text="Fur type")

        self.tree.column("species", width=120, anchor="w")
        self.tree.column("gender", width=60, anchor="center")
        self.tree.column("score", width=60, anchor="e")
        self.tree.column("weight", width=80, anchor="e")
        self.tree.column("level", width=105, anchor="center")
        self.tree.column("diamond", width=65, anchor="center")
        self.tree.column("rare", width=75, anchor="center")

        tree_scroll = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.scatter_collections = []
        self.scatter_data_map = {}

        self.canvas.mpl_connect("button_press_event", self.on_click)
        self.update_plot()

    def on_reserve_change(self, event):
        self.update_plot()

    def update_plot(self):
        self.ax.clear()
        self.scatter_collections.clear()
        self.scatter_data_map.clear()

        self.lbl_zone_info.config(
            text="Click a zone marker on the map to inspect.",
            font=("Arial", 10, "italic"),
        )
        self.lbl_pos_info.config(text="")
        for item in self.tree.get_children():
            self.tree.delete(item)

        selected_label = self.dropdown.get()
        rid = self.reserve_map.get(selected_label)
        if rid is None:
            return

        sub_df = self.df[self.df["ReserveId"] == rid].copy()
        if sub_df.empty:
            self.canvas.draw()
            return

        if rid in RESERVE_BOUNDS:
            bounds = RESERVE_BOUNDS[rid]
            min_x, max_x = bounds["X_MIN"], bounds["X_MAX"]
            min_z, max_z = bounds["Z_MIN"], bounds["Z_MAX"]
        else:
            padding = 500
            min_x = sub_df["Position_X"].min() - padding
            max_x = sub_df["Position_X"].max() + padding
            min_z = sub_df["Position_Z"].min() - padding
            max_z = sub_df["Position_Z"].max() + padding

        left, right = min(min_x, max_x), max(min_x, max_x)
        bottom, top = min(min_z, max_z), max(min_z, max_z)

        center_z = (bottom + top) / 2.0
        sub_df["Plot_X"] = sub_df["Position_X"]
        sub_df["Plot_Z"] = 2 * center_z - sub_df["Position_Z"]

        bg_img = get_map_image(rid)
        if bg_img is not None:
            self.ax.imshow(
                bg_img,
                extent=[left, right, bottom, top],
                origin="upper",
                aspect="equal",
                zorder=0,
            )

        for need_type, meta in NEED_TYPES.items():
            type_df = sub_df[sub_df["NeedType"] == need_type]
            if type_df.empty:
                continue

            sc = self.ax.scatter(
                type_df["Plot_X"],
                type_df["Plot_Z"],
                c=meta["color"],
                marker=meta["marker"],
                label=f"{meta['name']} Zone",
                alpha=0.85,
                s=45,
                edgecolors="black",
                linewidths=0.6,
                zorder=2,
                picker=5,
            )
            self.scatter_collections.append(sc)
            self.scatter_data_map[sc] = type_df.to_dict("records")

        self.ax.set_xlim(left, right)
        self.ax.set_ylim(bottom, top)

        if max_z > 0:
            self.ax.invert_yaxis()

        self.ax.set_title(
            f"Need Zones — {selected_label} (n={len(sub_df)})",
            fontsize=12,
            fontweight="bold",
        )
        self.ax.set_xlabel("Position X (m)", fontsize=9)
        self.ax.set_ylabel("Position Z (m)", fontsize=9)

        self.ax.set_aspect("equal", adjustable="box")
        self.ax.grid(True, linestyle="--", alpha=0.3, zorder=1)
        self.ax.legend(loc="upper right")

        self.canvas.draw()

    def display_zone_details(self, row):
        reserve_id = int(row["ReserveId"])
        zone_id = int(row["NeedZoneId"])
        need_type_id = int(row["NeedType"])
        type_name = NEED_TYPES.get(need_type_id, {}).get("name", "Unknown")

        matches = self.animal_lookup.get(
            (canonical_uint32(reserve_id), canonical_uint32(zone_id)), []
        )

        zone_species = resolve_zone_species(row, matches, reserve_id)

        species_matches = []
        for rec in matches:
            record_species = resolve_zone_species(
                {"AnimalTypeLocalizationName": rec.get("name_hash_id")},
                [rec],
                reserve_id,
            )
            if record_species == zone_species:
                species_matches.append(rec)
        if species_matches:
            matches = species_matches

        self.lbl_zone_info.config(
            text=f"Zone ID: {zone_id} ({zone_species} {type_name})",
            font=("Arial", 11, "bold"),
        )
        self.lbl_pos_info.config(
            text=f"X: {row['Position_X']:.1f} | Z: {row['Position_Z']:.1f}\n"
            f"Animals linked: {len(matches)}"
        )

        zone_status = ["Diamond present: No", "Rare fur: Unknown"]
        self.lbl_zone_status.config(text=" | ".join(zone_status))

        for item in self.tree.get_children():
            self.tree.delete(item)

        for rec in matches:
            record_species = resolve_zone_species(
                {"AnimalTypeLocalizationName": rec.get("name_hash_id")},
                [rec],
                reserve_id,
            )
            gender = rec.get("gender") or rec.get("gender_name") or "N/A"

            trophy_val = (
                rec.get("score")
                or rec.get("trophy_score")
                or rec.get("trophy_rating")
            )
            trophy_str = (
                f"{float(trophy_val):.2f}" if trophy_val is not None else "N/A"
            )

            weight_val = (
                rec.get("weight_kg")
                or rec.get("weight")
                or rec.get("body_weight")
            )
            weight_str = (
                f"{float(weight_val):.1f}" if weight_val is not None else "N/A"
            )
            level_str, diamond_str = estimate_trophy_status(
                record_species,
                trophy_val,
                weight_val,
                reserve_id=reserve_id,
                is_great_one=bool(
                    rec.get("is_great_one")
                    or rec.get("IsGreatOne")
                    or rec.get("is_fabled")
                    or rec.get("IsFabled")
                ),
            )
            rare_str = rare_fur_status(rec)
            if diamond_str == "Yes":
                zone_status[0] = "Diamond present: Yes"
            if "Rare" in rare_str or "Albino" in rare_str or "Melanistic" in rare_str:
                zone_status[1] = f"Rare fur: {rare_str}"

            self.tree.insert(
                "",
                tk.END,
                values=(
                    record_species,
                    gender,
                    trophy_str,
                    weight_str,
                    level_str,
                    diamond_str,
                    rare_str,
                ),
            )

        self.lbl_zone_status.config(text=" | ".join(zone_status))

    def on_click(self, event):
        if self.toolbar.mode != "" or event.inaxes != self.ax:
            return

        for sc in self.scatter_collections:
            cont, ind = sc.contains(event)
            if cont:
                idx = ind["ind"][0]
                row = self.scatter_data_map[sc][idx]
                self.display_zone_details(row)
                break

    def on_close(self):
        plt.close("all")
        self.root.quit()
        self.root.destroy()


def load_zone_animal_lookup():
    lookup = {}
    readable_dir = Path(r"C:\Users\gills\Results_readable")
    report_species = {}

    if SPECIES_HASH_REPORT.exists():
        try:
            with SPECIES_HASH_REPORT.open("r", encoding="utf-8") as f:
                report = json.load(f)
            for hash_text, details in report.items():
                species = details.get("assigned_species")
                if not species:
                    continue
                try:
                    animal_hash = int(str(hash_text).strip().removeprefix("0x"), 16)
                except (TypeError, ValueError):
                    continue
                report_species[animal_hash & 0xFFFFFFFF] = str(species)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load {SPECIES_HASH_REPORT}: {e}")

    def learn_species_hash(animal):
        animal_hash = canonical_uint32(
            animal.get("name_hash_id") or animal.get("NameHashId")
        )
        species = (
            animal.get("species")
            or animal.get("species_name")
            or animal.get("name")
        )
        if animal_hash is not None and species:
            species = str(species)
            if (
                not species.startswith("Animal Type")
                and not re.fullmatch(r"(?:0x)?[0-9a-fA-F]{8}", species)
            ):
                ANIMAL_TYPE_HASH_NAMES[animal_hash] = species

    parsed_files = [
        f
        for f in readable_dir.glob("animal_population_*_decoded_parsed.json")
        if f.is_file()
    ]

    def add_to_lookup(res_id, zone_id, animal):
        try:
            reserve_int = canonical_uint32(res_id)
            zone_int = canonical_uint32(zone_id)
            if reserve_int is None or zone_int is None:
                return
            bucket = lookup.setdefault((reserve_int, zone_int), [])
            if not any(a is animal for a in bucket):
                bucket.append(animal)
        except (TypeError, ValueError):
            pass

    for file_path in parsed_files:
        match = re.search(r"animal_population_(\d+)_", file_path.name)
        if not match:
            continue

        res_id = int(match.group(1))

        try:
            with file_path.open("r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load {file_path.name}: {e}")
            continue

        animals = extract_animals_from_json(records, default_reserve_id=res_id)

        for animal in animals:
            learn_species_hash(animal)
            animal_res = animal.get("_reserve_id", res_id)
            for zone_id in animal.get("_extracted_zones", []):
                add_to_lookup(animal_res, zone_id, animal)

    if ANIMAL_FILE.exists():
        try:
            with ANIMAL_FILE.open("r", encoding="utf-8") as f:
                all_records = json.load(f)
            all_extracted = extract_animals_from_json(
                all_records, default_reserve_id=None
            )
            for animal in all_extracted:
                learn_species_hash(animal)
                animal_res = animal.get("_reserve_id")
                if animal_res is None:
                    continue
                for zone_id in animal.get("_extracted_zones", []):
                    add_to_lookup(animal_res, zone_id, animal)
        except Exception as e:
            print(f"Warning: Could not load {ANIMAL_FILE}: {e}")

    ANIMAL_TYPE_HASH_NAMES.update(report_species)
    ANIMAL_TYPE_HASH_NAMES.update(VERIFIED_HASH_SPECIES_OVERRIDES)
    return lookup


def load_static_reserve_catalog():
    if not STATIC_ANIMAL_CATALOG.exists():
        return
    try:
        with STATIC_ANIMAL_CATALOG.open("r", encoding="utf-8") as f:
            catalog = json.load(f)
        hashes_by_species = {}
        for item in catalog.get("animal_name_hashes", []):
            ANIMAL_TYPE_HASH_NAMES[item["hash32"]] = item["species"]
            hashes_by_species.setdefault(item["species"], []).append(
                item["hash32"]
            )
        for reserve_id, reserve in catalog.get("reserves", {}).items():
            names = [animal["name"] for animal in reserve.get("animals", [])]
            if names:
                existing = RESERVE_SPECIES_NAMES.setdefault(int(reserve_id), {})
                reserve_hashes = RESERVE_STATIC_NAME_HASHES.setdefault(
                    int(reserve_id), {}
                )
                for index, name in enumerate(names):
                    if name not in existing.values():
                        existing[-(index + 1)] = name
                    for animal_hash in hashes_by_species.get(name, []):
                        reserve_hashes[animal_hash] = name
    except (OSError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load {STATIC_ANIMAL_CATALOG}: {e}")


def canonical_uint32(value):
    """Normalize signed, unsigned, hexadecimal, and numeric-string IDs."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            if value.lower().startswith("0x"):
                value = int(value, 16)
            elif any(character in "abcdefABCDEF" for character in value):
                value = int(value, 16)
            else:
                value = int(value, 10)
        return int(value) & 0xFFFFFFFF
    except (TypeError, ValueError, OverflowError):
        return None


def main():
    if not ZONE_FILE.exists():
        print(f"Error: Could not find CSV at {ZONE_FILE}")
        return

    df = pd.read_csv(ZONE_FILE)
    if MASTER_ZONE_FILE.exists():
        try:
            master_df = pd.read_csv(MASTER_ZONE_FILE)
            df = pd.concat([df, master_df], ignore_index=True)
            df = df.drop_duplicates(
                subset=["ReserveId", "NeedZoneId", "NeedType"],
                keep="first",
            )
            print(f"Loaded master need zones: {MASTER_ZONE_FILE}")
        except (OSError, pd.errors.ParserError) as e:
            print(f"Warning: Could not load {MASTER_ZONE_FILE}: {e}")
    df["ReserveId"] = pd.to_numeric(df["ReserveId"], errors="coerce").astype(
        "Int64"
    )
    df["NeedZoneId"] = pd.to_numeric(df["NeedZoneId"], errors="coerce")
    df["NeedType"] = pd.to_numeric(df["NeedType"], errors="coerce").astype(
        "Int64"
    )
    df["Position_X"] = pd.to_numeric(df["Position_X"], errors="coerce")
    df["Position_Z"] = pd.to_numeric(df["Position_Z"], errors="coerce")
    df = df.dropna(
        subset=[
            "ReserveId",
            "NeedZoneId",
            "NeedType",
            "Position_X",
            "Position_Z",
        ]
    ).copy()

    load_static_reserve_catalog()
    animal_lookup = load_zone_animal_lookup()

    root = tk.Tk()
    app = NeedZoneApp(root, df, animal_lookup)
    root.mainloop()
    sys.exit(0)


if __name__ == "__main__":
    main()