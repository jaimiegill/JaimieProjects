import io
import json
import zlib
from pathlib import Path

# Paths configuration
BASE_DIR = Path(r"C:\Users\gills\cow\data")
TABLE_DIR = BASE_DIR / "table_dumps"
TABLE_DIR.mkdir(exist_ok=True)

# Import deca libraries for COTW binary parsing
from deca.ff_adf import Adf
from deca.file import ArchiveFile

def parse_adf_file(file_path):
    """Unpacks and deserializes COTW binary ADF save files."""
    with open(file_path, "rb") as f:
        raw_bytes = f.read()
    
    if len(raw_bytes) == 0:
        return None

    try:
        decompressed = zlib.decompress(raw_bytes[32:]) if raw_bytes.startswith(b"SAVE") else zlib.decompress(raw_bytes)
        stream = ArchiveFile(io.BytesIO(decompressed[5:]))
        adf = Adf()
        adf.deserialize(stream)
        if hasattr(adf, "table_instance_values") and adf.table_instance_values:
            return adf.table_instance_values
    except Exception:
        pass
    return None

def format_dict_list_as_table(data_list):
    """Converts a list of dictionaries into a neat aligned text table format."""
    if not isinstance(data_list, list) or not data_list:
        return str(data_list)
    
    dicts = [item for item in data_list if isinstance(item, dict)]
    if not dicts:
        return str(data_list)
        
    # Gather all unique keys to use as column headers (capped at top 10 for neatness)
    keys = []
    for d in dicts:
        for k in d.keys():
            if k not in keys:
                keys.append(k)
    
    if len(keys) > 10:
        keys = keys[:10]
        
    # Calculate max column widths for clean padding
    col_widths = {k: len(str(k)) for k in keys}
    for d in dicts:
        for k in keys:
            val_str = str(d.get(k, ""))
            if isinstance(d.get(k), (dict, list)):
                val_str = json.dumps(d.get(k))
            col_widths[k] = max(col_widths[k], len(val_str))

    # Build header and separator lines
    header_parts = [f"{str(k):<{col_widths[k]}}" for k in keys]
    sep_parts = [f"{'-' * col_widths[k]}" for k in keys]
    
    lines = [" | ".join(header_parts), "-|-".join(sep_parts)]
    
    # Build data rows
    for d in dicts:
        row_parts = []
        for k in keys:
            val = d.get(k, "")
            if isinstance(val, (dict, list)):
                val = json.dumps(val)
            val_str = str(val)
            row_parts.append(f"{val_str:<{col_widths[k]}}")
        lines.append(" | ".join(row_parts))
        
    return "\n".join(lines)

def find_all_record_lists(obj, depth=0):
    """Recursively searches through ADF nodes to locate clean lists of records."""
    results = []
    if depth > 6:
        return results
    if isinstance(obj, list):
        if obj and all(isinstance(i, dict) for i in obj):
            results.append(obj)
        else:
            for item in obj:
                results.extend(find_all_record_lists(item, depth + 1))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            results.extend(find_all_record_lists(v, depth + 1))
    return results

def convert_saves_to_tables():
    print(f"[+] Scanning save directory: {BASE_DIR}")
    converted_count = 0

    for file_path in BASE_DIR.iterdir():
        if file_path.is_dir() or file_path.name in ["converted_dumps", "table_dumps"]:
            continue

        print(f"[*] Processing table dump for: {file_path.name}")
        output_txt_path = TABLE_DIR / f"{file_path.name}_table.txt"

        parsed_data = parse_adf_file(file_path)
        table_output = ""

        if parsed_data is not None:
            try:
                record_lists = find_all_record_lists(parsed_data)
                if record_lists:
                    sections = []
                    for idx, r_list in enumerate(record_lists):
                        sections.append(f"=== Table Section {idx + 1} (Total Rows: {len(r_list)}) ===")
                        sections.append(format_dict_list_as_table(r_list))
                        sections.append("\n" + "="*60 + "\n")
                    table_output = "\n".join(sections)
                else:
                    # Fallback to standard JSON text if no tabular lists are found
                    table_output = json.dumps(parsed_data, indent=4, default=str)
            except Exception as e:
                table_output = f"Error formatting records into table: {e}"
        else:
            # Fallback for plain text files (like configuration files)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as tf:
                    table_output = tf.read()
            except Exception:
                table_output = "[!] Could not parse file format."

        # Write out the formatted text table file
        with open(output_txt_path, "w", encoding="utf-8") as out_f:
            out_f.write(table_output)
        converted_count += 1

    print("\n--- Table Generation Complete ---")
    print(f"[+] Successfully converted {converted_count} files into text tables.")
    print(f"[+] Find your readable table text files in: {TABLE_DIR}")

if __name__ == "__main__":
    convert_saves_to_tables()