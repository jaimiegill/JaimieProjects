#!/usr/bin/env python3
"""Decode COTW animal population save files using zlib.decompressobj and DECA ADF parsing."""

from __future__ import annotations

import argparse
import io
import sys
import zlib
from pathlib import Path

# Set up pathing to locate DECA modules
REPO_ROOT = Path(__file__).resolve().parent
DECA_ROOT = REPO_ROOT / "python" / "deca"
if str(DECA_ROOT) not in sys.path:
    sys.path.insert(0, str(DECA_ROOT))

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from deca.file import ArchiveFile
from deca.ff_adf import Adf


class SafeVal(dict):
    """Recursive mock dictionary/value to prevent indexing errors during DECA VFS string dumps."""
    def __getitem__(self, key):
        return SafeVal()

    def __getattr__(self, name):
        return SafeVal()

    def __call__(self, *args, **kwargs):
        return SafeVal()

    def __str__(self):
        return ""

    def __repr__(self):
        return ""

    def __bool__(self):
        return True

    def __iter__(self):
        return iter([])

    def __len__(self):
        return 0

    def get(self, key, default=None):
        if default is not None:
            return default
        return SafeVal()


class FakeVfs:
    """Mock VFS object that safely handles arbitrary lookup queries from DECA."""
    def hash_string_match(self, hash32=None, hash48=None, hash64=None):
        return []

    def __getattr__(self, name):
        return lambda *args, **kwargs: SafeVal()


def decompress_save_payload(raw: bytes) -> bytes | None:
    """Decompress SAVE container data starting at offset 32 (0x20)."""
    if len(raw) < 32 or not raw.startswith(b"SAVE"):
        return None

    payload = raw[32:]

    # Primary Attempt: Standard zlib stream via decompressobj
    try:
        dobj = zlib.decompressobj()
        decompressed = dobj.decompress(payload)
        if decompressed:
            return decompressed
    except Exception:
        pass

    # Fallback: Raw Inflate
    try:
        dobj = zlib.decompressobj(-zlib.MAX_WBITS)
        decompressed = dobj.decompress(payload)
        if decompressed:
            return decompressed
    except Exception:
        pass

    return None


def decode_file_to_texts(input_path: Path, output_dir: Path) -> list[str]:
    raw = input_path.read_bytes()
    produced = []

    decompressed = decompress_save_payload(raw) if raw.startswith(b"SAVE") else raw

    if not decompressed:
        return produced

    adf_idx = decompressed.find(b" FDA")
    if adf_idx == -1:
        adf_idx = decompressed.find(b"FDA")
        if adf_idx != -1:
            adf_idx = max(0, adf_idx - 1)

    if adf_idx == -1:
        return produced

    adf_bytes = decompressed[adf_idx:]

    try:
        with ArchiveFile(io.BytesIO(adf_bytes)) as af:
            adf = Adf()
            adf.deserialize(af)
            text = adf.dump_to_string(FakeVfs())

        out_path = output_dir / f"{input_path.stem}_decoded.txt"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8", errors="replace")
        produced.append(str(out_path))
    except Exception as exc:
        print(f"  [ADF Parse Error] {input_path.name}: {exc}")

    return produced


def main() -> None:
    parser = argparse.ArgumentParser(description="Decode COTW animal population save files.")
    parser.add_argument(
        "--input-dir",
        default=r"C:\Users\gills\OneDrive\Documents\Avalanche Studios\Microsoft Store\COTW\Saves\2535433028166168",
        help="Directory containing the animal population files.",
    )
    parser.add_argument(
        "--output-dir",
        default=r"C:\Users\gills\JaimieProjects\PythonProjects\COTWTrackerWorking\DecodedBinariesADFFormat",
        help="Directory where decoded text dumps will be written.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    input_dir = Path(args.input_dir)
    found_files = 0
    found_outputs = 0
    skipped = 0

    for src_path in sorted(input_dir.rglob("*")):
        if not src_path.is_file() or "animal_population" not in src_path.name.lower():
            continue

        rel_dir = src_path.parent.relative_to(input_dir) if src_path.is_relative_to(input_dir) else Path(".")
        target_dir = output_dir / rel_dir
        outputs = decode_file_to_texts(src_path, target_dir)
        found_files += 1
        found_outputs += len(outputs)

        if outputs:
            for out in outputs:
                print(f"Decoded: {src_path.name} -> {out}")
        else:
            skipped += 1
            print(f"Skipped: {src_path.name}")

    print(f"\nFinished. Files scanned: {found_files}. Decoded payloads: {found_outputs}. Skipped: {skipped}.")


if __name__ == "__main__":
    main()