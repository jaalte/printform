#!/usr/bin/env python3
import json
import os

# Default template offsets that were used in all templates
DEFAULT_TEMPLATE_OFFSETS = [50, -20]

# Path for saved-label-index
INPUT_FILE = '../saved-label-index.json'
OUTPUT_FILE = '../saved-label-index-new.json'

def migrate_saved_label_index():
    # Read the existing saved label index
    print(f"Reading saved label index from {INPUT_FILE}")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
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
            # Note: saved-label-index entries may have different fields than print-log entries
            new_entry = {}
            
            # Preserve session_id if it exists
            if 'session_id' in entry:
                new_entry['session_id'] = entry['session_id']
                
            # Copy other common fields in proper order
            for field in ['formdata', 'offset_adjustment', 'label_template', 'filepath', 'date_created']:
                if field == 'offset_adjustment':
                    new_entry['offset_adjustment'] = offset_adjustment
                elif field in entry:
                    new_entry[field] = entry[field]
            
            # Copy any remaining fields not explicitly handled
            for key, value in entry.items():
                if key not in new_entry and key != 'label_template':
                    new_entry[key] = value
            
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
    print(f"Writing migrated data to {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

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
    print("Starting migration of saved-label-index.json...")
    migrate_saved_label_index()
    print("Done!") 