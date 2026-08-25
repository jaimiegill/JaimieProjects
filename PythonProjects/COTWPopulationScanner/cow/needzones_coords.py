import io
import sys
import zlib
from pathlib import Path

BASE_DIR = Path(r"C:\Users\gills\cow")
sys.path.insert(0, str(BASE_DIR))
from deca.ff_adf import Adf
from deca.file import ArchiveFile


def load_adf(path):
    with open(path, "rb") as f:
        b = f.read()
    decomp = zlib.decompress(b[32:] if b.startswith(b"SAVE") else b)
    stream = ArchiveFile(io.BytesIO(decomp[5:]))
    adf = Adf()
    adf.deserialize(stream)
    return adf


# Find and load files
zone_path = next(BASE_DIR.glob("*found_need_zones*"), BASE_DIR / "found_need_zones_adf")
pop_path = BASE_DIR / "animal_population_2"

zone_adf = load_adf(zone_path)
pop_adf = load_adf(pop_path)

zones = zone_adf.table_instance_values[0].get("NeedZones", zone_adf.table_instance_values[0].get("DiscoveredNeedZones", []))
pops = pop_adf.table_instance_values[0].get("Populations", [])

print(f"--- DIAGNOSTIC ---")
print(f"Zone file total entries: {len(zones)}")
if zones:
    print(f"Sample zone item keys: {list(zones[0].keys())}")
    print(f"Sample zone raw Guid value: {repr(zones[0].get('Guid', zones[0].get('PathGuid')))} (Type: {type(zones[0].get('Guid', zones[0].get('PathGuid')))})")

for p in pops:
    groups = p.get("Groups", [])
    if groups and "NeedZonePathGuids" in groups[0]:
        sample_pg = groups[0]["NeedZonePathGuids"][0]
        print(f"Sample Pop NeedZonePathGuids value: {repr(sample_pg)} (Type: {type(sample_pg)})")
        break