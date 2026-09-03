#!/usr/bin/env python3
r"""Decode a COTW ADF payload and surface any embedded need-zone data.

This script handles both:
- raw ADF files beginning with b' FDA'
- wrapped SAVE/COMP compressed save payloads that contain an ADF blob inside
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import zlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DECA_ROOT = REPO_ROOT / "deca" / "python" / "deca"
for p in [str(DECA_ROOT), str(REPO_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from deca.file import ArchiveFile
from deca.ff_adf import Adf


class SafeVal(dict):
    """Fallback object for DECA dump routines that query arbitrary data."""

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
        return default if default is not None else SafeVal()


class FakeVfs:
    """Minimal VFS stub used for pretty-printing DECA ADF data."""

    def hash_string_match(self, hash32=None, hash48=None, hash64=None):
        return []

    def __getattr__(self, name):
        return lambda *args, **kwargs: SafeVal()


def _align_to_adf_magic(data: bytes) -> bytes | None:
    """Finds the absolute starting index of the ADF header magic."""
    magics = [b" FDA", b"\x00FDA"]
    for magic in magics:
        idx = data.find(magic)
        if idx >= 0:
            return data[idx:]
    return None


def normalize_adf_bytes(raw: bytes) -> bytes | None:
    """Return an ADF payload extracted from either a raw ADF or a SAVE container."""
    if not raw:
        return None

    # Step 1: Check if raw uncompressed data already has ADF magic
    direct_adf = _align_to_adf_magic(raw)
    if direct_adf:
        return direct_adf

    # Step 2: Handle SAVE/COMP container decompression
    decompressed_payload = None
    if raw.startswith(b"SAVE") and len(raw) >= 32:
        payload = raw[32:]

        # Try standard zlib decompression variants
        for kwargs in ({}, {"wbits": -zlib.MAX_WBITS}):
            try:
                cobj = zlib.decompressobj(**kwargs)
                out = cobj.decompress(payload)
                if out:
                    decompressed_payload = out
                    break
            except Exception:
                pass

        # Try locating zlib stream signature inside the header payload
        if not decompressed_payload:
            for off in range(0, min(len(payload), 4096)):
                if payload[off] == 0x78 and off + 1 < len(payload) and payload[off + 1] in (0x01, 0x5E, 0x9C, 0xDA):
                    try:
                        out = zlib.decompress(payload[off:])
                        if out:
                            decompressed_payload = out
                            break
                    except Exception:
                        continue

    # Step 3: Align decompressed output directly to the ADF magic offset
    if decompressed_payload:
        return _align_to_adf_magic(decompressed_payload)

    return None


def decode_adf_blob(adf_bytes: bytes) -> str:
    """Use DECA's ADF parser to turn raw ADF bytes into readable text."""
    with ArchiveFile(io.BytesIO(adf_bytes)) as af:
        adf = Adf()
        adf.deserialize(af)
        return adf.dump_to_string(FakeVfs())


def extract_need_zone_values(text: str) -> list[str]:
    """Try to locate need-zone GUID values in the ADF dump text."""
    results: list[str] = []

    for m in re.finditer(r"NeedZone(?:Path)?Guids|need_zone_guids|need_zone_guid", text, flags=re.IGNORECASE):
        start = max(0, m.start() - 200)
        end = min(len(text), m.end() + 500)
        window = text[start:end]
        vals = re.findall(r"0x[0-9A-Fa-f]+|\b\d{5,}\b", window)
        for val in vals:
            if val not in results:
                results.append(val)

    for val in re.findall(r"\b[0-9a-fA-F]{8,}\b", text):
        if len(val) >= 8 and val not in results:
            results.append(val)

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Decode COTW need-zone ADF files.")
    parser.add_argument(
        "--input",
        default=r"C:\Users\gills\OneDrive\Documents\Avalanche Studios\Microsoft Store\COTW\Saves\2535433028166168\found_need_zones_adf",
        help="Path to the ADF file or SAVE container to decode.",
    )
    parser.add_argument(
        "--output",
        default=r"C:\Users\gills\JaimieProjects\PythonProjects\COTWTrackerWorking\DecodedNeedZoneData",
        help="Directory for decoded output text files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    src = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        raise FileNotFoundError(f"Input file does not exist: {src}")

    raw = src.read_bytes()
    print(f"[INFO] File: {src}")
    print(f"[INFO] Size: {len(raw)} bytes")
    print(f"[INFO] Header: {raw[:32].hex()}")

    adf_bytes = normalize_adf_bytes(raw)
    if adf_bytes is None:
        raise ValueError(f"No ADF payload found in {src}")

    print(f"[INFO] Aligned ADF payload starts with: {adf_bytes[:16].hex()}")
    print(f"[INFO] Aligned ADF payload size: {len(adf_bytes)} bytes")

    decoded = decode_adf_blob(adf_bytes)

    out_file = out_dir / f"{src.stem}_decoded.txt"
    out_file.write_text(decoded, encoding="utf-8", errors="replace")
    print(f"[OK] Wrote readable decode to: {out_file}")

    zone_values = extract_need_zone_values(decoded)
    if zone_values:
        print(f"[INFO] Possible need-zone values found: {zone_values[:50]}")
        if len(zone_values) > 50:
            print(f"[INFO] ... plus {len(zone_values) - 50} more values")
    else:
        print("[INFO] No need-zone values were detected in the decoded text.")

    summary = {
        "source_file": str(src),
        "payload_size": len(adf_bytes),
        "possible_need_zone_values": zone_values,
    }
    json_file = out_dir / f"{src.stem}_summary.json"
    json_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[OK] Wrote JSON summary to: {json_file}")


if __name__ == "__main__":
    main()