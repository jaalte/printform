#!/usr/bin/env python3
import os
import csv
import re
import json
import shutil
from datetime import datetime

# Input paths - relative to parent directory
CSV_FILE = '../print_history.csv'
LABELS_FOLDER = '../static/labels/generated_labels'

# Output paths - save to utility-scripts directory
ORPHAN_LABELS_FOLDER = './orphan-labels'
ORPHAN_LOGS_CSV = './orphan-logs.csv'
CONFLICTS_JSON = './conflicts.json'

# Output path for plantlist.json - this needs to be in root for migrate_database.py
PLANTLIST_JSON = '../plantlist.json'

# Create the orphan-labels folder if it doesn't exist
if not os.path.exists(ORPHAN_LABELS_FOLDER):
    os.makedirs(ORPHAN_LABELS_FOLDER)

def sanitize_string(s: str) -> str:
    """
    Remove any non-alphanumeric/whitespace chars from s, then replace spaces with '-'.
    Finally, lowercases the result.
    Example: "Nephrolepsis exaltata" -> "nephrolepsis-exaltata"
    """
    s = re.sub(r'[^a-zA-Z0-9\s]', '', s)  # keep letters, digits, spaces
    s = s.replace(' ', '-')               # replace spaces with hyphens
    return s.lower()

def parse_filename_prefix_and_timestamp(filename: str):
    """
    Filename format is generally:
        label_<any-words-or-dashes>-YYYYmmdd-HHMMSS.png

      1) Strip the .png suffix.
      2) Split from the RIGHT with a limit of 2. The last two dash segments are the
         date part (YYYYmmdd) and time part (HHMMSS).
      3) Rejoin those two pieces with a dash -> "YYYYmmdd-HHMMSS".
      4) The leftover left portion is the full prefix (including 'label_').
    """
    basename, ext = os.path.splitext(filename)
    if ext.lower() != '.png':
        raise ValueError(f"[DEBUG] Not a PNG file: '{filename}'")

    parts = basename.rsplit('-', 2)
    if len(parts) != 3:
        raise ValueError(
            f"[DEBUG] Could not properly split '{filename}' into prefix + date + time. "
            f"Got parts: {parts}"
        )

    prefix_part, date_part, time_part = parts
    dt_str = f"{date_part}-{time_part}"  # "YYYYmmdd-HHMMSS"
    try:
        dt = datetime.strptime(dt_str, "%Y%m%d-%H%M%S")
    except ValueError as e:
        raise ValueError(
            f"[DEBUG] Timestamp '{dt_str}' from '{filename}' is not 'YYYYmmdd-HHMMSS' format. "
            f"Error: {e}"
        )

    return prefix_part, dt

def get_sanitized_prefix_from_csv_row(row: dict, fieldnames: list) -> str:
    """
    Given a CSV row (dict) and the list of fieldnames,
    replicate how the label code was originally generated:

        filename = "label_" + "-".join(sanitized_values) + "-" + timestamp + ".png"
    """
    values = []
    for field in fieldnames:
        cell = row.get(field, '')
        if cell is None:
            cell = ''
        values.append(cell.strip())

    sanitized_values = [sanitize_string(v) for v in values]
    prefix = "label_" + '-'.join(sanitized_values)
    return prefix

