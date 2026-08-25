import io
import json
import zlib
from collections import defaultdict
from pathlib import Path
import matplotlib.pyplot as plt
from PIL import Image

BASE_DIR_DATA = Path(r"C:\Users\gills\cow\data")

BASE_DIR = Path(r"C:\Users\gills\cow")
JSON_FILE = BASE_DIR_DATA / "moose_all_binary_keys.json"
ADF_FILE = BASE_DIR_DATA / "found_need_zones_adf"
MAP_IMAGE_FILE = BASE_DIR / "Medved-Taiga.jpg"

# --- MANUAL MAP ALIGNMENT & SCALING CONTROLS ---
# Full 10,000 unit world scale centered at -7500, -7500 for Medved-Taiga:
MAP_CENTER_X = -8000.0   # Center X-coordinate of the reserve
MAP_CENTER_Z = -7250.0   # Center Z-coordinate of the reserve
MAP_WIDTH = 4000.0      # Full 10km map width in game world units
ZOOM_PADDING = 500       # Margin around active data clusters
# ------------------------------------------------

from deca.ff_adf import Adf
from deca.file import ArchiveFile

def load_adf_file(file_path):
    if not file_path.exists():
        return None
    try:
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
        decompressed = zlib.decompress(raw_bytes[32:] if raw_bytes.startswith(b"SAVE") else raw_bytes)
        stream = ArchiveFile(io.BytesIO(decompressed[5:]))
        adf = Adf()
        adf.deserialize(stream)
        return adf
    except Exception as e:
        return None

def parse_position(pos):
    if pos is None: return None
    x, z = 0.0, 0.0
    if isinstance(pos, (list, tuple)) and len(pos) >= 3:
        x = float(pos[0])
        z = float(pos[2])  
    elif isinstance(pos, dict):
        x = float(pos.get("X", pos.get("x", 0.0)))
        z = float(pos.get("Z", pos.get("z", 0.0)))
    if x != 0.0 or z != 0.0:
        return round(x, 2), round(z, 2)
    return None

def parse_level(lvl_val):
    try:
        return float(lvl_val)
    except (ValueError, TypeError):
        return 0.0

