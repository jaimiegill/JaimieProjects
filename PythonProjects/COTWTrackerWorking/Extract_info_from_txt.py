import re
from pathlib import Path

# Set your decoder text file directory and output target
INPUT_DIR = Path("./decoded_files")
OUTPUT_DIR = Path("./Results_table")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_all_fields(file_path):
    """Scans the decoded text file and extracts every single key-value field across all records without dropping or filtering data."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Split into entries separated by blank lines
    blocks = [b.strip() for b in re.split(r"\n\s*\n+", content) if b.strip()]

    records = []
    all_headers = []

    for block in blocks:
        record = {}
        lines = block.splitlines()

        for line in lines:
            # Matches key-value delimiters like 'key: value' or 'key = value'
            if ":" in line or "=" in line:
                delimiter = ":" if ":" in line else "="
                parts = line.split(delimiter, 1)
                key = parts[0].strip()
                value = parts[1].strip()

                record[key] = value
                if key not in all_headers:
                    all_headers.append(key)

        if record:
            records.append(record)

    return records, all_headers


def build_unfiltered_table(records, headers, filename):
    """Generates a text table containing all discovered headers and records, dynamically sizing every column."""
    if not records or not headers:
        return f"=== No key-value pairs extracted from {filename} ==="

    # Determine maximum width for each column to align headers and values
    col_widths = {h: len(h) for h in headers}
    for rec in records:
        for h in headers:
            val_len = len(str(rec.get(h, "")))
            if val_len > col_widths[h]:
                col_widths[h] = val_len

    # Format table headers and divider
    header_row = " | ".join(f"{h:<{col_widths[h]}}" for h in headers)
    divider = "-+-".join("-" * col_widths[h] for h in headers)

    # Format data rows (places empty string/blank if a field is missing in a specific record)
    data_rows = []
    for rec in records:
        row = " | ".join(
            f"{str(rec.get(h, '')):<{col_widths[h]}}" for h in headers
        )
        data_rows.append(row)

    file_header = f"=== Complete Unfiltered Table: {filename} ===\nTotal Fields: {len(headers)} | Total Records: {len(records)}\n"
    return "\n".join([file_header, header_row, divider, *data_rows])


def batch_export():
    txt_files = list(INPUT_DIR.glob("*.txt"))

    if not txt_files:
        print(f"No .txt files found in {INPUT_DIR.resolve()}")
        return

    for txt_file in txt_files:
        records, headers = parse_all_fields(txt_file)

        if not records:
            print(f"Skipped {txt_file.name}: No parseable key-value structures.")
            continue

        table_content = build_unfiltered_table(records, headers, txt_file.name)
        output_file = OUTPUT_DIR / f"{txt_file.stem}_full_table.txt"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(table_content)

        print(
            f"Processed: {txt_file.name} -> {output_file.name} [{len(headers)} columns]"
        )


if __name__ == "__main__":
    batch_export()