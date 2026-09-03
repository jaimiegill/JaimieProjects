from collections import defaultdict
import json
from pathlib import Path
import re
import sys
import time

INPUT_DIR = Path(r"C:\Users\gills\JaimieProjects\PythonProjects\COTWTrackerWorking\DecodedBinariesADFFormat")
OUTPUT_DIR = Path(r"C:\Users\gills\JaimieProjects\PythonProjects\COTWTrackerWorking\DecodedADFJSONFormat")

# -------------------------------------------------------------------------
# VALID RESERVES & MAP
# -------------------------------------------------------------------------
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

VALID_RESERVE_IDS = set(RESERVE_NAMES.keys())

# -------------------------------------------------------------------------
# RESERVE-SPECIFIC NATIVE SPECIES WHITELIST
# Prevents cross-map species bleeding (e.g., Puma on Medved Taiga)
# -------------------------------------------------------------------------
RESERVE_SPECIES_WHITELIST = {
    0: {  # Hirschfelden
        "Red Deer",
        "Fallow Deer",
        "Roe Deer",
        "Wild Boar",
        "European Bison",
        "Red Fox",
        "Canada Goose",
        "Pheasant",
    },
    1: {  # Layton Lake
        "Moose",
        "Whitetail Deer",
        "Blacktail Deer",
        "Roosevelt Elk",
        "Black Bear",
        "Coyote",
        "Mallard",
        "Harlequin Duck",
    },
    2: {  # Medved Taiga
        "Moose",
        "Brown Bear",
        "Reindeer",
        "Siberian Musk Deer",
        "Eurasian Lynx",
        "Gray Wolf",
        "Western Capercaillie",
    },
    3: {  # Vurhonga Savanna
        "Springbok",
        "Lesser Kudu",
        "Warthog",
        "Blue Wildebeest",
        "Gemsbok",
        "Lion",
        "Side-striped Jackal",
    },
    4: {  # Parque Fernando
        "Puma",
        "Axis Deer",
        "Blackbuck",
        "Mule Deer",
        "Red Deer",
        "Water Buffalo",
        "Cinnamon Teal",
    },
    6: {  # Yukon Valley
        "Moose",
        "Grizzly Bear",
        "Caribou",
        "Plains Bison",
        "Harlequin Duck",
        "Red Fox",
        "Gray Wolf",
    },
    8: {  # Cuatro Colinas
        "Red Deer",
        "Roe Deer",
        "Wild Boar",
        "Fallow Deer",
        "Mouflon",
        "Iberian Wolf",
        "Beceite Ibex",
        "Gredos Ibex",
        "Ronda Ibex",
        "Southeastern Spanish Ibex",
    },
    9: {  # Silver Ridge Peaks
        "Bighorn Sheep",
        "Mountain Goat",
        "Pronghorn",
        "Plains Bison",
        "Black Bear",
        "Puma",
        "Merriam Turkey",
        "Mule Deer",
        "Rocky Mountain Elk",
    },
    10: {  # Te Awaroa
        "Fallow Deer",
        "Red Deer",
        "Sika Deer",
        "Feral Pig",
        "Chamois",
        "Wild Turkey",
    },
    11: {  # Rancho del Arroyo
        "Whitetail Deer",
        "Mule Deer",
        "Bighorn Sheep",
        "Pronghorn",
        "Coyote",
        "Collared Peccary",
        "Rio Grande Turkey",
        "Mexican Bobcat",
    },
    12: {  # Mississippi Acres
        "Whitetail Deer",
        "Black Bear",
        "Wild Boar",
        "Raccoon",
        "American Alligator",
        "Gray Fox",
        "Bobcat",
        "Wild Turkey",
    },
    13: {  # Revontuli Coast
        "Moose",
        "Brown Bear",
        "Whitetail Deer",
        "Mountain Hare",
        "Raccoon Dog",
        "Eurasian Lynx",
        "Capercaillie",
        "Black Grouse",
        "Hazel Grouse",
        "Mallard",
        "Canada Goose",
        "Greylag Goose",
    },
    14: {  # New England Mountains
        "Moose",
        "Black Bear",
        "Whitetail Deer",
        "Red Fox",
        "Coyote",
        "Raccoon",
        "Bobcat",
        "Eastern Wild Turkey",
        "Snowshoe Hare",
        "Mallard",
        "Canada Goose",
    },
    16: {  # Emerald Coast
        "Banteng",
        "Red Deer",
        "Fallow Deer",
        "Rusa Deer",
        "Sambar Deer",
        "Axis Deer",
        "Wild Boar",
        "Saltwater Crocodile",
        "Magpie Goose",
        "Eastern Grey Kangaroo",
        "Feral Goat",
        "Red Fox",
        "European Rabbit",
        "Brown Hare",
    },
    17: {  # Sundarpatan
        "Bengal Tiger",
        "Barasingha",
        "Nilgai",
        "Chital",
        "Wild Water Buffalo",
        "Snow Leopard",
        "Blue Sheep",
        "Bar-headed Goose",
    },
}

