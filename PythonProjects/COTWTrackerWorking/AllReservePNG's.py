import io
from pathlib import Path
import urllib.request
from PIL import Image

MAP_CACHE_DIR = Path(r"C:\Users\gills\JaimieProjects\PythonProjects\COTWTrackerWorking\map_cache")


def _load_full_map_image(reserve_id):
    # Ensure the cache directory exists before saving files to it
    MAP_CACHE_DIR.mkdir(parents=True, exist_ok=True)

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


if __name__ == "__main__":
    _load_full_map_image(21)