def plot_medved_zones():
    if not ADF_FILE.exists():
        print(f"[-] Could not find {ADF_FILE}")
        return

    # 1. Group all moose records by coordinate location
    coord_map = defaultdict(list)
    
    if JSON_FILE.exists():
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            formatted_moose = json.load(f)
            
        for m in formatted_moose:
            is_diamond = m.get("IsDiamond") == "YES" or m.get("IsDiamond") is True
            rank = m.get("Rank", "?")
            score = m.get("Score", "?")
            level = m.get("Level", "?")
            gender = m.get("Gender", m.get("Sex", "?"))
            
            moose_info = {
                "is_diamond": is_diamond,
                "rank": rank,
                "score": score,
                "level": level,
                "gender": gender
            }
            
            entry_coords = []
            for coord_str in m.get("AllHerdCoordsList", []):
                if isinstance(coord_str, str) and "(" in coord_str and ")" in coord_str:
                    try:
                        inner = coord_str.split("(")[1].split(")")[0]
                        parts = inner.split(",")
                        entry_coords.append((float(parts[0]), float(parts[1])))
                    except:
                        pass
                        
            for k in ["Coords", "Position", "DrinkCoords", "ZoneCoords"]:
                if k in m:
                    p = parse_position(m[k])
                    if p:
                        entry_coords.append(p)
                        
            if not entry_coords and ("X" in m or "x" in m):
                mx = float(m.get("X", m.get("x", 0.0)))
                mz = float(m.get("Z", m.get("z", 0.0)))
                if mx != 0 or mz != 0:
                    entry_coords.append((mx, mz))

            for mx, mz in entry_coords:
                key = (round(mx, 1), round(mz, 1))
                coord_map[key].append(moose_info)

    reg_x, reg_y = [], []
    pink_x, pink_y = [], []
    diam_x, diam_y = [], []

    # 2. Load ADF and locate need zones
    adf = load_adf_file(ADF_FILE)
    reserve_zones = []
    
    if adf and adf.table_instance_values:
        root_node = adf.table_instance_values[0]
        for reserve in root_node.get("NZData", []):
            candidate_zones = []
            for zone in reserve.get("NeedZoneData", []):
                pos = parse_position(zone.get("Position"))
                if pos:
                    candidate_zones.append(pos)
            
            if candidate_zones and coord_map:
                candidate_zones = candidate_zones
                break

    fig, ax = plt.subplots(figsize=(14, 14))

    # Calculate exact bounding box for map rendering
    half_w = MAP_WIDTH / 2.0
    img_min_x = MAP_CENTER_X - half_w
    img_max_x = MAP_CENTER_X + half_w
    img_min_z = MAP_CENTER_Z - half_w
    img_max_z = MAP_CENTER_Z + half_w

   # Load and render background image
    if MAP_IMAGE_FILE.exists():
        try:
            img = Image.open(MAP_IMAGE_FILE)
            
            # --- ROTATE MAP TO MATCH IN-GAME ORIENTATION ---
            # Rotates the map image counter-clockwise so features line up correctly
            # -----------------------------------------------

            # Matplotlib extent: [left, right, bottom, top]
            # Inverting Z axis range ensures North (+Z) is at the top
            extent = [img_min_x, img_max_x, img_max_z, img_min_z]
            ax.imshow(img, extent=extent, alpha=0.85, zorder=0)
        except Exception as e:
            print(f"[-] Error loading background image: {e}")

    # Plot ADF discovered zones
    r_xs, r_zs = [], []
    if reserve_zones:
        r_xs = [c[0] for c in reserve_zones]
        r_zs = [c[1] for c in reserve_zones]
        ax.scatter(r_xs, r_zs, c='cornflowerblue', alpha=0.4, s=50, edgecolors='navy', linewidths=0.5, zorder=2, label='Discovered Need Zones')

    all_x, all_z = list(r_xs), list(r_zs)

    # 3. Render markers and text labels
    for (mx, mz), moose_list in coord_map.items():
        has_diamond = any(item["is_diamond"] for item in moose_list)
        has_high_level = any(
            parse_level(item["level"]) >= 3 and str(item["gender"]).lower() == "male"
            for item in moose_list
        )
        
        all_x.append(mx)
        all_z.append(mz)

        lines = [f"Herd ({len(moose_list)} moose):"]
        for idx, item in enumerate(moose_list, 1):
            d_tag = "💎 " if item["is_diamond"] else ""
            lines.append(f"{idx}. {d_tag}R{item['rank']} | Sc:{item['score']} | L:{item['level']} | {item['gender']}")
        full_text = "\n".join(lines)

        if has_diamond:
            diam_x.append(mx)
            diam_y.append(mz)
            ax.annotate(full_text, (mx, mz), textcoords="offset points", xytext=(0, 12),
                        ha='center', fontsize=7, fontweight='bold', zorder=6,
                        bbox=dict(boxstyle="round,pad=0.4", fc="yellow", alpha=0.9, edgecolor="red"))
        elif has_high_level:
            pink_x.append(mx)
            pink_y.append(mz)
            ax.annotate(full_text, (mx, mz), textcoords="offset points", xytext=(0, 10),
                        ha='center', fontsize=6.5, fontweight='bold', zorder=5,
                        bbox=dict(boxstyle="round,pad=0.35", fc="hotpink", alpha=0.9, edgecolor="deeppink"))
        else:
            reg_x.append(mx)
            reg_y.append(mz)
            ax.annotate(full_text, (mx, mz), textcoords="offset points", xytext=(0, 8),
                        ha='center', fontsize=6, zorder=4,
                        bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8, edgecolor="gray"))

    # Scatter points
    if reg_x:
        ax.scatter(reg_x, reg_y, c='dodgerblue', alpha=0.8, s=50, edgecolors='navy', linewidths=0.5, zorder=3, label='Moose Herds')
    if pink_x:
        ax.scatter(pink_x, pink_y, c='deeppink', alpha=0.95, s=80, edgecolors='darkmagenta', linewidths=0.8, zorder=4, label='High-Level Herds (L3+)')
    if diam_x:
        ax.scatter(diam_x, diam_y, c='gold', edgecolors='red', s=200, marker='*', zorder=5, label='Diamond Moose Herds 💎')

    # Dynamic Zoom focused strictly on the active data cluster
    if all_x and all_z:
        min_x, max_x = min(all_x), max(all_x)
        min_z, max_z = min(all_z), max(all_z)
        
        ax.set_xlim(min_x - ZOOM_PADDING, max_x + ZOOM_PADDING)
        # Note: Inverted Y limits maintain correct top-down map orientation
        ax.set_ylim(max_z + ZOOM_PADDING, min_z - ZOOM_PADDING)

    ax.set_title("Medved-Taiga Reserve: Complete Herd Details Map", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("X Coordinate (West <---> East)", fontsize=11)
    ax.set_ylabel("Z Coordinate (North <---> South)", fontsize=11)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc='upper right', framealpha=0.9)

    print("[+] Map loaded with updated coordinate alignment controls.")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    plot_medved_zones()