def main():
    print(f"[DEBUG] CSV_FILE: {CSV_FILE}")
    print(f"[DEBUG] LABELS_FOLDER: {LABELS_FOLDER}")

    # 1) Read CSV
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            print("[DEBUG] No fieldnames found in CSV. Is the file empty or badly formatted?")
            return
        csv_rows = list(reader)

    print(f"[DEBUG] CSV Fieldnames: {fieldnames}")
    print(f"[DEBUG] Number of CSV rows: {len(csv_rows)}")

    # 2) Gather all PNG files in LABELS_FOLDER and parse out prefix/timestamps
    label_files = [f for f in os.listdir(LABELS_FOLDER) if f.lower().endswith('.png')]
    print(f"[DEBUG] Found {len(label_files)} PNG file(s) in {LABELS_FOLDER}")

    label_map = {}
    for lbl in label_files:
        try:
            prefix_part, dt = parse_filename_prefix_and_timestamp(lbl)
        except ValueError as err:
            print(f"[DEBUG] Skipping '{lbl}' - parse error: {err}")
            continue

        print(f"[DEBUG] Discovered file '{lbl}' -> prefix='{prefix_part}', timestamp='{dt}'")
        label_map.setdefault(prefix_part, []).append((lbl, dt))

    # 3) Sort each prefix list by timestamp descending so most recent is first
    for prefix_key in label_map:
        label_map[prefix_key].sort(key=lambda x: x[1], reverse=True)

    print("[DEBUG] The label_map contains the following prefixes:")
    for prefix_key, file_list in label_map.items():
        print(f"   prefix='{prefix_key}' -> {len(file_list)} file(s): {[f[0] for f in file_list]}")

    # 4) Match each CSV row to a label file
    matched_rows = []
    orphan_rows = []
    used_filenames = set()

    for i, row in enumerate(csv_rows):
        csv_prefix = get_sanitized_prefix_from_csv_row(row, fieldnames)

        print(f"\n[DEBUG] CSV row {i} -> row data: {row}")
        print(f"[DEBUG]   -> computed prefix: '{csv_prefix}'")

        if csv_prefix in label_map and label_map[csv_prefix]:
            chosen_file, chosen_dt = label_map[csv_prefix][0]
            used_filenames.add(chosen_file)

            entry = dict(row)
            entry["date-created"] = chosen_dt.strftime("%Y-%m-%d %H:%M:%S")
            # Force forward slashes for consistency
            entry["path"] = f"{LABELS_FOLDER}/{chosen_file}"

            print(f"[DEBUG]   -> MATCH FOUND: '{chosen_file}' (timestamp={entry['date-created']})")
            matched_rows.append(entry)
        else:
            print(f"[DEBUG]   -> NO MATCH; row will go to orphan logs.")
            orphan_rows.append(row)

    # 5) Any label files not used get copied to orphan-labels
    for lbl in label_files:
        if lbl not in used_filenames:
            src = os.path.join(LABELS_FOLDER, lbl)
            dst = os.path.join(ORPHAN_LABELS_FOLDER, lbl)
            print(f"[DEBUG] Orphan label file '{lbl}' -> copying to '{ORPHAN_LABELS_FOLDER}'")
            if not os.path.exists(dst):
                shutil.copy2(src, dst)

    # 6) Write the orphan CSV lines to orphan-logs.csv
    if orphan_rows:
        print(f"[DEBUG] Writing {len(orphan_rows)} orphan row(s) to '{ORPHAN_LOGS_CSV}'")
        with open(ORPHAN_LOGS_CSV, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(orphan_rows)
    else:
        print("[DEBUG] No orphan rows found.")

    # 7) Deduplicate matched_rows by path, track conflicts in conflicts.json
    seen_paths = {}
    conflicts = {}  # { path -> [ list of differences from duplicates ] }

    for row in matched_rows:
        path_val = row["path"]
        if path_val not in seen_paths:
            # first time seeing this path, store the row
            seen_paths[path_val] = row
        else:
            # we already have an entry for this path; check for differences
            original = seen_paths[path_val]
            diff = {}
            # Compare field by field (excluding path)
            all_keys = set(original.keys()).union(row.keys())
            for key in all_keys:
                if key == "path":
                    continue
                val_original = original.get(key, "")
                val_duplicate = row.get(key, "")
                if val_original != val_duplicate:
                    diff[key] = {
                        "original": val_original,
                        "duplicate": val_duplicate
                    }
            # Only record if differences exist
            if diff:
                conflicts.setdefault(path_val, []).append(diff)

    # Build final deduplicated list
    deduplicated_entries = list(seen_paths.values())

    # Write conflicts.json
    with open(CONFLICTS_JSON, 'w', encoding='utf-8') as f:
        json.dump(conflicts, f, indent=2, ensure_ascii=False)

    # 8) Finally, write the deduplicated rows to plantlist.json
    print(f"[DEBUG] Writing {len(deduplicated_entries)} deduplicated row(s) to '{PLANTLIST_JSON}'")
    with open(PLANTLIST_JSON, 'w', encoding='utf-8') as f:
        json.dump(deduplicated_entries, f, indent=2, ensure_ascii=False)

    print("[DEBUG] Done.")

if __name__ == '__main__':
    main()
