#!/usr/bin/env python3

import json
from datetime import datetime, timedelta
from collections import defaultdict

# ------------------------------------------------------------
# Normalize formdata to a tuple key
# ------------------------------------------------------------
def get_formdata_key(fd):
    return (
        fd.get("main_text", "").strip().lower(),
        fd.get("midtext", "").strip().lower(),
        fd.get("subtext", "").strip().lower()
    )

# ------------------------------------------------------------
# Load print-log.json
# ------------------------------------------------------------
with open("print-log.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

cutoff = datetime.now() - timedelta(weeks=4)

# ------------------------------------------------------------
# Filter entries within the last 4 weeks
# ------------------------------------------------------------
filtered = []
skipped = 0

for entry in raw_data:
    ts = entry.get("time")
    try:
        dt = datetime.fromisoformat(ts)
    except Exception:
        skipped += 1
        continue
    if dt >= cutoff:
        filtered.append(entry)

print(f"Filtered {len(filtered)} entries from the last 4 weeks. Skipped {skipped} invalid timestamps.")

# ------------------------------------------------------------
# Group by normalized formdata key
# ------------------------------------------------------------
grouped = defaultdict(lambda: {"formdata": None, "total_count": 0, "has_multi": False})

for entry in filtered:
    fd = entry["formdata"]
    key = get_formdata_key(fd)

    group = grouped[key]
    group["formdata"] = fd
    group["total_count"] += entry["count"]
    if entry["count"] > 1:
        group["has_multi"] = True

# ------------------------------------------------------------
# Prepare rows: only include entries with at least one count > 1
# ------------------------------------------------------------
rows = []
for group in grouped.values():
    if group["has_multi"]:
        fd = group["formdata"]
        rows.append((
            fd.get("main_text", "").strip(),
            fd.get("midtext", "").strip(),
            fd.get("subtext", "").strip(),
            group["total_count"]
        ))

# ------------------------------------------------------------
# Calculate column widths
# ------------------------------------------------------------
col_widths = [0, 0, 0]
for main, mid, sub, _ in rows:
    col_widths[0] = max(col_widths[0], len(main))
    col_widths[1] = max(col_widths[1], len(mid))
    col_widths[2] = max(col_widths[2], len(sub))

# Add 2 spaces of padding per column
col_widths = [w + 2 for w in col_widths]

# ------------------------------------------------------------
# Format and write the output
# ------------------------------------------------------------
with open("recent-tags.txt", "w", encoding="utf-8") as f:
    for main, mid, sub, count in rows:
        line = (
            main.ljust(col_widths[0]) +
            mid.ljust(col_widths[1]) +
            sub.ljust(col_widths[2]) +
            f": {count}"
        )
        f.write(line + "\n")

print("Done. Written to recent-tags.txt.")