# -------------------------------------------------------------------------
# GLOBAL SPECIES WEIGHT PROFILES (kg)
# Used for auto-deduction fallback
# -------------------------------------------------------------------------
GLOBAL_SPECIES_PROFILES = {
    "Teal": {"min_w": 0.3, "max_w": 0.6},
    "Mallard": {"min_w": 0.7, "max_w": 2.0},
    "Hazel Grouse": {"min_w": 0.3, "max_w": 0.5},
    "Pheasant": {"min_w": 0.8, "max_w": 2.2},
    "Black Grouse": {"min_w": 0.9, "max_w": 1.7},
    "Capercaillie": {"min_w": 1.5, "max_w": 5.0},
    "European Rabbit": {"min_w": 1.0, "max_w": 2.5},
    "Snowshoe Hare": {"min_w": 1.2, "max_w": 2.2},
    "Scrub Hare": {"min_w": 1.5, "max_w": 4.5},
    "Cackling Goose": {"min_w": 1.5, "max_w": 4.0},
    "Greylag Goose": {"min_w": 2.5, "max_w": 5.5},
    "Turkey": {"min_w": 4.0, "max_w": 11.0},
    "Siberian Musk Deer": {"min_w": 6.0, "max_w": 18.0},
    "Red Fox": {"min_w": 3.0, "max_w": 14.0},
    "Coyote": {"min_w": 7.0, "max_w": 25.0},
    "Eurasian Lynx": {"min_w": 18.0, "max_w": 48.0},
    "Springbok": {"min_w": 25.0, "max_w": 48.0},
    "Roe Deer": {"min_w": 15.0, "max_w": 35.0},
    "Blackbuck": {"min_w": 20.0, "max_w": 55.0},
    "Collared Peccary": {"min_w": 14.0, "max_w": 31.0},
    "Chital": {"min_w": 30.0, "max_w": 85.0},
    "Axis Deer": {"min_w": 30.0, "max_w": 90.0},
    "Iberian Wolf": {"min_w": 25.0, "max_w": 55.0},
    "Gray Wolf": {"min_w": 25.0, "max_w": 60.0},
    "Puma": {"min_w": 35.0, "max_w": 100.0},
    "Ronda Ibex": {"min_w": 30.0, "max_w": 80.0},
    "Southeastern Spanish Ibex": {"min_w": 35.0, "max_w": 90.0},
    "Beceite Ibex": {"min_w": 40.0, "max_w": 105.0},
    "Gredos Ibex": {"min_w": 40.0, "max_w": 105.0},
    "Iberian Mouflon": {"min_w": 35.0, "max_w": 55.0},
    "Bighorn Sheep": {"min_w": 50.0, "max_w": 140.0},
    "Mountain Goat": {"min_w": 45.0, "max_w": 136.0},
    "Wild Boar": {"min_w": 45.0, "max_w": 260.0},
    "Feral Pig": {"min_w": 40.0, "max_w": 210.0},
    "Warthog": {"min_w": 45.0, "max_w": 150.0},
    "Blacktail Deer": {"min_w": 45.0, "max_w": 105.0},
    "Whitetail Deer": {"min_w": 45.0, "max_w": 130.0},
    "Fallow Deer": {"min_w": 40.0, "max_w": 100.0},
    "Bushbuck": {"min_w": 30.0, "max_w": 80.0},
    "Lesser Kudu": {"min_w": 50.0, "max_w": 105.0},
    "Pronghorn": {"min_w": 35.0, "max_w": 65.0},
    "Reindeer": {"min_w": 70.0, "max_w": 190.0},
    "Gemsbok": {"min_w": 180.0, "max_w": 240.0},
    "Lion": {"min_w": 110.0, "max_w": 270.0},
    "Bengal Tiger": {"min_w": 140.0, "max_w": 300.0},
    "Red Deer": {"min_w": 90.0, "max_w": 240.0},
    "Barasingha": {"min_w": 130.0, "max_w": 280.0},
    "Nilgai": {"min_w": 120.0, "max_w": 290.0},
    "Roosevelt Elk": {"min_w": 230.0, "max_w": 500.0},
    "Rocky Mountain Elk": {"min_w": 220.0, "max_w": 480.0},
    "Black Bear": {"min_w": 50.0, "max_w": 290.0},
    "Brown Bear": {"min_w": 190.0, "max_w": 510.0},
    "Grizzly Bear": {"min_w": 180.0, "max_w": 550.0},
    "Moose": {"min_w": 300.0, "max_w": 650.0},
    "Plains Bison": {"min_w": 350.0, "max_w": 1000.0},
    "Cape Buffalo": {"min_w": 400.0, "max_w": 900.0},
    "Water Buffalo": {"min_w": 500.0, "max_w": 1200.0},
}

