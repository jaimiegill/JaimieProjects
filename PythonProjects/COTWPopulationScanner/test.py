import os
import struct
import zlib

WORKING_DIR = r"C:\Users\gills\cow"
INPUT_FILE = os.path.join(WORKING_DIR, "animal_population_2")
OUTPUT_FILE = os.path.join(WORKING_DIR, "medved_moose_zones_parsed.txt")


def load_payload():
    if not os.path.exists(INPUT_FILE):
        print(f"[-] File not found: {INPUT_FILE}")
        return None

    with open(INPUT_FILE, "rb") as f:
        data = f.read()

    # Decompress zlib payload
    decompressed = bytearray()
    offset = 0
    while offset < len(data) - 2:
        if data[offset : offset + 2] in (b"\x78\x01", b"\x78\x9c", b"\x78\xda"):
            try:
                dobj = zlib.decompressobj()
                chunk = dobj.decompress(data[offset:])
                decompressed.extend(chunk)
                consumed = len(data[offset:]) - len(dobj.unconsumed_tail)
                offset += max(consumed, 1)
                continue
            except zlib.error:
                pass
        offset += 1

    payload = bytes(decompressed) if decompressed else data
    return payload


def extract_species_zones():
    payload = load_payload()
    if not payload:
        return

    print(f"[+] Processing Medved ADF payload ({len(payload):,} bytes)...")

    # Locate species data block markers (AnimalPopulationData_8)
    marker = b"AnimalPopulationData_8"
    block_offsets = [m.start() for m in re.finditer(marker, payload)]

    if not block_offsets:
        # Fallback: scan full payload if string markers are indexed in string table
        block_offsets = [0]

    print(
        f"[+] Identified {len(block_offsets)} species data blocks in ADF structure."
    )

    all_species_zones = []

    # Scan each species payload block for map coordinates
    for i, start_off in enumerate(block_offsets):
        end_off = (
            block_offsets[i + 1] if i + 1 < len(block_offsets) else len(payload)
        )
        block_data = payload[start_off:end_off]

        zones_in_block = []
        seen = set()

        # Step through block data searching for valid Medved coordinate floats
        for ptr in range(0, len(block_data) - 12, 4):
            try:
                x, y, z = struct.unpack("<fff", block_data[ptr : ptr + 12])

                # Medved map boundary: X and Z in [-4000, 4000], Y elevation in [-50, 500]
                if (
                    (-4000.0 <= x <= 4000.0)
                    and (-50.0 <= y <= 500.0)
                    and (-4000.0 <= z <= 4000.0)
                ):
                    # Filter out origin defaults, tiny values, and scale floats
                    if abs(x) > 100.0 and abs(z) > 100.0:
                        key = (round(x, 1), round(z, 1))
                        if key not in seen:
                            seen.add(key)
                            abs_offset = start_off + ptr
                            zones_in_block.append(
                                (
                                    abs_offset,
                                    round(x, 2),
                                    round(y, 2),
                                    round(z, 2),
                                )
                            )
            except struct.error:
                continue

        if zones_in_block:
            all_species_zones.append((i + 1, zones_in_block))

    total_extracted = sum(len(zones) for _, zones in all_species_zones)
    print(
        f"[+] Extracted {total_extracted} total coordinates across all species blocks!"
    )

    # Export coordinates organized by species block
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write(
            f"MEDVED-TAIGA SPECIES NEED ZONES ({total_extracted} Total Coordinates)\n"
        )
        out.write("=" * 70 + "\n\n")

        for species_idx, zones in all_species_zones:
            out.write(
                f"--- Species Block #{species_idx:02d} ({len(zones)} Need Zones) ---\n"
            )
            for off, x, y, z in zones:
                out.write(
                    f"  Offset: 0x{off:06X} | X: {x:8.2f} | Y (Elev): {y:6.2f} | Z: {z:8.2f}\n"
                )
            out.write("\n")

    print(f"[+] Complete breakdown exported to: {OUTPUT_FILE}")


if __name__ == "__main__":
    import re

    extract_species_zones()