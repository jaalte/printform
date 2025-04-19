#!/usr/bin/env python3
import json
import os

# Default template offsets that were used in all templates
DEFAULT_TEMPLATE_OFFSETS = [50, -20]

def migrate_print_log():
    # Read the existing print log
    with open('print-log.json', 'r', encoding='utf-8') as f:
        entries = json.load(f)

    # Track problematic entries
    problematic_entries = []
    migrated_count = 0

    # Process each entry
    for i, entry in enumerate(entries):
        try:
            # Skip if already migrated (has offset_adjustment)
            if 'offset_adjustment' in entry:
                continue

            # Get the template from the entry
            template = entry.get('label_template')
            if not template:
                problematic_entries.append({
                    'index': i,
                    'formdata': entry.get('formdata', {}),
                    'reason': 'Missing label_template'
                })
                continue

            # Check for offsets in template
            if 'offsets' not in template:
                problematic_entries.append({
                    'index': i,
                    'formdata': entry.get('formdata', {}),
                    'reason': 'Missing offsets in template'
                })
                continue

            # Calculate the offset_adjustment by subtracting default offsets
            stored_offsets = template['offsets']
            offset_adjustment = [
                stored_offsets[0] - DEFAULT_TEMPLATE_OFFSETS[0],
                stored_offsets[1] - DEFAULT_TEMPLATE_OFFSETS[1]
            ]

            # Update the entry - ensure offset_adjustment is between formdata and label_template
            template['offsets'] = DEFAULT_TEMPLATE_OFFSETS.copy()
            
            # Create a new entry with the desired order
            new_entry = {
                "session_id": entry["session_id"],
                "count": entry["count"],
                "formdata": entry["formdata"],
                "offset_adjustment": offset_adjustment,
                "label_template": template,
                "unix_time": entry["unix_time"],
                "time": entry["time"]
            }
            
            # Update the original entry
            entries[i] = new_entry
            migrated_count += 1

        except Exception as e:
            problematic_entries.append({
                'index': i,
                'formdata': entry.get('formdata', {}),
                'reason': f'Error processing: {str(e)}'
            })

    # Write the migrated data to a new file
    with open('print_log_fixed.json', 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2)

    # Print summary
    print(f"\nMigration Summary:")
    print(f"Total entries processed: {len(entries)}")
    print(f"Successfully migrated: {migrated_count}")
    print(f"Problematic entries: {len(problematic_entries)}")
    
    if problematic_entries:
        print("\nProblematic entries:")
        for entry in problematic_entries:
            formdata = entry['formdata']
            main_text = formdata.get('main_text', '')
            midtext = formdata.get('midtext', '')
            subtext = formdata.get('subtext', '')
            print(f"  - Entry {entry['index']} (main_text: '{main_text}', midtext: '{midtext}', subtext: '{subtext}'): {entry['reason']}")

    print("\nOriginal template offsets have been reset to [50, -20]")
    print("Offset adjustments have been calculated as: stored_offsets - [50, -20]")

if __name__ == '__main__':
    migrate_print_log() 