META_KEYWORDS = {
    "typedefs",
    "name_table",
    "structure",
    "primtype",
    "o:",
    "s:",
    "t:",
    "dt:",
    "dv:",
}


class TokenStream:

  def __init__(self, text: str):
    self.tokens = []
    self.pos = 0
    self._tokenize(text)

  def _tokenize(self, text: str):
    for line in text.splitlines():
      if "#" in line:
        line = line.split("#", 1)[0]
      line = line.strip()
      if not line:
        continue

      parts = re.findall(r"\{|\}|\[|\]|[^ \t\{\}\[\]]+", line)
      for part in parts:
        if part:
          self.tokens.append(part)

  def peek(self):
    return self.tokens[self.pos] if self.pos < len(self.tokens) else None

  def pop(self):
    val = self.peek()
    if val is not None:
      self.pos += 1
    return val

  def has_more(self):
    return self.pos < len(self.tokens)


def skip_metadata_annotations(stream: TokenStream, max_skips=200):
  skips = 0
  while stream.has_more() and skips < max_skips:
    tok = stream.peek()
    if tok is None:
      break
    tok_lower = tok.lower()

    if tok_lower in META_KEYWORDS or tok_lower.startswith("primtype"):
      stream.pop()
      skips += 1
      continue

    if tok_lower == "a":
      saved_pos = stream.pos
      stream.pop()
      if stream.peek() == "[":
        stream.pop()
        inner_skips = 0
        while (
            stream.has_more()
            and stream.peek() != "]"
            and inner_skips < max_skips
        ):
          stream.pop()
          inner_skips += 1
        if stream.peek() == "]":
          stream.pop()
        skips += 1
        continue
      stream.pos = saved_pos

    if re.search(
        r"\b(o:|s:|t:|dt:|dv:|name_table|structure|typedefs)\b",
        tok,
        re.IGNORECASE,
    ):
      stream.pop()
      skips += 1
      continue

    return


def parse_scalar(val: str):
  if val is None:
    return None
  if re.fullmatch(r"[-+]?\d+", val):
    return int(val)
  if re.fullmatch(r"0x[0-9a-fA-F]+", val, re.IGNORECASE):
    return int(val, 16)
  try:
    if re.fullmatch(r"[-+]?\d*\.\d+(?:[eE][-+]?\d+)?", val):
      return float(val)
  except ValueError:
    pass
  return val


def parse_value(stream: TokenStream):
  skip_metadata_annotations(stream)
  tok = stream.peek()

  if tok is None:
    return None
  if tok == "{":
    return parse_object(stream)
  if tok == "[":
    return parse_array(stream)
  if tok.endswith(":"):
    stream.pop()
    return None

  return parse_scalar(stream.pop())


def parse_object(stream: TokenStream) -> dict:
  stream.pop()
  obj = {}

  while stream.has_more():
    skip_metadata_annotations(stream)
    tok = stream.peek()

    if tok is None or tok == "}" or tok == "]":
      if tok == "}":
        stream.pop()
      break

    if tok.endswith(":"):
      key = stream.pop()[:-1]
      val = parse_value(stream)
      obj[key] = val
    elif tok == "{":
      sub_obj = parse_object(stream)
      if "_blocks" not in obj:
        obj["_blocks"] = []
      obj["_blocks"].append(sub_obj)
    else:
      stream.pop()

  return obj


def parse_array(stream: TokenStream) -> list:
  stream.pop()
  arr = []

  while stream.has_more():
    skip_metadata_annotations(stream)
    tok = stream.peek()

    if tok is None or tok == "]" or tok == "}":
      if tok == "]":
        stream.pop()
      break

    pos_before = stream.pos
    val = parse_value(stream)

    if val is not None:
      arr.append(val)
    elif stream.pos == pos_before:
      stream.pop()

  return arr


