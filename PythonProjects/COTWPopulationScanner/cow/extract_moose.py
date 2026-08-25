import json
from pathlib import Path

BASE_DIR = Path(r"C:\Users\gills\cow")
INPUT_FILE = BASE_DIR / "all_extracted_animals.json"

if not INPUT_FILE.exists():
    print(f"Error: {INPUT_FILE} does not exist.")
    exit(1)

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    animals = json.load(f)

# Group animals by their parent/species container
groups = {}
for anim in animals:
    # Fallback keys to ensure we capture the group ID
    gid = anim.get("NameHashId", anim.get("Group_ID", "Unknown"))
    if gid not in groups:
        groups[gid] = []
    groups[gid].append(anim)

print("==================================================")
print("      SPECIES WEIGHT ANALYSIS (FIND MOOSE)        ")
print("==================================================\n")

moose_hash = None

for gid, group in groups.items():
    weights = [a.get("Weight", 0.0) for a in group if "Weight" in a]
    if weights:
        min_w, max_w = min(weights), max(weights)
        avg_w = sum(weights) / len(weights)
        print(
            f"Hash ID: {str(gid):<12} | Count: {len(group):<4} | "
            f"Weight Range: {min_w:.1f}kg - {max_w:.1f}kg (Avg: {avg_w:.1f}kg)"
        )

        # Moose have an average weight over 350 kg and max > 500 kg
        if avg_w > 300 or max_w > 500:
            moose_hash = gid

if moose_hash is not None:
    moose_list = groups[moose_hash]
    print(f"\n[+] Matched Moose Population under Hash ID: {moose_hash}")
    print(f"[+] Total Moose found: {len(moose_list)}")

    out_file = BASE_DIR / "moose_only.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(moose_list, f, indent=2)

    print(f"[+] Full Moose population saved to: {out_file}\n")

    if moose_list:
        print("--- SAMPLE MOOSE ENTRY ---")
        print(json.dumps(moose_list[0], indent=2))
else:
    print(
        "\n[-] Could not auto-detect Moose by weight. "
        "Check all_extracted_animals.json field names."
    )