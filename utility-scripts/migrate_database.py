#!/usr/bin/env python3
import os
import json
import sqlite3
import re
import csv
import glob
import hashlib
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Set, Any, Tuple, Optional

# Paths for JSON and CSV files - now relative to parent directory
SAVED_INDEX_FILE = '../saved-label-index.json'
PRINT_LOG_FILE = '../print-log.json'
PLANTLIST_JSON = '../plantlist.json'
CSV_FILE = '../print_history.csv'
CSV_CLEAN_JSON = '../print_history_csv_clean.json'
DB_PATH = '../plant_tags.db'
LABELS_DIR = '../static/labels/generated_labels'

# Path to default template file
DEFAULT_TEMPLATE_FILE = '../static/label-templates/label_template_default.json'

# Paths for utility scripts
REPAIR_LOGS_SCRIPT = './repair-logs.py'

def load_default_template():
    """Load the default template from file - fail if not found"""
    if not os.path.exists(DEFAULT_TEMPLATE_FILE):
        raise FileNotFoundError(f"Default template file {DEFAULT_TEMPLATE_FILE} not found")
        
    with open(DEFAULT_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_content_hash(formdata: Dict[str, str]) -> str:
    """
    Create a content hash based only on formdata
    This is used to identify unique tags by their content, ignoring template and offsets
    """
    # Only use formdata for hash generation
    content = {"formdata": formdata}
    
    content_str = json.dumps(content, sort_keys=True)
    return hashlib.md5(content_str.encode('utf-8')).hexdigest()

def sanitize_string(s):
    """Removes special characters and replaces spaces with dashes."""
    if s is None:
        return ""
    return re.sub(r'[^a-zA-Z0-9\s]', '', s).replace(' ', '-')

def generate_filename(main_text, mid_text, sub_text):
    """
    Mimics the filename generation process from printform-server.py
    """
    # Sanitize each field before combining
    sanitized_main = sanitize_string(main_text).lower() if main_text else ""
    sanitized_mid = sanitize_string(mid_text).lower() if mid_text else ""
    sanitized_sub = sanitize_string(sub_text).lower() if sub_text else ""
    
    # Create the base for the filename pattern (without timestamp)
    parts = []
    if sanitized_main:
        parts.append(sanitized_main)
    if sanitized_mid:
        parts.append(sanitized_mid)
    if sanitized_sub:
        parts.append(sanitized_sub)
    
    # Join with hyphens for the base filename
    base_filename = f"label_{'-'.join(parts)}"
    
    # This will be used as a pattern for globbing
    return base_filename + "_*.png"

def find_matching_file(pattern):
    """Find a file matching the pattern in the labels directory"""
    matches = glob.glob(os.path.join(LABELS_DIR, pattern))
    if matches:
        # Sort by modification time, newest first
        matches.sort(key=os.path.getmtime, reverse=True)
        return matches[0]
    return None

def extract_date_from_filename(filename):
    """
    Extract the date from the filename
    Format is typically: label_name-parts_YYYYMMDD-HHMMSS.png
    """
    basename = os.path.basename(filename)
    # Try to find a date pattern in the filename
    match = re.search(r'(\d{8}-\d{6})\.png$', basename)
    if match:
        date_str = match.group(1)
        try:
            # Convert to datetime
            dt = datetime.strptime(date_str, "%Y%m%d-%H%M%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    
    # Fallback to file modification time
    mod_time = os.path.getmtime(filename)
    return datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")

def get_existing_content_hashes() -> Dict[str, int]:
    """
    Get all content hashes from the database along with their tag_id
    """
    hashes = {}
    if not os.path.exists(DB_PATH):
        return hashes
        
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tag_id, content_hash FROM plant_tags")
        for row in cursor.fetchall():
            tag_id, content_hash = row
            hashes[content_hash] = tag_id
    
    return hashes

def get_print_log_entries():
    """
    Extract print log entries and organize them by content hash
    Returns a dictionary mapping content_hash -> list of print records
    """
    print_logs_by_hash = {}
    
    if not os.path.exists(PRINT_LOG_FILE):
        print(f"Warning: {PRINT_LOG_FILE} not found, skipping print log processing")
        return print_logs_by_hash
    
    # Load print logs
    with open(PRINT_LOG_FILE, 'r', encoding='utf-8') as f:
        print_logs = json.load(f)
    
    # Group logs by content hash
    for log in print_logs:
        # Extract data for hash generation
        formdata = log.get("formdata", {})
        
        # Skip entries without valid formdata
        if not formdata:
            continue
            
        content_hash = create_content_hash(formdata)
        
        if content_hash not in print_logs_by_hash:
            print_logs_by_hash[content_hash] = []
            
        # Add this log with its print count and reference to full log
        print_logs_by_hash[content_hash].append({
            "copies": log.get("count", 1),
            "date": log.get("time", datetime.now().isoformat()),
            "unix_time": log.get("unix_time", int(datetime.now().timestamp())),
            "log_entry": log  # Store the full log for reference
        })
    
    return print_logs_by_hash

def find_image_for_print_log(log_entry):
    """
    Try to find an image file for a print log entry
    Uses multiple strategies to increase chances of finding a match
    """
    formdata = log_entry.get("formdata", {})
    
    # Strategy 1: Use standard filename pattern
    main_text = formdata.get("main_text", "")
    midtext = formdata.get("midtext", "")
    subtext = formdata.get("subtext", "")
    
    pattern = generate_filename(main_text, midtext, subtext)
    image_path = find_matching_file(pattern)
    
    if image_path:
        return image_path
    
    # Strategy 2: Try more aggressive pattern matching
    # Just use main_text, which is most likely to be consistent
    pattern = generate_filename(main_text, "", "")
    matches = glob.glob(os.path.join(LABELS_DIR, pattern))
    
    if matches:
        # Sort by modification time, newest first
        matches.sort(key=os.path.getmtime, reverse=True)
        return matches[0]
    
    # Strategy 3: Search by timestamp if available
    if "time" in log_entry:
        try:
            log_time = datetime.fromisoformat(log_entry["time"])
            date_part = log_time.strftime("%Y%m%d")
            
            # Look for any files with this date
            date_pattern = f"*{date_part}*.png"
            date_matches = glob.glob(os.path.join(LABELS_DIR, date_pattern))
            
            if date_matches:
                # Find files from this date, use one closest in time
                closest_file = None
                min_time_diff = float('inf')
                
                for file_path in date_matches:
                    try:
                        # Extract timestamp from filename
                        match = re.search(r'(\d{8}-\d{6})\.png$', os.path.basename(file_path))
                        if match:
                            file_time_str = match.group(1)
                            file_time = datetime.strptime(file_time_str, "%Y%m%d-%H%M%S")
                            time_diff = abs((file_time - log_time).total_seconds())
                            
                            if time_diff < min_time_diff:
                                min_time_diff = time_diff
                                closest_file = file_path
                    except Exception:
                        continue
                
                # Only return if the time difference is reasonable (within an hour)
                if closest_file and min_time_diff < 3600:
                    return closest_file
        except Exception:
            pass
    
    # No image found
    return None

def process_csv_to_json():
    """Process the CSV file and create a clean JSON output"""
    if not os.path.exists(CSV_FILE):
        print(f"Error: {CSV_FILE} not found")
        return []
    
    # Get a list of all PNG files in the labels directory
    all_files = os.listdir(LABELS_DIR)
    png_files = [f for f in all_files if f.endswith('.png')]
    print(f"Found {len(png_files)} PNG files in {LABELS_DIR}")
    
    # Read the CSV file
    records = []
    discarded = 0
    recognized = 0
    
    with open(CSV_FILE, 'r', encoding='utf-8', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for i, row in enumerate(reader):
            # Skip header row if needed
            if i == 0 and 'main_text' in row and row['main_text'] == 'main_text':
                continue
            
            try:
                # Extract the text fields
                main_text = row.get('main_text', '')
                midtext = row.get('midtext', '')
                subtext = row.get('subtext', '')
                
                # Generate filename pattern
                pattern = generate_filename(main_text, midtext, subtext)
                
                # Look for a matching file
                matching_file = find_matching_file(pattern)
                
                if matching_file:
                    # Extract date
                    image_date = extract_date_from_filename(matching_file)
                    
                    # Create record
                    record = {
                        "formdata": {
                            "main_text": main_text,
                            "midtext": midtext,
                            "subtext": subtext
                        },
                        "image_name": os.path.basename(matching_file),
                        "image_date": image_date,
                        "image_path": matching_file.replace('\\', '/').replace('./', '/')
                    }
                    
                    records.append(record)
                    recognized += 1
                else:
                    discarded += 1
                    
                # Print progress every 100 rows
                if (i + 1) % 100 == 0:
                    print(f"Processed {i+1} rows, recognized: {recognized}, discarded: {discarded}")
                
            except Exception as e:
                print(f"Error processing row {i+1}: {e}")
                discarded += 1
    
    # Save to JSON
    with open(CSV_CLEAN_JSON, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    
    print("\nCSV Processing Summary:")
    print(f"Total rows processed: {recognized + discarded}")
    print(f"Recognized: {recognized}")
    print(f"Discarded: {discarded}")
    print(f"Results saved to {CSV_CLEAN_JSON}")
    
    return records

def add_print_records(cursor, tag_id, print_records):
    """Add print records for a tag"""
    for record in print_records:
        # Extract data from the record
        copies = record.get("copies", 1)
        print_date = record.get("date", datetime.now().isoformat())
        unix_time = record.get("unix_time", int(datetime.now().timestamp()))
        
        # Add the print record
        cursor.execute("""
        INSERT INTO print_history
        (tag_id, copies, print_date, unix_time)
        VALUES (?, ?, ?, ?)
        """, (tag_id, copies, print_date, unix_time))

def migrate_saved_labels(cursor, existing_hashes, print_logs_by_hash):
    """
    Migrate data from saved-label-index.json to the database
    """
    if not os.path.exists(SAVED_INDEX_FILE):
        print(f"Warning: {SAVED_INDEX_FILE} not found, skipping")
        return 0
        
    # Load saved labels
    with open(SAVED_INDEX_FILE, 'r', encoding='utf-8') as f:
        saved_labels = json.load(f)
        
    # Process saved labels (highest priority)
    migrated_count = 0
    for label_data in saved_labels:
        # Get the necessary data, preserving all metadata
        formdata = label_data.get("formdata", {})
        template = label_data.get("label_template", {})
        image_path = label_data.get("filepath", "")
        created_date = label_data.get("date_created", datetime.now().isoformat())
        
        # Generate content hash
        content_hash = create_content_hash(formdata)
        
        # Check if this tag already exists in the database
        tag_id = None
        if content_hash in existing_hashes:
            # Tag already exists, get its ID
            tag_id = existing_hashes[content_hash]
        else:
            # Generate exact hash (including offset adjustment)
            offset_adjustment = template.get("offsets", (0, 0))
            if not isinstance(offset_adjustment, (list, tuple)) or len(offset_adjustment) != 2:
                offset_adjustment = (0, 0)
                
            # Create exact hash
            exact_hash = hashlib.md5((content_hash + str(offset_adjustment)).encode('utf-8')).hexdigest()
            
            # Insert into database as confirmed tag (from saved labels)
            cursor.execute("""
            INSERT INTO plant_tags 
            (content_hash, exact_hash, formdata, template, offset_adjustment, 
            image_path, created_date, confirmed)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                content_hash,
                exact_hash,
                json.dumps(formdata),
                json.dumps(template),
                json.dumps(offset_adjustment),
                image_path,
                created_date
            ))
            
            tag_id = cursor.lastrowid
            existing_hashes[content_hash] = tag_id
            migrated_count += 1
        
        # Check if this tag has print log entries
        if content_hash in print_logs_by_hash:
            print_records = print_logs_by_hash[content_hash]
            add_print_records(cursor, tag_id, print_records)
            # Remove from print logs to avoid duplicate processing
            del print_logs_by_hash[content_hash]
    
    return migrated_count

def migrate_print_logs(cursor, existing_hashes, print_logs_by_hash):
    """
    Process print logs for tags that weren't in saved labels (medium priority)
    """
    if not print_logs_by_hash:
        print("No print logs to process")
        return 0
    
    # Process print logs
    migrated_count = 0
    for content_hash, print_records in print_logs_by_hash.items():
        # Skip if already processed in saved labels or no records
        if not print_records:
            continue
        
        # Check if this tag already exists in the database
        tag_id = None
        if content_hash in existing_hashes:
            # Tag already exists, get its ID
            tag_id = existing_hashes[content_hash]
            # Add print records to the existing tag
            add_print_records(cursor, tag_id, print_records)
        else:
            # Get the log entry with the highest print count
            best_record = max(print_records, key=lambda x: x.get("copies", 1))
            best_log_entry = best_record.get("log_entry")
            
            if not best_log_entry:
                continue
                
            # Extract data, preserving all metadata
            formdata = best_log_entry.get("formdata", {})
            template = best_log_entry.get("label_template", {})
            offset_adjustment = best_log_entry.get("offset_adjustment", (0, 0))
            created_date = best_log_entry.get("time", datetime.now().isoformat())
            
            # Look for an image path
            image_path = find_image_for_print_log(best_log_entry)
            
            # Determine if tag should be confirmed (multiple copies printed)
            confirmed = False
            for record in print_records:
                if record.get("copies", 1) > 1:
                    confirmed = True
                    break
            
            # Create exact hash
            exact_hash = hashlib.md5((content_hash + str(offset_adjustment)).encode('utf-8')).hexdigest()
            
            # Insert into database
            cursor.execute("""
            INSERT INTO plant_tags 
            (content_hash, exact_hash, formdata, template, offset_adjustment, 
            image_path, created_date, confirmed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                content_hash,
                exact_hash,
                json.dumps(formdata),
                json.dumps(template),
                json.dumps(offset_adjustment),
                image_path if image_path else "",
                created_date,
                1 if confirmed else 0
            ))
            
            tag_id = cursor.lastrowid
            existing_hashes[content_hash] = tag_id
            
            # Add print records
            add_print_records(cursor, tag_id, print_records)
            
            migrated_count += 1
    
    return migrated_count

def migrate_plantlist(cursor, existing_hashes):
    """
    Import tags from plantlist.json that aren't already in the database (low priority)
    """
    if not os.path.exists(PLANTLIST_JSON):
        print(f"Warning: {PLANTLIST_JSON} not found, skipping")
        return 0
    
    # Load plantlist.json
    with open(PLANTLIST_JSON, 'r', encoding='utf-8') as f:
        plantlist = json.load(f)
    
    # Process plantlist entries
    imported_count = 0
    for entry in plantlist:
        # Create formdata from the plantlist entry
        formdata = {
            "main_text": entry.get("main_text", ""),
            "midtext": entry.get("midtext", ""),
            "subtext": entry.get("subtext", "")
        }
        
        # Since plantlist entries don't have template info, we need to infer
        # based on categories like "pepper", "tomato", etc. in the main_text
        # For now, use default template
        template = load_default_template()
        
        # Generate content hash to check for duplicates
        content_hash = create_content_hash(formdata)
        
        # Skip if this tag already exists
        if content_hash in existing_hashes:
            continue
        
        # Generate exact hash (including offset adjustment)
        offset_adjustment = template.get("offsets", (0, 0))
        exact_hash = hashlib.md5((content_hash + str(offset_adjustment)).encode('utf-8')).hexdigest()
        
        # Get image path and created date
        image_path = entry.get("path", "")
        created_date = entry.get("date-created", datetime.now().isoformat())
        
        # Verify if the image exists, if not try to find a matching one
        if not image_path or not os.path.exists(image_path.lstrip('/')):
            # Try to find a matching image
            pattern = generate_filename(
                formdata.get("main_text", ""),
                formdata.get("midtext", ""),
                formdata.get("subtext", "")
            )
            matching_file = find_matching_file(pattern)
            if matching_file:
                image_path = matching_file.replace('\\', '/').replace('./', '/')
        
        # Insert into database as unconfirmed tag
        cursor.execute("""
        INSERT INTO plant_tags 
        (content_hash, exact_hash, formdata, template, offset_adjustment, 
         image_path, created_date, confirmed)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            content_hash,
            exact_hash,
            json.dumps(formdata),
            json.dumps(template),
            json.dumps(offset_adjustment),
            image_path,
            created_date
        ))
        
        imported_count += 1
        # Add this hash to our set to avoid duplicates
        existing_hashes[content_hash] = cursor.lastrowid
    
    return imported_count

def migrate_csv_entries(cursor, existing_hashes):
    """
    Import entries from the cleaned CSV JSON file (lowest priority)
    """
    if not os.path.exists(CSV_CLEAN_JSON):
        print(f"Warning: {CSV_CLEAN_JSON} not found, processing CSV first")
        clean_records = process_csv_to_json()
    else:
        with open(CSV_CLEAN_JSON, 'r', encoding='utf-8') as f:
            clean_records = json.load(f)
    
    if not clean_records:
        print("No CSV records to process")
        return 0
    
    # Process CSV entries
    imported_count = 0
    for record in clean_records:
        # Get formdata and image information
        formdata = record.get("formdata", {})
        image_path = record.get("image_path", "")
        image_date = record.get("image_date", datetime.now().isoformat())
        
        # Use default template since CSV entries don't have template info
        template = load_default_template()
        
        # Generate content hash
        content_hash = create_content_hash(formdata)
        
        # Skip if already processed
        if content_hash in existing_hashes:
            continue
        
        # Generate exact hash (including offset adjustment)
        offset_adjustment = template.get("offsets", (0, 0))
        exact_hash = hashlib.md5((content_hash + str(offset_adjustment)).encode('utf-8')).hexdigest()
        
        # Insert into database as unconfirmed tag
        cursor.execute("""
        INSERT INTO plant_tags 
        (content_hash, exact_hash, formdata, template, offset_adjustment, 
         image_path, created_date, confirmed)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            content_hash,
            exact_hash,
            json.dumps(formdata),
            json.dumps(template),
            json.dumps(offset_adjustment),
            image_path,
            image_date
        ))
        
        imported_count += 1
        # Add this hash to our set to avoid duplicates
        existing_hashes[content_hash] = cursor.lastrowid
    
    return imported_count

def ensure_db_exists():
    """Ensure the database exists with proper schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tags table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS plant_tags (
        tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_hash TEXT NOT NULL,
        exact_hash TEXT NOT NULL,
        formdata TEXT NOT NULL,
        template TEXT NOT NULL,
        offset_adjustment TEXT NOT NULL,
        image_path TEXT,
        created_date TEXT NOT NULL,
        confirmed BOOLEAN DEFAULT 0
    )
    """)
    
    # Create print history table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS print_history (
        print_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tag_id INTEGER NOT NULL,
        copies INTEGER NOT NULL,
        print_date TEXT NOT NULL,
        unix_time INTEGER NOT NULL,
        FOREIGN KEY (tag_id) REFERENCES plant_tags (tag_id)
    )
    """)
    
    conn.commit()
    return conn, cursor

def run_repair_logs():
    """
    Run the repair-logs.py script first to ensure plantlist.json is up to date
    """
    print("Running repair-logs.py to update plantlist.json...")
    
    try:
        # Check if repair-logs.py exists
        if not os.path.exists(REPAIR_LOGS_SCRIPT):
            print(f"Warning: {REPAIR_LOGS_SCRIPT} not found, skipping")
            return False
        
        # Run the script
        result = subprocess.run(
            [sys.executable, REPAIR_LOGS_SCRIPT], 
            cwd=os.path.dirname(os.path.abspath(__file__)),
            check=True
        )
        
        if result.returncode == 0:
            print("Successfully ran repair-logs.py")
            return True
        else:
            print(f"Warning: repair-logs.py exited with code {result.returncode}")
            return False
    
    except Exception as e:
        print(f"Error running repair-logs.py: {str(e)}")
        return False

def migrate_all():
    """
    Main function to migrate all data sources to the database
    Priority order:
    1. saved-label-index.json (highest trust)
    2. print-log.json (medium trust)
    3. plantlist.json (low trust)
    4. print_history.csv (lowest trust)
    """
    print("Starting comprehensive database migration...")
    
    # First, run repair-logs.py to ensure plantlist.json is up to date
    #run_repair_logs()
    
    # Next, ensure the database exists
    conn, cursor = ensure_db_exists()
    
    # Get existing hashes from database
    existing_hashes = get_existing_content_hashes()
    print(f"Found {len(existing_hashes)} existing records in database")
    
    # Get print logs organized by content hash
    print_logs_by_hash = get_print_log_entries()
    print(f"Found {len(print_logs_by_hash)} unique tags in print logs")
    
    # Migrate saved labels (highest priority, confirmed tags)
    saved_count = migrate_saved_labels(cursor, existing_hashes, print_logs_by_hash)
    print(f"Migrated {saved_count} new records from saved-label-index.json")
    
    # Process remaining print logs (medium priority)
    printlog_count = migrate_print_logs(cursor, existing_hashes, print_logs_by_hash)
    print(f"Migrated {printlog_count} additional records from print-log.json")
    
    # Migrate plantlist.json (low priority, unconfirmed tags)
    plantlist_count = migrate_plantlist(cursor, existing_hashes)
    print(f"Migrated {plantlist_count} additional records from plantlist.json")
    
    # Process and migrate CSV entries (lowest priority)
    csv_count = migrate_csv_entries(cursor, existing_hashes)
    print(f"Migrated {csv_count} additional records from cleaned CSV data")
    
    # Commit and close the database connection
    conn.commit()
    conn.close()
    
    print("\nMigration Summary:")
    print(f"Total migrated records: {saved_count + printlog_count + plantlist_count + csv_count}")
    print(f"- From saved-label-index.json: {saved_count}")
    print(f"- From print-log.json: {printlog_count}")
    print(f"- From plantlist.json: {plantlist_count}")
    print(f"- From print_history.csv: {csv_count}")
    print("Done!")

if __name__ == "__main__":
    migrate_all() 