def resolve_species(val, reserve_id):
  # First resolve generic hashes if valid, then check against reserve whitelist
  whitelist = RESERVE_SPECIES_WHITELIST.get(reserve_id, set())

  # If val matches a known hash mapping, verify it belongs to this reserve
  # (Placeholder logic can be expanded here with your actual verified hash map)
  if isinstance(val, str) and len(val) == 8:
    # If your specific hash maps to a name, check whitelist:
    pass

  return str(val), None


def build_animal_record(raw: dict, context: dict, reserve_id: int) -> dict:
  gender_raw = raw.get("Gender") or raw.get("gender")
  gender_str = None
  if gender_raw is not None:
    if gender_raw == 1:
      gender_str = "Male"
    elif gender_raw == 2:
      gender_str = "Female"
    elif isinstance(gender_raw, str):
      if "1" in gender_raw:
        gender_str = "Male"
      elif "2" in gender_raw:
        gender_str = "Female"

  pos_raw = (
      raw.get("MapPosition")
      or raw.get("Position")
      or raw.get("Pos")
      or raw.get("Location")
      or {}
  )
  pos_x, pos_y = None, None

  if isinstance(pos_raw, dict):
    pos_x = pos_raw.get("X") if pos_raw.get("X") is not None else pos_raw.get("x")
    pos_y = pos_raw.get("Y") if pos_raw.get("Y") is not None else pos_raw.get("y")
  elif isinstance(pos_raw, (list, tuple)) and len(pos_raw) >= 2:
    pos_x = pos_raw[0]
    pos_y = pos_raw[1]

  animal_id = (
      raw.get("Id")
      if raw.get("Id") is not None
      else (
          raw.get("ID")
          if raw.get("ID") is not None
          else raw.get("AnimalId", raw.get("InstanceId", None))
      )
  )

  species = context.get("species")
  whitelist = RESERVE_SPECIES_WHITELIST.get(reserve_id, set())
  if species and species not in whitelist:
    species = None  # Drop misattributed cross-map species

  return {
      "name_hash_id": context.get("name_hash_id"),
      "species": species,
      "spawn_area_id": context.get("spawn_area_id"),
      "need_zone_guids": list(context.get("need_zone_guids", [])),
      "gender": gender_str,
      "weight_kg": raw.get("Weight") or raw.get("weight"),
      "score": raw.get("Score") or raw.get("score"),
      "visual_variation_seed": raw.get("VisualVariationSeed")
      or raw.get("Seed"),
      "animal_id": animal_id,
      "map_position": {"x": pos_x, "y": pos_y},
  }


def extract_animals_from_ast(node, reserve_id, current_context=None):
  if current_context is None:
    current_context = {
        "name_hash_id": None,
        "species": None,
        "spawn_area_id": None,
        "need_zone_guids": [],
    }

  animals = []

  if isinstance(node, dict):
    context = dict(current_context)

    if "NameHashId" in node:
      norm_hash, species_name = resolve_species(node["NameHashId"], reserve_id)
      context["name_hash_id"] = norm_hash
      context["species"] = species_name

    if "SpawnAreadId" in node:
      context["spawn_area_id"] = node["SpawnAreadId"]
    elif "SpawnAreaId" in node:
      context["spawn_area_id"] = node["SpawnAreaId"]

    if "NeedZonePathGuids" in node:
      nz = node["NeedZonePathGuids"]
      if isinstance(nz, list):
        filtered = [v for v in nz if isinstance(v, int) and v >= 100000]
        context["need_zone_guids"] = filtered if filtered else nz
      else:
        context["need_zone_guids"] = [nz]

    if "Animals" in node and isinstance(node["Animals"], list):
      for animal_raw in node["Animals"]:
        if isinstance(animal_raw, dict):
          animals.append(
              build_animal_record(animal_raw, context, reserve_id)
          )

    for k, v in node.items():
      if k != "Animals":
        animals.extend(extract_animals_from_ast(v, reserve_id, context))

  elif isinstance(node, list):
    for item in node:
      animals.extend(extract_animals_from_ast(item, reserve_id, current_context))

  return animals


def _weight_score_for_profile(weight, prof):
  if weight is None:
    return 0.0
  min_w = prof["min_w"]
  max_w = prof["max_w"]
  if min_w <= weight <= max_w:
    return 1.0
  range_width = max(1.0, max_w - min_w)
  if weight < min_w:
    dist = (min_w - weight) / range_width
  else:
    dist = (weight - max_w) / range_width
  return max(0.0, 1.0 - dist)


