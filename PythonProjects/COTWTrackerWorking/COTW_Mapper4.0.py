from collections import Counter
from functools import lru_cache
import io
import json
import os
from pathlib import Path
import re
import sys
import tkinter as tk
from tkinter import ttk
import urllib.request

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk,
)
from matplotlib.figure import Figure
from matplotlib.legend_handler import HandlerBase
from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from svgelements import SVG, Close as SvgClose, Move as SvgMove
from svgelements import Path as SvgPath
from svgelements import Shape as SvgShape

from ADF_Reader import GLOBAL_SPECIES_PROFILES
from species_metadata import SPECIES_METADATA


SPECIES_METADATA_ALIASES = {
    "Brown Bear": "Eurasian Brown Bear",
    "Reindeer": "Mountain Reindeer",
    "Musk Deer": "Siberian Musk Deer",
    "Caribou": "Grant Caribou",
    "Wild Turkey": "Merriam Turkey",
    "Northern Bobwhite Quail": "Bobwhite Quail",
    "Eastern Grey Kangaroo": "Eastern Gray Kangaroo",
    "Green-winged Teal": "Green Winged Teal",
    "Merriam's Turkey": "Merriam Turkey",
}


def metadata_species_for_reserve(reserve_id):
    return SPECIES_METADATA.get(int(reserve_id), {})


def normalize_species_for_reserve(species, reserve_id):
    if not species:
        return None
    allowed = metadata_species_for_reserve(reserve_id)
    species = str(species).strip()
    if species in allowed:
        return species

    alias = SPECIES_METADATA_ALIASES.get(species)
    if alias in allowed:
        return alias

    normalized = re.sub(r"[^a-z0-9]", "", species.lower())
    matches = [
        name for name in allowed
        if re.sub(r"[^a-z0-9]", "", name.lower()) == normalized
    ]
    if len(matches) == 1:
        return matches[0]
    return None

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
# Source map tiles are up to 8192x8192; resampling that on every pan/zoom
# redraw is the main cause of drag/zoom lag, so a smaller display copy is
# cached and used instead (see get_map_image).
MAP_DISPLAY_MAX_DIM = 2200

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

# Per-reserve cache for animal-record name_hash_id -> species. Keyed by
# (reserve_id, hash) so a resolution made on one reserve (or one slot of a
# shared need zone) can never leak the wrong species onto another record.
RECORD_HASH_SPECIES_CACHE = {}

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

# Official COTW need-zone icons, rasterized from vector art at runtime and
# used for the map legend so it matches the in-game HUD icons.
NEED_ZONE_ICON_DIR = Path(
    r"C:\Users\gills\JaimieProjects\PythonProjects\COTWTrackerWorking\NeedZoneSVG's"
)
NEED_TYPE_ICON_FILES = {
    1: NEED_ZONE_ICON_DIR / "FeedingZoneIcon.svg",
    2: NEED_ZONE_ICON_DIR / "DrinkingZoneIcon.svg",
    3: NEED_ZONE_ICON_DIR / "RestingZoneIcon.svg",
}

# Only render need-zone markers once the visible view is zoomed in to at
# most this fraction of the reserve's full extent, and only draw the
# markers that actually fall inside the current view, so panning/zooming a
# reserve with thousands of zones stays responsive.
NEED_ZONE_ZOOM_THRESHOLD = 0.45
NEED_ZONE_VIEW_MARGIN = 0.15  # extra padding around the view, as a fraction of it
# Size is in display points (via OffsetImage's zoom), not data units, so it
# stays fixed on screen regardless of how far the map is zoomed in/out.
NEED_ZONE_MARKER_ICON_PX = 16  # on-screen size of each need-zone icon glyph
NEED_ZONE_MAX_VISIBLE_MARKERS = 350  # cap drawn per refresh, closest-first
NEED_ZONE_REFRESH_DEBOUNCE_MS = 80  # coalesce rapid pan/zoom events


def _svg_color_to_rgba01(value):
    """Convert an svgelements Color to a 0-1 (r, g, b, a) tuple, or None."""
    if value is None or str(value) == "none" or value.red is None:
        return None
    alpha = value.opacity if value.opacity is not None else 1.0
    return (value.red / 255, value.green / 255, value.blue / 255, alpha)


def _flatten_svg_shape(shape, samples_per_curve=32):
    """Flatten an svgelements shape into a list of polygons (point lists)."""
    path = SvgPath(shape)
    subpaths = []
    current = []
    for seg in path:
        if isinstance(seg, SvgMove):
            if current:
                subpaths.append(current)
            current = [(seg.end.x, seg.end.y)]
        elif isinstance(seg, SvgClose):
            if current:
                current.append((seg.end.x, seg.end.y))
        else:
            for i in range(1, samples_per_curve + 1):
                pt = seg.point(i / samples_per_curve)
                current.append((pt.x, pt.y))
    if current:
        subpaths.append(current)
    return subpaths


