#!/usr/bin/env python3

import json
import re
import sys
from collections import defaultdict
from rapidfuzz import fuzz, process

# ------------------------------------------------------------
# Helper function to remove punctuation and make lowercase
# ------------------------------------------------------------
def canonicalize(text):
    """
    Remove punctuation, make lowercase, and trim.
    """
    text = text.lower()
    # Remove all non-word (non-alphanumeric/underscore) and non-space characters
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()

# ------------------------------------------------------------
# 1. Load print-log.json and aggregate entries with count > 1
# ------------------------------------------------------------
with open("print-log.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

aggregated = {}
for entry in raw_data:
    if entry["count"] <= 1:
        continue

    fd = entry["formdata"]
    main_text = fd.get("main_text", "").strip()
    mid_text = fd.get("midtext", "").strip()
    sub_text = fd.get("subtext", "").strip()

    key = (
        main_text.lower(),
        mid_text.lower(),
        sub_text.lower()
    )
    if key not in aggregated:
        aggregated[key] = {
            "formdata": fd,
            "count": 0
        }
    aggregated[key]["count"] += entry["count"]

# ------------------------------------------------------------
# 2. Build a "searchable string" for each aggregated entry
# ------------------------------------------------------------
printlog_entries = []
for (main, mid, sub), data in aggregated.items():
    # Combine them all into a single string
    combined = f"{main} {mid} {sub}"
    # Also store a canonicalized version for fuzzy matching
    canonical = canonicalize(combined)

    printlog_entries.append({
        "search_string": combined,
        "canonical_search": canonical,
        "midtext": data["formdata"].get("midtext", ""),
        "count": data["count"]
    })

# ------------------------------------------------------------
# 3. Load master-list.txt -> parse "Name - Count"
# ------------------------------------------------------------
master_entries = []
with open("master-list.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        match = re.match(r"(.+?)\s*-\s*(\d+)", line)
        if not match:
            continue
        name = match.group(1).strip()      # keep raw form for output if no match
        name_lower = name.lower()
        count = int(match.group(2))
        master_entries.append((name, name_lower, count))

# ------------------------------------------------------------
# 4. Fuzzy match each master entry to the aggregated print-log
#    Using partial_token_set_ratio to ignore extra tokens & word order
# ------------------------------------------------------------
results = []

for raw_name, name_lower, master_count in master_entries:
    # Prepare canonical name for matching
    canonical_name = canonicalize(name_lower)

    # Generate a list of (candidate, score)
    candidate_scores = []
    for e in printlog_entries:
        score = fuzz.partial_token_set_ratio(canonical_name, e["canonical_search"])
        candidate_scores.append((e, score))

    # Sort by best score descending
    candidate_scores.sort(key=lambda x: x[1], reverse=True)

    # If best match meets threshold, treat as match
    best_match, best_score = candidate_scores[0] if candidate_scores else (None, 0)

    if best_score >= 70:
        # matched
        matched_entry = best_match
        midtext = matched_entry["midtext"]
        printed_count = matched_entry["count"]
        remaining = master_count - printed_count

        print(f"✔ MATCH: '{raw_name}' → '{matched_entry['search_string']}' "
              f"(score={best_score}, used_count={printed_count}, remaining={remaining})")

        if remaining > 0:
            # Write the "midtext : remainder" form to results
            results.append(f"{midtext} : {remaining}")
    else:
        # no good match
        print(f"✘ NO MATCH: '{raw_name}'")
        # We'll just use the raw name if no match
        results.append(f"{raw_name} : {master_count}")

# ------------------------------------------------------------
# 5. Write to needs-printed.txt
# ------------------------------------------------------------
with open("needs-printed.txt", "w", encoding="utf-8") as f:
    for line in results:
        f.write(line + "\n")

print("\nDone.\nResults written to needs-printed.txt.\n")  
