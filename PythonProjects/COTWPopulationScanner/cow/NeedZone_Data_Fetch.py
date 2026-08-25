import os
import struct
import zlib

# Change 'animal_population_0' to match your reserve file
# (0 = Layton Lake, 2 = Medved, 6 = Yukon, 11 = Revontuli)
POP_FILE_PATH = r"C:\Users\gills\cow\animal_population_2"


def parse_population_file(path):
    if not os.path.exists(path):
        print(f"[-] Error: Population file not found at '{path}'")
        return

    with open(path, "rb") as f:
        raw_data = f.read()

    print(f"[+] Loaded raw file: {len(raw_data)} bytes")

    # Locate zlib header magic bytes (0x7801, 0x789C, 0x78DA)
    zlib_offset = -1
    for i in range(len(raw_data) - 2):
        if raw_data[i : i + 2] in (b"\x78\x01", b"\x78\x9c", b"\x78\xda"):
            zlib_offset = i
            break

    if zlib_offset == -1:
        print("[-] Could not locate zlib stream header in population file.")
        return

    print(
        f"[+] Located compressed zlib payload at byte offset 0x{zlib_offset:02X}"
    )

    try:
        decompressed_data = zlib.decompress(raw_data[zlib_offset:])
        print(
            f"[+] Successfully decompressed payload: {len(decompressed_data)} bytes!"
        )
    except zlib.error as e:
        print(f"[-] Decompression failed: {e}")
        return

    # Extract 3D Need Zone / Animal Node coordinates from decompressed memory
    unique_coords = set()
    for offset in range(0, len(decompressed_data) - 12, 4):
        try:
            x, y, z = struct.unpack(
                "<fff", decompressed_data[offset : offset + 12]
            )

            # Filter for valid map bounds (X/Z between -11500 and 11500, Y elevation > 0)
            if (
                (-11500.0 <= x <= 11500.0)
                and (0.0 <= y <= 1000.0)
                and (-11500.0 <= z <= 11500.0)
            ):
                if abs(x) > 50.0 and abs(z) > 50.0:
                    unique_coords.add((round(x, 2), round(y, 2), round(z, 2)))
        except struct.error:
            continue

    print(
        f"\n[+] Successfully extracted {len(unique_coords)} valid need zone/animal coordinates!"
    )

    # Save decompressed raw binary for deep inspection if needed
    decompressed_path = path + "_decompressed.bin"
    with open(decompressed_path, "wb") as out:
        out.write(decompressed_data)
    print(f"[+] Dumped uncompressed binary payload to: {decompressed_path}")


if __name__ == "__main__":
    parse_population_file(POP_FILE_PATH)