def _score_boost_from_trophy(trophy_score):
  if trophy_score is None or trophy_score <= 0:
    return 0.0
  if trophy_score < 50:
    return 0.05
  if trophy_score < 100:
    return 0.10
  if trophy_score < 200:
    return 0.18
  return 0.30


def classify_species_by_weight_and_score(
    weight, trophy_score, reserve_id, profiles=GLOBAL_SPECIES_PROFILES
):
  if weight is None and trophy_score is None:
    return None, 0.0

  whitelist = RESERVE_SPECIES_WHITELIST.get(reserve_id, profiles.keys())

  candidates = []
  for sp_name, prof in profiles.items():
    if sp_name not in whitelist:
      continue
    wscore = _weight_score_for_profile(weight, prof)
    boost = _score_boost_from_trophy(trophy_score)
    combined = (0.85 * wscore) + (0.15 * boost)
    candidates.append((sp_name, combined, wscore))

  if not candidates:
    return None, 0.0

  candidates.sort(key=lambda x: x[1], reverse=True)
  best_name, best_conf, best_wscore = candidates[0]

  CONF_THRESHOLD = 0.45
  MIN_WEIGHT_CLOSENESS = 0.25

  if best_conf >= CONF_THRESHOLD and best_wscore >= MIN_WEIGHT_CLOSENESS:
    return best_name, round(best_conf, 3)
  return None, round(best_conf, 3)


def apply_auto_classification(records, reserve_id):
  """Keep unknown species unknown; weight is not a unique species key."""
  for r in records:
    if r.get("species") is None:
      r["species_confidence"] = 0.0
  return 0


def parse_file(path: Path, reserve_id: int):
  with open(path, "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

  stream = TokenStream(text)
  ast_root = []
  while stream.has_more():
    pos_before = stream.pos
    val = parse_value(stream)

    if val is not None:
      ast_root.append(val)
    elif stream.pos == pos_before:
      stream.pop()

  extracted = extract_animals_from_ast(ast_root, reserve_id)
  apply_auto_classification(extracted, reserve_id)
  return extracted


def extract_reserve_id(file_path: Path):
  match = re.search(r"\d+", file_path.stem)
  if match:
    return int(match.group(0))
  return None


if __name__ == "__main__":
  start_time = time.time()
  print("=" * 60, flush=True)
  print(" UNIVERSAL ADF PARSER LOG MONITOR ", flush=True)
  print("=" * 60, flush=True)

  all_files = list(INPUT_DIR.rglob("*.txt"))
  files_to_process = []

  for f in all_files:
    res_id = extract_reserve_id(f)
    if res_id in VALID_RESERVE_IDS:
      files_to_process.append((f, res_id))
    else:
      print(
          f"[Skipped] '{f.name}' (Reserve ID: {res_id} is not valid)",
          flush=True,
      )

  total_files = len(files_to_process)
  print(
      f"\nFound {total_files} valid reserve file(s) to process.\n", flush=True
  )

  if total_files == 0:
    print("[!] No valid reserve .txt files found to process.", flush=True)
    sys.exit(0)

  all_animals = []

  for idx, (file_path, res_id) in enumerate(files_to_process, 1):
    file_start = time.time()
    file_size_kb = file_path.stat().st_size / 1024
    print(
        f"[{idx}/{total_files}] Processing '{file_path.name}'"
        f" (Reserve ID: {res_id}) ({file_size_kb:.1f} KB)...",
        flush=True,
    )

    parsed = parse_file(file_path, res_id)
    all_animals.extend(parsed)

    out_file = OUTPUT_DIR / f"{file_path.stem}_parsed.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
      json.dump(parsed, f, indent=2)

    elapsed = time.time() - file_start
    print(f"    Saved: {out_file.name} (took {elapsed:.2f}s)\n", flush=True)

  summary_file = OUTPUT_DIR / "all_animals.json"
  with open(summary_file, "w", encoding="utf-8") as f:
    json.dump(all_animals, f, indent=2)

  total_elapsed = time.time() - start_time
  print("=" * 60, flush=True)
  print(
      f"COMPLETE! Processed {total_files} files in {total_elapsed:.2f}"
      " seconds.",
      flush=True,
  )
  print(f"Total Animals Extracted : {len(all_animals)}", flush=True)
  print(f"Master file saved at    : {summary_file}", flush=True)
  print("=" * 60, flush=True)