@lru_cache(maxsize=None)
def load_need_zone_icon(need_type, size=48, supersample=4):
    """Rasterize a need-zone SVG icon to an RGBA numpy array, cached by size.

    Rendered with matplotlib's PathPatch (nonzero winding fill), because
    these icons rely on overlapping same-colour subpaths punching out
    negative-space cutouts (e.g. the drop/leaf/zzz silhouettes) — a plain
    per-subpath fill would just paint over those holes.
    """
    svg_path = NEED_TYPE_ICON_FILES.get(need_type)
    if svg_path is None or not svg_path.exists():
        return None

    try:
        svg = SVG.parse(str(svg_path))
        canvas_px = size * supersample
        dpi = 100
        fig = Figure(figsize=(canvas_px / dpi, canvas_px / dpi), dpi=dpi)
        fig.patch.set_alpha(0.0)
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.patch.set_alpha(0.0)
        ax.set_xlim(0, 512)
        ax.set_ylim(512, 0)  # SVG's y-axis points down
        ax.set_axis_off()

        for shape in svg.elements():
            if not isinstance(shape, SvgShape):
                continue
            fill = _svg_color_to_rgba01(shape.fill)
            stroke = _svg_color_to_rgba01(shape.stroke)
            stroke_width_pt = (
                (shape.stroke_width or 0) * (canvas_px / 512.0) * 72.0 / dpi
            )

            verts, codes = [], []
            for subpath in _flatten_svg_shape(shape):
                verts.append(subpath[0])
                codes.append(MplPath.MOVETO)
                for pt in subpath[1:]:
                    verts.append(pt)
                    codes.append(MplPath.LINETO)
                verts.append(subpath[0])
                codes.append(MplPath.CLOSEPOLY)
            if not verts:
                continue

            ax.add_patch(PathPatch(
                MplPath(verts, codes),
                facecolor=fill if fill else "none",
                edgecolor=stroke if stroke else "none",
                linewidth=stroke_width_pt if stroke else 0,
                joinstyle="round",
            ))

        canvas.draw()
        img = Image.fromarray(np.asarray(canvas.buffer_rgba()), mode="RGBA")

        # Trim the transparent margin around the icon (down to just outside
        # the white circular border) so it isn't drawn smaller than it needs
        # to be once resized.
        bbox = img.getchannel("A").getbbox()
        if bbox:
            pad = max(2, supersample)
            img = img.crop((
                max(bbox[0] - pad, 0),
                max(bbox[1] - pad, 0),
                min(bbox[2] + pad, img.width),
                min(bbox[3] + pad, img.height),
            ))

        return np.asarray(img.resize((size, size), Image.LANCZOS))
    except Exception:
        return None



class _IconLegendHandler(HandlerBase):
    """Draws a legend entry as a small raster icon instead of a marker."""

    def __init__(self, image):
        super().__init__()
        self.image = image

    def create_artists(
        self, legend, orig_handle, xdescent, ydescent, width, height,
        fontsize, trans,
    ):
        size = min(width, height)
        offset_image = OffsetImage(self.image, zoom=size / self.image.shape[0])
        ab = AnnotationBbox(
            offset_image,
            (width / 2 - xdescent, height / 2 - ydescent),
            xycoords=trans,
            frameon=False,
        )
        return [ab]


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


def _load_full_map_image(reserve_id):
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

    return None


@lru_cache(maxsize=None)
def get_map_image(reserve_id):
    """Background map for the given reserve, downsized for interactive draws.

    The source tiles are up to 8192x8192; resampling that every single
    pan/zoom redraw is the main drag/zoom lag, so a display-resolution copy
    is cached (in memory and on disk) and reused instead of the full-res art.
    """
    display_cache = MAP_CACHE_DIR / f"reserve_{reserve_id}_display.png"
    if display_cache.exists():
        try:
            return Image.open(display_cache)
        except Exception:
            pass

    img = _load_full_map_image(reserve_id)
    if img is None:
        return generate_fallback_grid()

    if max(img.size) > MAP_DISPLAY_MAX_DIM:
        scale = MAP_DISPLAY_MAX_DIM / max(img.size)
        new_size = (
            max(1, int(img.width * scale)), max(1, int(img.height * scale)),
        )
        img = img.convert("RGBA").resize(new_size, Image.LANCZOS)
        try:
            img.save(display_cache)
        except Exception:
            pass
    return img


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
    candidates = list(metadata_species_for_reserve(reserve_id))
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
    allowed_species = metadata_species_for_reserve(reserve_id)
    reserve_hashes = RESERVE_HASH_SPECIES_OVERRIDES.get(int(reserve_id), {})
    static_hashes = RESERVE_STATIC_NAME_HASHES.get(int(reserve_id), {})
    for rec in matches:
        record_hash = canonical_uint32(
            rec.get("name_hash_id") or rec.get("NameHashId")
        )
        if record_hash in reserve_hashes:
            resolved = normalize_species_for_reserve(
                reserve_hashes[record_hash], reserve_id
            )
            if resolved:
                return resolved
        if record_hash in static_hashes:
            resolved = normalize_species_for_reserve(
                static_hashes[record_hash], reserve_id
            )
            if resolved:
                return resolved

    need_type = canonical_uint32(row.get("NeedType"))
    override = RESERVE_NEED_SPECIES_OVERRIDES.get(int(reserve_id), {}).get(
        need_type
    )
    if override:
        animal_type_id = canonical_uint32(row.get("AnimalTypeLocalizationName"))
        override = normalize_species_for_reserve(override, reserve_id)
        if override and animal_type_id is not None:
            ANIMAL_TYPE_HASH_NAMES[animal_type_id] = override
        if override:
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
                resolved = normalize_species_for_reserve(resolved, reserve_id)
                if resolved:
                    return resolved
            resolved = static_hashes.get(animal_type_id)
            if resolved:
                resolved = normalize_species_for_reserve(resolved, reserve_id)
                if resolved:
                    return resolved
            resolved = ANIMAL_TYPE_HASH_NAMES.get(animal_type_id)
            if resolved:
                resolved = normalize_species_for_reserve(resolved, reserve_id)
                if resolved:
                    return resolved

            reserve_types = RESERVE_SPECIES_NAMES.get(int(reserve_id), {})
            resolved = reserve_types.get(animal_type_id)
            if resolved and not resolved.startswith("Animal Type"):
                species_name = normalize_species_for_reserve(
                    resolved, reserve_id
                )

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
            resolved = normalize_species_for_reserve(resolved, reserve_id)
            if resolved:
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
                resolved = normalize_species_for_reserve(sp, reserve_id)
                if resolved:
                    species_list.append(resolved)
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


