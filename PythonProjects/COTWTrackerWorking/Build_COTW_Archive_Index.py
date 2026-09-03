"""Build the DECA index for the installed COTW ARC/TAB archives."""

from __future__ import annotations

import json
import os
from pathlib import Path

from deca.db_processor import vfs_structure_prep


GAME_ROOT = Path(r"E:\XboxGames\theHunter- Call of the Wild - Windows 10")
GAME_EXE = GAME_ROOT / "Content" / "theHunterCotW_F.exe"
INDEX_ROOT = Path(
    os.environ.get("COTW_STATIC_INDEX", r"E:\COTWTrackerCache")
)
PROJECT_FILE = INDEX_ROOT / "project.json"
CORE_DB = INDEX_ROOT / "db" / "core.db"
COMPLETE_MARKER = INDEX_ROOT / "index_complete.marker"


def main() -> int:
    if not GAME_EXE.is_file():
        print(f"[ERROR] COTW executable not found: {GAME_EXE}", flush=True)
        return 1

    if COMPLETE_MARKER.is_file() and CORE_DB.is_file() and CORE_DB.stat().st_size > 0:
        print(f"[OK] Static archive index already exists: {CORE_DB}", flush=True)
        return 0

    INDEX_ROOT.mkdir(parents=True, exist_ok=True)
    PROJECT_FILE.write_text(
        json.dumps(
            {
                "game_dir": str(GAME_EXE.parent),
                "exe_name": GAME_EXE.name,
                "game_id": "hp",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[INFO] Indexing COTW archives from {GAME_ROOT / 'Content'}", flush=True)
    vfs = vfs_structure_prep(
        str(PROJECT_FILE),
        str(INDEX_ROOT) + "\\",
    )
    if vfs is None:
        print("[ERROR] DECA could not identify the COTW installation.", flush=True)
        return 1

    vfs.shutdown()
    if not CORE_DB.exists() or CORE_DB.stat().st_size == 0:
        print("[ERROR] Archive indexing did not create a database.", flush=True)
        return 1

    COMPLETE_MARKER.write_text("Archive index completed successfully.\n", encoding="utf-8")
    print(f"[OK] Static archive index created: {CORE_DB}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())