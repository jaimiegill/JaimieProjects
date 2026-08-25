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

with open(POP_FILE, "rb") as f:
    raw_bytes = f.read()

decompressed = zlib.decompress(
    raw_bytes[32:] if raw_bytes.startswith(b"SAVE") else raw_bytes
)
stream = ArchiveFile(io.BytesIO(decompressed[5:]))
adf = Adf()
adf.deserialize(stream)

root = adf.table_instance_values[0]

print("==================================================")
print("          COORDINATE LOCATION DIAGNOSTIC          ")
print("==================================================\n")

# Check root keys
print("Root Keys in ADF:", list(root.keys()))

# Check non-zero animal coordinates count
pops = root.get("Populations", [])
total_animals = 0
nonzero_anim_coords = 0
group_keys_with_pos = set()

for pop in pops:
    for g in pop.get("Groups", []):
        # Inspect group keys for coordinate fields
        for k in g.keys():
            if "pos" in k.lower() or "coord" in k.lower() or "area" in k.lower() or "zone" in k.lower():
                group_keys_with_pos.add(k)

        for anim in g.get("Animals", []):
            total_animals += 1
            pos = anim.get("MapPosition", {})
            if isinstance(pos, dict):
                x = pos.get("X", 0.0)
                y = pos.get("Y", 0.0)
                if x != 0.0 or y != 0.0:
                    nonzero_anim_coords += 1

print(f"Total Animals Scanned: {total_animals}")
print(f"Animals with Non-Zero MapPosition: {nonzero_anim_coords}")
print(f"Group-level Location Keys Found: {list(group_keys_with_pos)}\n")

# Sample Group Structure
if pops and pops[0].get("Groups"):
    sample_group = pops[0]["Groups"][0]
    print("--- Sample Group Keys & Values (Excluding Animals list) ---")
    for k, v in sample_group.items():
        if k != "Animals":
            print(f"  {k}: {v}")