def resolve_record_species(rec, zone_species, reserve_id, zone_guid_species=None):
    """Resolve a single linked animal record's species.

    The global ``ANIMAL_TYPE_HASH_NAMES`` table is keyed by ``name_hash_id``,
    but those hashes are NOT unique across reserves (the same hash means
    'Axis Deer' on one reserve and labels a Black Bear on another), and many
    record hashes appear in no table at all. The only reliable per-reserve
    species source is the need-zone CSV's ``AnimalTypeLocalizationName``.

    Resolution order:
    1. The species of the decoded zone the record is standing in
       (``zone_guid_species``), which is authoritative per reserve.
    2. The explicitly-provided ``zone_species`` (the zone being displayed).
    3. Reserve-scoped override / static-hash tables.
    4. The global hash table, only when its name is valid on THIS reserve.
    5. Weight / trophy attribute inference as a last resort.

    Resolutions are cached per (reserve, hash) so identical records stay
    consistent within a reserve without leaking across reserves.
    """
    reserve_id_int = int(reserve_id) if reserve_id is not None else None
    record_hash = canonical_uint32(
        rec.get("name_hash_id") or rec.get("NameHashId")
    )

    cache_key = (reserve_id_int, record_hash)
    if record_hash is not None and cache_key in RECORD_HASH_SPECIES_CACHE:
        return RECORD_HASH_SPECIES_CACHE[cache_key]

    resolved = None

    # 1. Species of the decoded zone(s) this record occupies.
    if zone_guid_species:
        for z in rec.get("_extracted_zones", []) or []:
            zid = canonical_uint32(z)
            if zid in zone_guid_species:
                resolved = normalize_species_for_reserve(
                    zone_guid_species[zid], reserve_id_int
                )
                if resolved:
                    break

    # 2. The zone currently being displayed.
    if not resolved and zone_species and zone_species != "Unknown Species":
        resolved = normalize_species_for_reserve(zone_species, reserve_id_int)

    if not resolved and record_hash is not None:
        # 3. Reserve-scoped override / static tables.
        reserve_hashes = RESERVE_HASH_SPECIES_OVERRIDES.get(reserve_id_int, {})
        static_hashes = RESERVE_STATIC_NAME_HASHES.get(reserve_id_int, {})
        raw = reserve_hashes.get(record_hash) or static_hashes.get(record_hash)
        resolved = normalize_species_for_reserve(raw, reserve_id_int)
        # 4. Global table, only when valid on THIS reserve.
        if not resolved:
            resolved = normalize_species_for_reserve(
                ANIMAL_TYPE_HASH_NAMES.get(record_hash), reserve_id_int
            )

    # 5. Last resort: infer from this record's weight / trophy attributes.
    if not resolved:
        resolved = infer_species_from_attributes([rec], reserve_id_int)

    if not resolved:
        return "Unknown Species"

    if record_hash is not None:
        RECORD_HASH_SPECIES_CACHE[(reserve_id_int, record_hash)] = resolved
    return resolved


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

        # Per-reserve map of need-zone GUID -> species, built from the zone
        # CSV's authoritative AnimalTypeLocalizationName. This is the only
        # species source that is reliable per reserve (animal-record
        # name_hash_id values collide across reserves), so it is the primary
        # signal for resolving which species an animal record belongs to.
        self.zone_guid_species = {}
        for (res_id, zone_id), zgroup in self.df.groupby(
            ["ReserveId", "NeedZoneId"]
        ):
            zid = canonical_uint32(zone_id)
            if zid is None:
                continue
            species = resolve_zone_species(
                zgroup.iloc[0].to_dict(), [], res_id
            )
            if species and species != "Unknown Species":
                self.zone_guid_species.setdefault(int(res_id), {})[zid] = (
                    species
                )

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

        # --- Left species navigation sidebar ---
        nav_frame = ttk.LabelFrame(paned, text=" Species ", padding=(6, 6))
        paned.add(nav_frame, weight=0)

        # Species buttons (the "widgets") live at the top of the sidebar.
        self.species_button_frame = ttk.Frame(nav_frame)
        self.species_button_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(
            nav_frame,
            text="Animals (high → low level)",
            font=("Arial", 9, "bold"),
        ).pack(side=tk.TOP, anchor="w", pady=(8, 2))

        # Scrollable animal listbox below the species buttons.
        list_container = ttk.Frame(nav_frame)
        list_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.animal_list = tk.Listbox(
            list_container,
            font=("Consolas", 9),
            activestyle="none",
            exportselection=False,
            width=30,
        )
        list_scroll = ttk.Scrollbar(
            list_container, orient="vertical", command=self.animal_list.yview
        )
        self.animal_list.configure(yscrollcommand=list_scroll.set)
        self.animal_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.animal_list.bind("<<ListboxSelect>>", self.on_animal_nav_select)
        self._nav_records = []  # records backing the current listbox rows

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

        # Cached data for the current reserve, used to redraw only the
        # need-zone markers visible in the current viewport as the user
        # zooms/pans, instead of replotting the whole reserve every time.
        self._zone_view_sub_df = None
        self._zone_view_bounds = None
        self._zone_artists = []
        self._zoom_hint_artist = None
        self._zone_refresh_job = None
        self._pan_active = False
        self._pan_dragged = False
        self._clamping_view = False

        self.canvas.mpl_connect("button_press_event", self.on_mouse_press)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("button_release_event", self.on_mouse_release)
        self.canvas.mpl_connect("scroll_event", self.on_scroll_zoom)
        self.update_plot()
        self.refresh_species_nav()

    def on_reserve_change(self, event):
        self.update_plot()
        self.refresh_species_nav()

    def _current_reserve_animals(self):
        """All linked animal records for the currently selected reserve."""
        selected_label = self.dropdown.get()
        rid = self.reserve_map.get(selected_label)
        if rid is None:
            return None, []
        rid_key = canonical_uint32(rid)
        records = []
        seen = set()
        for (res_id, _zone_id), animals in self.animal_lookup.items():
            if res_id != rid_key:
                continue
            for rec in animals:
                if id(rec) not in seen:
                    seen.add(id(rec))
                    records.append(rec)
        return rid, records

    def _animal_level_info(self, rec, reserve_id, species):
        """Return (sort_level, level_text) for an animal record."""
        trophy_val = (
            rec.get("score")
            or rec.get("trophy_score")
            or rec.get("trophy_rating")
        )
        weight_val = (
            rec.get("weight_kg") or rec.get("weight") or rec.get("body_weight")
        )
        level_str, _diamond = estimate_trophy_status(
            species,
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
        # Leading integer of "N (Name; max M)" drives the high→low sort.
        try:
            sort_level = int(str(level_str).split(" ", 1)[0])
        except (ValueError, IndexError):
            sort_level = -1
        return sort_level, level_str

    def refresh_species_nav(self):
        """Rebuild the species buttons for the selected reserve."""
        for widget in self.species_button_frame.winfo_children():
            widget.destroy()
        self.animal_list.delete(0, tk.END)
        self._nav_records = []

        rid, records = self._current_reserve_animals()
        if rid is None:
            return

        # Group records by resolved species, preserving metadata order.
        guid_map = self.zone_guid_species.get(int(rid), {})
        species_groups = {}
        for rec in records:
            species = resolve_record_species(rec, None, rid, guid_map)
            species_groups.setdefault(species, []).append(rec)

        ordered = [s for s in metadata_species_for_reserve(rid)
                   if s in species_groups]
        ordered += sorted(s for s in species_groups if s not in ordered)

        if not ordered:
            ttk.Label(
                self.species_button_frame,
                text="No animals decoded.",
                font=("Arial", 9, "italic"),
            ).pack(anchor="w")
            return

        for species in ordered:
            count = len(species_groups[species])
            btn = ttk.Button(
                self.species_button_frame,
                text=f"{species} ({count})",
                command=lambda s=species: self.show_species_animals(s),
            )
            btn.pack(side=tk.TOP, fill=tk.X, pady=1)

        # Auto-select the first species so the list is populated.
        self.show_species_animals(ordered[0])

    def show_species_animals(self, species):
        """Fill the animal listbox with one species, sorted high→low level."""
        self.animal_list.delete(0, tk.END)
        self._nav_records = []

        rid, records = self._current_reserve_animals()
        if rid is None:
            return

        entries = []
        guid_map = self.zone_guid_species.get(int(rid), {})
        for rec in records:
            rec_species = resolve_record_species(rec, None, rid, guid_map)
            if rec_species != species:
                continue
            sort_level, level_str = self._animal_level_info(rec, rid, species)
            entries.append((sort_level, level_str, rec))

        # Highest level first; ties broken by descending score.
        def _score(rec):
            try:
                return float(
                    rec.get("score")
                    or rec.get("trophy_score")
                    or rec.get("trophy_rating")
                    or 0
                )
            except (TypeError, ValueError):
                return 0.0

        entries.sort(key=lambda e: (e[0], _score(e[2])), reverse=True)

        for sort_level, level_str, rec in entries:
            gender = rec.get("gender") or rec.get("gender_name") or "?"
            gender_char = str(gender)[0].upper() if gender else "?"
            weight_val = (
                rec.get("weight_kg") or rec.get("weight")
                or rec.get("body_weight")
            )
            try:
                weight_str = f"{float(weight_val):.0f}kg"
            except (TypeError, ValueError):
                weight_str = "  ?kg"
            level_num = level_str.split(" ", 1)[0]
            self.animal_list.insert(
                tk.END, f"L{level_num:<2} {gender_char} {weight_str:>6}"
            )
            self._nav_records.append(rec)

    def on_animal_nav_select(self, event):
        """Clicking an animal in the sidebar highlights its zone details."""
        selection = self.animal_list.curselection()
        if not selection:
            return
        rec = self._nav_records[selection[0]]
        rid, _records = self._current_reserve_animals()
        if rid is None:
            return

        # Prefer the record's own zone list; fall back to its map position.
        zone_ids = rec.get("_extracted_zones") or []
        target = None
        if zone_ids:
            zid = canonical_uint32(zone_ids[0])
            rows = self.df[
                (self.df["ReserveId"] == rid)
                & (self.df["NeedZoneId"].apply(canonical_uint32) == zid)
            ]
            if not rows.empty:
                target = rows.iloc[0].to_dict()
        if target is None:
            pos = rec.get("map_position") or {}
            px = pos.get("x") or pos.get("X")
            pz = pos.get("z") or pos.get("Z")
            if px is not None and pz is not None:
                rows = self.df[
                    (self.df["ReserveId"] == rid)
                    & (self.df["Position_X"].round(0) == round(float(px)))
                    & (self.df["Position_Z"].round(0) == round(float(pz)))
                ]
                if not rows.empty:
                    target = rows.iloc[0].to_dict()
        if target is not None:
            self.display_zone_details(target)

    def update_plot(self):
        self.ax.clear()
        # ax.clear() drops any previously registered callbacks, so the
        # viewport-based marker refresh must be reconnected every time.
        self.ax.callbacks.connect("xlim_changed", self.on_view_changed)
        self.ax.callbacks.connect("ylim_changed", self.on_view_changed)
        self.scatter_collections.clear()
        self.scatter_data_map.clear()
        self._zone_artists = []
        self._zoom_hint_artist = None

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
            self._zone_view_sub_df = None
            return

        sub_df = self.df[self.df["ReserveId"] == rid].copy()
        if sub_df.empty:
            self._zone_view_sub_df = None
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

        # Cache the reserve's full data set so zoom/pan can redraw only the
        # markers visible in the viewport without recomputing any of this.
        self._zone_view_sub_df = sub_df
        self._zone_view_bounds = (left, right, bottom, top)

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

        self._build_legend()
        self._refresh_zone_markers()

    def _build_legend(self):
        """Build a legend that uses the actual COTW need-zone icons."""
        handles = []
        labels = []
        handler_map = {}
        for need_type, meta in NEED_TYPES.items():
            icon = load_need_zone_icon(need_type)
            proxy = Line2D([], [], linestyle="none")
            if icon is not None:
                handler_map[proxy] = _IconLegendHandler(icon)
            else:
                proxy = Line2D(
                    [], [], marker=meta["marker"], color=meta["color"],
                    linestyle="none", markeredgecolor="black",
                    markersize=8,
                )
            handles.append(proxy)
            labels.append(f"{meta['name']} Zone")

        self.ax.legend(
            handles, labels, handler_map=handler_map, loc="upper right",
            handlelength=2.0, handleheight=2.0, labelspacing=0.9,
            fontsize=9, borderpad=0.6,
        )

    def on_view_changed(self, _axes):
        # Also clamp views set by the toolbar's own Pan/Zoom-rect tools; the
        # guard flag stops the set_xlim/set_ylim calls below from recursing.
        if not self._clamping_view:
            xlim, ylim = self.ax.get_xlim(), self.ax.get_ylim()
            clamped_xlim, clamped_ylim = self._clamp_view_to_bounds(xlim, ylim)
            if clamped_xlim != xlim or clamped_ylim != ylim:
                self._clamping_view = True
                try:
                    self.ax.set_xlim(clamped_xlim)
                    self.ax.set_ylim(clamped_ylim)
                finally:
                    self._clamping_view = False

        # Coalesce bursts of pan/zoom events (a single scroll tick already
        # fires this twice, once for x and once for y) into one redraw.
        if self._zone_refresh_job is not None:
            self.root.after_cancel(self._zone_refresh_job)
        self._zone_refresh_job = self.root.after(
            NEED_ZONE_REFRESH_DEBOUNCE_MS, self._run_debounced_zone_refresh
        )

    def _run_debounced_zone_refresh(self):
        self._zone_refresh_job = None
        self._refresh_zone_markers()

    def _hide_zone_markers(self):
        """Hide icon/marker artists so in-flight drag/zoom redraws only have
        to resample the basemap, not re-blit every icon; the debounced
        refresh rebuilds and shows the correct set once the view settles."""
        for artist in self._zone_artists:
            artist.set_visible(False)
        if self._zoom_hint_artist is not None:
            self._zoom_hint_artist.set_visible(False)

    def _refresh_zone_markers(self):
        """Redraw only the need-zone markers inside the current viewport.

        Below `NEED_ZONE_ZOOM_THRESHOLD` (i.e. zoomed out), no markers are
        drawn at all so panning/zooming a reserve with many zones stays
        responsive; a hint is shown instead.
        """
        for artist in self._zone_artists:
            artist.remove()
        self._zone_artists = []
        self.scatter_collections.clear()
        self.scatter_data_map.clear()
        if self._zoom_hint_artist is not None:
            self._zoom_hint_artist.remove()
            self._zoom_hint_artist = None

        sub_df = self._zone_view_sub_df
        if sub_df is None or sub_df.empty or self._zone_view_bounds is None:
            self.canvas.draw_idle()
            return

        left, right, bottom, top = self._zone_view_bounds
        full_width = abs(right - left)
        full_height = abs(top - bottom)

        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        view_width = abs(xlim[1] - xlim[0])
        view_height = abs(ylim[1] - ylim[0])

        zoomed_in_enough = (
            full_width > 0 and view_width <= full_width * NEED_ZONE_ZOOM_THRESHOLD
        ) or (
            full_height > 0
            and view_height <= full_height * NEED_ZONE_ZOOM_THRESHOLD
        )

        if not zoomed_in_enough:
            self._zoom_hint_artist = self.ax.text(
                0.5, 0.5,
                "Zoom in to view need zone markers",
                transform=self.ax.transAxes,
                ha="center", va="center",
                fontsize=11, fontweight="bold", color="white",
                bbox=dict(boxstyle="round", facecolor="black", alpha=0.55),
                zorder=5,
            )
            self.canvas.draw_idle()
            return

        x_min, x_max = min(xlim), max(xlim)
        y_min, y_max = min(ylim), max(ylim)
        margin_x = view_width * NEED_ZONE_VIEW_MARGIN
        margin_y = view_height * NEED_ZONE_VIEW_MARGIN
        visible_df = sub_df[
            sub_df["Plot_X"].between(x_min - margin_x, x_max + margin_x)
            & sub_df["Plot_Z"].between(y_min - margin_y, y_max + margin_y)
        ]

        # Cap how many markers get built each refresh (AnnotationBbox
        # objects are relatively expensive) so a very dense area can't stall
        # panning/zooming; keep whichever are closest to the view center.
        if len(visible_df) > NEED_ZONE_MAX_VISIBLE_MARKERS:
            center_x = (x_min + x_max) / 2.0
            center_z = (y_min + y_max) / 2.0
            dist2 = (
                (visible_df["Plot_X"] - center_x) ** 2
                + (visible_df["Plot_Z"] - center_z) ** 2
            )
            visible_df = visible_df.loc[
                dist2.nsmallest(NEED_ZONE_MAX_VISIBLE_MARKERS).index
            ]

        for need_type, meta in NEED_TYPES.items():
            type_df = visible_df[visible_df["NeedType"] == need_type]
            if type_df.empty:
                continue

            icon = load_need_zone_icon(need_type)

            # The scatter is the click-hit target; when an icon is drawn it
            # is made invisible and the icon image is the visible glyph.
            sc = self.ax.scatter(
                type_df["Plot_X"],
                type_df["Plot_Z"],
                c=meta["color"] if icon is None else "none",
                marker=meta["marker"],
                alpha=0.85 if icon is None else 0.0,
                s=45,
                edgecolors="black" if icon is None else "none",
                linewidths=0.6,
                zorder=2,
                picker=5,
            )
            self.scatter_collections.append(sc)
            self.scatter_data_map[sc] = type_df.to_dict("records")
            self._zone_artists.append(sc)

            if icon is not None:
                zoom = NEED_ZONE_MARKER_ICON_PX / icon.shape[0]
                for plot_x, plot_z in zip(type_df["Plot_X"], type_df["Plot_Z"]):
                    ab = AnnotationBbox(
                        OffsetImage(icon, zoom=zoom),
                        (plot_x, plot_z),
                        frameon=False,
                        pad=0,
                        zorder=3,
                    )
                    self.ax.add_artist(ab)
                    self._zone_artists.append(ab)

        self.canvas.draw_idle()

    def display_zone_details(self, row):
        reserve_id = int(row["ReserveId"])
        zone_id = int(row["NeedZoneId"])
        need_type_id = int(row["NeedType"])
        type_name = NEED_TYPES.get(need_type_id, {}).get("name", "Unknown")

        matches = self.animal_lookup.get(
            (canonical_uint32(reserve_id), canonical_uint32(zone_id)), []
        )

        # Species can share a single physical need zone. The save stores one
        # record per species/schedule slot, and shared zones sit at identical
        # coordinates with the same need type (measured distinct zones are
        # never closer than ~64 m apart, so meter-level position matching is
        # a safe sharing signal that does not merge merely-nearby zones).
        # Collect every record at this spot, regardless of NeedZoneId, so we
        # can list each species together with its active time window.
        pos_x = round(float(row["Position_X"]))
        pos_z = round(float(row["Position_Z"]))
        cluster = self.df[
            (self.df["ReserveId"] == reserve_id)
            & (self.df["NeedType"] == need_type_id)
            & (self.df["Position_X"].round(0) == pos_x)
            & (self.df["Position_Z"].round(0) == pos_z)
        ]
        zone_rows = cluster.to_dict("records") if not cluster.empty else [row]

        # Union the animal links across every zone id registered at this spot.
        matches = []
        seen_records = set()
        for zr in zone_rows:
            try:
                cid = int(zr["NeedZoneId"])
            except (TypeError, ValueError):
                continue
            for rec in self.animal_lookup.get(
                (canonical_uint32(reserve_id), canonical_uint32(cid)), []
            ):
                if id(rec) not in seen_records:
                    seen_records.add(id(rec))
                    matches.append(rec)

        def _fmt_time(value):
            try:
                hour = float(value)
                return f"{hour:04.1f}"
            except (TypeError, ValueError):
                return "?"

        # Build an ordered list of (species, time window, schedule index)
        # preserving the first-seen order in the data.
        species_slots = []
        seen_slots = set()
        for zrow in zone_rows:
            species = resolve_zone_species(zrow, matches, reserve_id)
            start = _fmt_time(zrow.get("NeedZoneStartTimeHours"))
            end = _fmt_time(zrow.get("NeedZoneEndTimeHours"))
            sched = zrow.get("NeedZoneScheduleIndex")
            slot_key = (species, start, end)
            if slot_key in seen_slots:
                continue
            seen_slots.add(slot_key)
            label = f"{species} {start}–{end}h"
            if sched is not None and str(sched) not in ("", "nan"):
                label += f" (slot {sched})"
            species_slots.append((species, label))

        zone_species = species_slots[0][0] if species_slots else "Unknown Species"

        # Map each zone id in this cluster to its own authoritative CSV
        # species. In a shared zone, an animal linked to the Whitetail zone id
        # must resolve as Whitetail, not as the first slot's species.
        zone_id_species = {}
        for zr in zone_rows:
            try:
                cid = canonical_uint32(int(zr["NeedZoneId"]))
            except (TypeError, ValueError):
                continue
            if cid is not None and cid not in zone_id_species:
                zone_id_species[cid] = resolve_zone_species(zr, matches, reserve_id)

        def species_for_record(rec):
            """Species for one linked record, keyed by its own zone."""
            guid_map = self.zone_guid_species.get(int(reserve_id), {})
            for z in rec.get("_extracted_zones", []):
                zid = canonical_uint32(z)
                if zid in zone_id_species:
                    return resolve_record_species(
                        rec, zone_id_species[zid], reserve_id, guid_map
                    )
            return resolve_record_species(rec, zone_species, reserve_id, guid_map)

        # Shared spots list every linked animal (the tree resolves each
        # record's species individually); single-species zones keep the legacy
        # filter that drops mismatched linked records.
        if len(species_slots) <= 1:
            species_matches = []
            guid_map = self.zone_guid_species.get(int(reserve_id), {})
            for rec in matches:
                record_species = resolve_record_species(
                    rec, zone_species, reserve_id, guid_map
                )
                if record_species == zone_species:
                    species_matches.append(rec)
            if zone_species != "Unknown Species":
                matches = species_matches

        if len(species_slots) > 1:
            zone_ids = sorted(
                {
                    int(zr["NeedZoneId"])
                    for zr in zone_rows
                    if str(zr.get("NeedZoneId", "")).strip() not in ("", "nan")
                }
            )
            zone_title = (
                f"Shared Zone ({type_name}) — IDs: "
                + ", ".join(str(z) for z in zone_ids)
                + "\n"
                + ", ".join(label for _, label in species_slots)
            )
        else:
            zone_title = f"Zone ID: {zone_id} ({zone_species} {type_name})"

        self.lbl_zone_info.config(
            text=zone_title,
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
            record_species = species_for_record(rec)
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

    def on_scroll_zoom(self, event):
        """Zoom the map in/out around the cursor using the mouse scroll wheel."""
        if event.inaxes != self.ax:
            return

        self._hide_zone_markers()

        base_scale = 1.2
        scale_factor = 1 / base_scale if event.button == "up" else base_scale

        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        xdata = event.xdata
        ydata = event.ydata
        if xdata is None or ydata is None:
            return

        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

        new_xlim = (xdata - new_width * (1 - relx), xdata + new_width * relx)
        new_ylim = (ydata - new_height * (1 - rely), ydata + new_height * rely)
        new_xlim, new_ylim = self._clamp_view_to_bounds(new_xlim, new_ylim)

        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.canvas.draw_idle()

    def _clamp_view_to_bounds(self, xlim, ylim):
        """Prevent zooming out past, or panning outside of, the full map."""
        bounds = self._zone_view_bounds
        if bounds is None:
            return xlim, ylim

        left, right, bottom, top = bounds
        full_left, full_right = min(left, right), max(left, right)
        full_bottom, full_top = min(bottom, top), max(bottom, top)
        full_width = full_right - full_left
        full_height = full_top - full_bottom

        x_lo, x_hi = min(xlim), max(xlim)
        y_lo, y_hi = min(ylim), max(ylim)
        width = min(x_hi - x_lo, full_width)
        height = min(y_hi - y_lo, full_height)

        cx = (x_lo + x_hi) / 2.0
        cy = (y_lo + y_hi) / 2.0
        x_lo, x_hi = cx - width / 2.0, cx + width / 2.0
        y_lo, y_hi = cy - height / 2.0, cy + height / 2.0

        # Slide the viewport back inside the map bounds instead of resizing.
        if x_lo < full_left:
            x_hi += full_left - x_lo
            x_lo = full_left
        if x_hi > full_right:
            x_lo -= x_hi - full_right
            x_hi = full_right
        if y_lo < full_bottom:
            y_hi += full_bottom - y_lo
            y_lo = full_bottom
        if y_hi > full_top:
            y_lo -= y_hi - full_top
            y_hi = full_top

        # Preserve whichever axis orientation was requested (may be inverted).
        clamped_xlim = (x_hi, x_lo) if xlim[0] > xlim[1] else (x_lo, x_hi)
        clamped_ylim = (y_hi, y_lo) if ylim[0] > ylim[1] else (y_lo, y_hi)
        return clamped_xlim, clamped_ylim

    def on_mouse_press(self, event):
        """Start a potential left-button drag-to-pan (no toolbar click needed)."""
        if self.toolbar.mode != "" or event.inaxes != self.ax or event.button != 1:
            return
        self._pan_active = True
        self._pan_dragged = False
        self._pan_start_px = (event.x, event.y)
        self._pan_start_xlim = self.ax.get_xlim()
        self._pan_start_ylim = self.ax.get_ylim()

    def on_mouse_move(self, event):
        if not getattr(self, "_pan_active", False):
            return
        if event.x is None or event.y is None:
            return

        dx_px = event.x - self._pan_start_px[0]
        dy_px = event.y - self._pan_start_px[1]
        if not self._pan_dragged and (abs(dx_px) > 3 or abs(dy_px) > 3):
            self._pan_dragged = True
            self._hide_zone_markers()
        if not self._pan_dragged:
            return

        inv = self.ax.transData.inverted()
        x0, y0 = inv.transform(self._pan_start_px)
        x1, y1 = inv.transform((event.x, event.y))
        dx, dy = x0 - x1, y0 - y1

        xlim = self._pan_start_xlim
        ylim = self._pan_start_ylim
        new_xlim, new_ylim = self._clamp_view_to_bounds(
            (xlim[0] + dx, xlim[1] + dx), (ylim[0] + dy, ylim[1] + dy)
        )
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.canvas.draw_idle()

    def on_mouse_release(self, event):
        was_dragging = getattr(self, "_pan_dragged", False)
        self._pan_active = False
        self._pan_dragged = False
        if not was_dragging:
            self.on_click(event)

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
        if self._zone_refresh_job is not None:
            self.root.after_cancel(self._zone_refresh_job)
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

    # ANIMAL_FILE (all_animals.json) is the aggregate of the per-reserve
    # parsed files already processed above. Its records carry no reserve_id
    # field of their own, so re-parsing it here would only relearn the same
    # species hashes and would never populate the zone lookup (reserve id
    # always resolves to None) -- it was pure redundant I/O and is skipped.

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
            # Species can share a single physical need zone (same ReserveId +
            # NeedZoneId + NeedType) on different schedule slots. Only treat a
            # row as a duplicate when the species and schedule slot also match,
            # so co-located zones for different species/time windows survive.
            dedup_cols = [
                "ReserveId",
                "NeedZoneId",
                "NeedType",
                "AnimalTypeLocalizationName",
                "NeedZoneScheduleIndex",
            ]
            dedup_cols = [c for c in dedup_cols if c in df.columns]
            df = df.drop_duplicates(
                subset=dedup_cols,
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