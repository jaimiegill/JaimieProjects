import csv
import re
from pathlib import Path


def convert_adf_txt_to_csv(input_txt_path, output_csv_path):
  input_path = Path(input_txt_path)

  # Check if file exists as-is or with a .txt extension
  if not input_path.exists():
    if input_path.with_suffix('.txt').exists():
      input_path = input_path.with_suffix('.txt')
    else:
      print(f"Error: File not found at '{input_path}'")
      return

  with open(input_path, 'r', encoding='utf-8') as f:
    content = f.read()

  records = []
  reserve_blocks = re.split(r'ReserveId:\s*', content)[1:]

  for block in reserve_blocks:
    reserve_match = re.search(r'^(-?\d+)', block)
    if not reserve_match:
      continue
    reserve_id = reserve_match.group(1)

    nz_entries = block.split('# Structure NeedZoneBaseData_3')[1:]
    for entry in nz_entries:
      nz_id = re.search(r'NeedZoneId:\s*(-?\d+)', entry)
      if not nz_id:
        continue

      x = re.search(r'X:\s*([-?\d.]+)', entry)
      y = re.search(r'Y:\s*([-?\d.]+)', entry)
      z = re.search(r'Z:\s*([-?\d.]+)', entry)
      n_type = re.search(r'NeedType:\s*(-?\d+)', entry)
      map_icon = re.search(r'MapIconId:\s*(\d+)', entry)
      start_t = re.search(r'NeedZoneStartTimeHours:\s*([-?\d.]+)', entry)
      end_t = re.search(r'NeedZoneEndTimeHours:\s*([-?\d.]+)', entry)
      animal_id = re.search(
          r'AnimalTypeLocalizationName:\s*([-+]?\d+|0x[0-9a-fA-F]+)',
          entry,
      )
      sched_idx = re.search(r'NeedZoneScheduleIndex:\s*(-?\d+)', entry)

      groups_match = re.search(
          r'DiscoveredGroups:\s*\[(.*?)\]', entry, re.DOTALL
      )
      disc_groups = []
      if groups_match:
        disc_groups = re.findall(
            r'(\d+)\s*#', groups_match.group(1)
        ) or re.findall(
            r'^\s*(\d+)\s*$', groups_match.group(1), re.MULTILINE
        )

      records.append({
          'ReserveId': reserve_id,
          'Position_X': x.group(1) if x else '',
          'Position_Y': y.group(1) if y else '',
          'Position_Z': z.group(1) if z else '',
          'NeedZoneId': nz_id.group(1),
          'NeedType': n_type.group(1) if n_type else '',
          'MapIconId': map_icon.group(1) if map_icon else '',
          'NeedZoneStartTimeHours': start_t.group(1) if start_t else '',
          'NeedZoneEndTimeHours': end_t.group(1) if end_t else '',
          'AnimalTypeLocalizationName': animal_id.group(1) if animal_id else '',
          'NeedZoneScheduleIndex': sched_idx.group(1) if sched_idx else '',
          'DiscoveredGroups': ';'.join(disc_groups),
      })

  output_path = Path(output_csv_path)
  output_path.parent.mkdir(parents=True, exist_ok=True)

  if records:
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
      writer = csv.DictWriter(f, fieldnames=records[0].keys())
      writer.writeheader()
      writer.writerows(records)

  print(
      f"Successfully processed {len(records)} need zone records into"
      f" '{output_path}'."
  )


if __name__ == '__main__':
  INPUT_FILE = (
      r'C:\Users\gills\JaimieProjects\PythonProjects\COTWTrackerWorking\DecodedNeedZoneData\found_need_zones_adf_decoded.txt'
  )
  OUTPUT_FILE = r'C:\Users\gills\JaimieProjects\PythonProjects\COTWTrackerWorking\DecodedNeedZoneData\need_zones.csv'
  convert_adf_txt_to_csv(INPUT_FILE, OUTPUT_FILE)