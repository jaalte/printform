#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify, send_from_directory
from PIL import Image, ImageDraw, ImageFont, ImageWin
import os
import csv
import json
import re
import codecs
import shutil
import win32print
import win32ui
from datetime import datetime
from tag_routes import register_tag_routes
from plant_tag import PlantTagDatabase
from difflib import SequenceMatcher

###############################################################################
# CONFIG / PATHS
###############################################################################
app = Flask(__name__)

# Adjust printer name to match your Windows printer
PRINTER_NAME = "Taglord (TEC B-SX5T) (305 dpi)"

# Single preview folder and file naming for each session
PREVIEW_FOLDER = 'static/preview_images'
os.makedirs(PREVIEW_FOLDER, exist_ok=True)

# Where permanent files are saved if user chooses "Save Label"
FINAL_LABELS_DIR = 'static/labels/generated_labels'
os.makedirs(FINAL_LABELS_DIR, exist_ok=True)

# Index file that tracks all saved labels
SAVED_INDEX_FILE = 'saved-label-index.json'

# Print log file that will track print jobs
PRINT_LOG_FILE = 'print-log.json'

# Paths for label template JSON
#  (We still keep this as a default, in case user doesn't pick any template_name)
label_template_path = 'static/label-templates/label_template_default.json'

###############################################################################
# A dictionary to remember each user's session data:
#   key = session_id
#   val = {
#       "used_formdata": { ...fields used to generate label... },
#       "label_template": { ... },
#       "date_created": "YYYY-MM-DDTHH:MM:SS",
#       "preview_filename": "preview_<session_id>.png"
#   }
###############################################################################
temp_label_store = {}

# Initialize PlantTag database
plant_tag_db = PlantTagDatabase()

###############################################################################
# INITIALIZATION
###############################################################################

def main():
    pass

def load_templates():
    """
    ### ADDED ###
    Loads all template files in static/label-templates that match label_template*.json,
    returning a dict keyed by each file's 'label' property. That 'label' is
    the human-readable name that goes in the dropdown.
    """
    templates = {}

    # Locate all template files in this directory
    # Template files match format label_template*.json
    template_folder_path = "static/label-templates"
    template_file_paths = [
        os.path.join(template_folder_path, f)
        for f in os.listdir(template_folder_path)
        if f.startswith("label_template") and f.endswith(".json")
    ]

    for template_path in template_file_paths:
        # Load label template
        with open(template_path, 'r', encoding='utf-8') as f:
            base_template = json.load(f)

        # Add the filename and location to improve logging
        template = {
            **base_template,
            "filename": os.path.basename(template_path),
            "template_path": template_path,
        }

        # "label" is a field in each JSON that identifies this template
        templates[template['label']] = template

    return templates

###############################################################################
# UTILITY FUNCTIONS
###############################################################################

def sanitize_string(s):
    """Removes special characters and replaces spaces with dashes."""
    return re.sub(r'[^a-zA-Z0-9\s]', '', s).replace(' ', '-')

def unescape_string(s):
    return codecs.decode(s, 'unicode_escape')

def offset_image(img, dx, dy):
    """Offsets the image by (dx, dy), cropping or padding with white as needed."""
    left = max(0, -dx)
    top = max(0, -dy)
    right = img.width - max(0, dx)
    bottom = img.height - max(0, dy)
    cropped_img = img.crop((left, top, right, bottom))

    paste_x = max(0, dx)
    paste_y = max(0, dy)
    offset_img = Image.new('RGB', (img.width, img.height), (255, 255, 255))
    offset_img.paste(cropped_img, (paste_x, paste_y))

    return offset_img

def generate_png(template, formdata, offset_adjustment):
    """
    Generates the label image in memory according to
    the template, formdata, and offset_adjustment.
    """
    label_base_path = template['base_image'] or "static/label-templates/label_base.png"
    
    img = Image.open(label_base_path)
    d = ImageDraw.Draw(img)

    for field in template['fields']:
        name = field['name']
        x, y = field['x'], field['y']
        data = field['data']
        text = formdata.get(name, '')

        if data['type'] == 'text':
            font_base = data['style']['font-base']
            font_size = data['style']['size']
            bold = data['style'].get('bold', False)
            italic = data['style'].get('italic', False)
            spacing = data['style'].get('spacing', 1)

            # Build the actual font path
            # (retain the user's original comment)
            if bold and italic:
                font_path = font_base.replace(".ttf", "bi.ttf")
            elif bold:
                font_path = font_base.replace(".ttf", "bd.ttf")
            elif italic:
                font_path = font_base.replace(".ttf", "i.ttf")
            else:
                font_path = font_base

            font = ImageFont.truetype(font_path, font_size)
            d.text((x, y), text, font=font, fill=(0, 0, 0), spacing=spacing)

    # Apply offsets - combine template offsets with adjustment
    dx = template["offsets"][0] + offset_adjustment[0]
    dy = template["offsets"][1] + offset_adjustment[1]
    return offset_image(img, dx, dy)

def append_to_saved_index(entry):
    """
    Appends a record to saved-label-index.json, creating if needed.
    Only called when /save_label is used.
    """
    index_path = os.path.join(app.root_path, SAVED_INDEX_FILE)
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            records = json.load(f)
    else:
        records = []

    records.append(entry)

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2)

def append_to_print_log(session_id, copies):
    """
    Appends a record to print-log.json containing the form data, template,
    and offset adjustments used to generate the label. These are loaded from temp_label_store.
    """
    log_path = os.path.join(app.root_path, PRINT_LOG_FILE)
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8') as f:
            logs = json.load(f)
    else:
        logs = []

    entry_data = temp_label_store.get(session_id, {})
    used_formdata = entry_data.get('used_formdata', {})
    label_template = entry_data.get('label_template', {})
    offset_adjustment = entry_data.get('offset_adjustment', (0, 0))

    log_entry = {
        "session_id": session_id,
        "count": copies,
        "formdata": used_formdata,        # the data used in generate_png
        "offset_adjustment": offset_adjustment, # the offset adjustments applied
        "label_template": label_template, # the template used
        "unix_time": int(datetime.now().timestamp()),
        "time": datetime.now().isoformat()
    }
    logs.append(log_entry)

    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2)

def print_label_file(image_path, copies, session_id=None):
    """
    Prints the given image `copies` times on Windows using win32print,
    then logs the form/template data to print-log.json.
    """
    if copies <= 0:
        return

    abs_path = os.path.join(app.root_path, image_path.lstrip('/'))
    if not os.path.exists(abs_path):
        return

    hprinter = win32print.OpenPrinter(PRINTER_NAME)
    printer_dc = win32ui.CreateDC()
    printer_dc.CreatePrinterDC(PRINTER_NAME)

    dpi_x = printer_dc.GetDeviceCaps(88)  # HORZRES
    dpi_y = printer_dc.GetDeviceCaps(90)  # VERTRES

    image = Image.open(abs_path)
    # Example dimension: 5" x 1" label
    target_width = int(5 * dpi_x)
    target_height = int(1 * dpi_y)
    image = image.resize((target_width, target_height))

    printer_dc.StartDoc(os.path.basename(abs_path))
    for _ in range(copies):
        printer_dc.StartPage()
        dib = ImageWin.Dib(image)
        dib.draw(printer_dc.GetHandleOutput(), (0, 0, target_width, target_height))
        printer_dc.EndPage()

    printer_dc.EndDoc()
    printer_dc.DeleteDC()
    win32print.ClosePrinter(hprinter)

    # Log the form data & template
    append_to_print_log(session_id if session_id else "unknown", copies)

###############################################################################
# ROUTES
###############################################################################

@app.route('/')
def index():
    """Serve the main HTML interface."""
    return render_template('printform-client.html')


@app.route('/get_templates', methods=['GET'])
def get_templates():
    """
    Returns the entire templates dictionary so the front-end can update labels
    from each template's fields[].
    """
    templates = load_templates()  # => a dict keyed by template['label']
    return jsonify(templates)


@app.route('/preview_label', methods=['POST'])
def preview_label():
    """
    Generate/update a single "preview" image in `static/preview_images/`
    for the given session_id. Overwrites the same file each time.
    Also saves 'used_formdata', 'label_template', and 'offset_adjustment' in temp_label_store.
    """
    session_id = request.form.get('session_id', '')
    if not session_id:
        return jsonify({"error": "No session_id provided"}), 400

    # ### ADDED ### - Check if user provided a template_name
    chosen_template_name = request.form.get('template_name', '')

    if chosen_template_name:
        # If user selected a template from the dropdown
        all_templates = load_templates()
        if chosen_template_name not in all_templates:
            return jsonify({"error": f"Unknown template_name: {chosen_template_name}"}), 400
        template = all_templates[chosen_template_name]
    else:
        # fallback to your default file if none provided
        with open(label_template_path, 'r', encoding='utf-8') as f:
            base_template = json.load(f)
        template = {
            "name": os.path.basename(label_template_path),
            **base_template
        }

    # Get offset adjustments
    offset_adjustment = (
        int(request.form.get('x-offset', 0)),
        int(request.form.get('y-offset', 0))
    )

    # Identify relevant field names
    fieldnames = [field["name"] for field in template['fields']]
    used_formdata = {name: request.form.get(name, '') for name in fieldnames}

    # Generate the in-memory label
    img = generate_png(template, used_formdata, offset_adjustment)

    # Construct the preview file path
    preview_filename = f"preview_{session_id}.png"
    abs_preview_path = os.path.join(app.root_path, PREVIEW_FOLDER, preview_filename)
    img.save(abs_preview_path)

    server_relative_path = '/' + os.path.relpath(abs_preview_path, app.root_path)
    server_relative_path = server_relative_path.replace('\\', '/')

    # Store data for later retrieval by /print_label
    temp_label_store[session_id] = {
        "used_formdata": used_formdata,       # data used to generate the label
        "label_template": template,           # the template used
        "offset_adjustment": offset_adjustment, # the offset adjustments applied
        "date_created": datetime.now().isoformat(),
        "preview_filename": preview_filename,
    }

    return jsonify({
        "message": f"Preview updated for session {session_id}.",
        "image_path": server_relative_path
    })

@app.route('/print_label', methods=['POST'])
def print_label():
    """
    Prints the single preview image for a session, repeated 'count' times.
    Uses the form data & template from temp_label_store[session_id].
    If count > 1, also saves the label to generated_labels.
    """
    data = request.get_json() or request.form
    session_id = data.get('session_id', '')
    count = int(data.get('count', 0))

    if not session_id or count <= 0:
        return jsonify({"message": "Nothing to print."}), 200

    # If printing multiple copies, save the label first
    if count > 1:
        save_label()

    preview_filename = f"preview_{session_id}.png"
    server_relative_path = f"/{PREVIEW_FOLDER}/{preview_filename}"
    print_label_file(server_relative_path, count, session_id=session_id)

    return jsonify({
        "message": f"Printed {count} copies of preview image for session {session_id}." + 
                  (" Label was automatically saved." if count > 1 else "")
    })

@app.route('/save_label', methods=['POST'])
def save_label():
    """
    Copies the single preview file for this session from preview_images to
    FINAL_LABELS_DIR, then appends an entry to saved-label-index.json.
    Now includes main_text, midtext, and subtext in the filename.
    """
    data = request.get_json() or request.form
    session_id = data.get('session_id', '')

    if not session_id:
        return jsonify({"error": "No session_id provided"}), 400

    preview_filename = f"preview_{session_id}.png"
    abs_preview_path = os.path.join(app.root_path, PREVIEW_FOLDER, preview_filename)
    if not os.path.exists(abs_preview_path):
        return jsonify({"error": "Preview file not found."}), 404

    # Retrieve stored data (form/template)
    entry_data = temp_label_store.get(session_id, {
        "used_formdata": {},
        "label_template": {},
        "date_created": datetime.now().isoformat()
    })

    # -- Build the dynamic filename from multiple fields --
    main_text  = entry_data["used_formdata"].get("main_text", "label")
    mid_text   = entry_data["used_formdata"].get("midtext", "")
    sub_text   = entry_data["used_formdata"].get("subtext", "")

    # Sanitize each field before combining
    sanitized_main = sanitize_string(main_text).lower()
    sanitized_mid  = sanitize_string(mid_text).lower()
    sanitized_sub  = sanitize_string(sub_text).lower()

    # Combine them with underscores
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    final_filename = f"label_{sanitized_main}_{sanitized_mid}_{sanitized_sub}_{timestamp}.png"

    abs_final_path = os.path.join(app.root_path, FINAL_LABELS_DIR, final_filename)

    # Copy instead of moving so we can still print the preview afterward
    shutil.copyfile(abs_preview_path, abs_final_path)

    new_rel_path = '/' + os.path.relpath(abs_final_path, app.root_path)
    new_rel_path = new_rel_path.replace('\\', '/')

    # Build a record for saved-label-index.json
    record = {
        "filepath": new_rel_path,
        "date_created": entry_data["date_created"],
        "formdata": entry_data["used_formdata"],
        "label_template": entry_data["label_template"]
    }
    append_to_saved_index(record)

    return jsonify({
        "message": f"Label saved to {new_rel_path}",
        "saved_path": new_rel_path
    })

# Optional route to manually download saved images
@app.route('/download_image/<path:filename>')
def download_image(filename):
    return send_from_directory(FINAL_LABELS_DIR, filename, as_attachment=True)

# If you want to serve the preview folder directly for debugging
@app.route('/static/preview_images/<path:filename>')
def serve_preview_images(filename):
    return send_from_directory(PREVIEW_FOLDER, filename)

@app.route('/search_labels', methods=['GET'])
def search_labels():
    """
    Search for labels in the generated_labels directory.
    Supports fuzzy search on filenames with word-level and sub-word matching.
    """
    query = request.args.get('q', '').lower().strip()
    
    if not query:
        return jsonify({'results': []})
    
    labels_dir = os.path.join(app.root_path, 'static/labels/generated_labels')
    results = []
    
    if not os.path.exists(labels_dir):
        return jsonify({'results': []})
    
    # Split query into individual search terms
    query_terms = [term.strip() for term in query.split() if term.strip()]
    
    # Get all PNG files in the directory
    for filename in os.listdir(labels_dir):
        if filename.endswith('.png') and filename.startswith('label_'):
            # Remove 'label_' prefix and '.png' suffix for search
            searchable_name = filename[6:-4].lower()
            
            # Extract plant info from filename
            # Format: label_plant-name_cultivar_description_date.png
            parts = searchable_name.split('_')
            
            # Create a list of all words in the filename (excluding date)
            filename_words = []
            for i, part in enumerate(parts[:-1]):  # Exclude the date part
                # Split each part by hyphens to get individual words
                filename_words.extend(part.split('-'))
            
            # Check if all query terms match somewhere in the filename
            all_terms_match = True
            best_similarity = 0.0
            
            for query_term in query_terms:
                term_matched = False
                term_best_similarity = 0.0
                
                # Check each word in the filename for a match
                for word in filename_words:
                    # Check for exact substring match within the word
                    if query_term in word:
                        term_matched = True
                        term_best_similarity = max(term_best_similarity, 0.8)  # High score for substring match
                        break
                
                if not term_matched:
                    all_terms_match = False
                    break
                
                best_similarity = max(best_similarity, term_best_similarity)
            
            # If all terms matched, calculate overall similarity for scoring
            if all_terms_match:
                # Calculate fuzzy similarity for ranking purposes only
                overall_similarity = SequenceMatcher(None, query, searchable_name).ratio()
                best_similarity = max(best_similarity, overall_similarity)
            
            # If all terms matched, include this result
            if all_terms_match:
                # Get file modification time
                file_path = os.path.join(labels_dir, filename)
                mod_time = os.path.getmtime(file_path)
                
                plant_info = {
                    'filename': filename,
                    'full_path': f'/static/labels/generated_labels/{filename}',
                    'similarity': best_similarity,
                    'mod_time': mod_time,
                    'plant_name': parts[0] if len(parts) > 0 else '',
                    'cultivar': parts[1] if len(parts) > 1 else '',
                    'description': '_'.join(parts[2:-1]) if len(parts) > 2 else '',
                    'date': parts[-1] if len(parts) > 0 else ''
                }
                
                results.append(plant_info)
    
    # Sort by modification time (newest first)
    # Ties broken by similarity score (highest first)
    results.sort(key=lambda x: (x['similarity'], x['mod_time']), reverse=True)
    
    return jsonify({'results': results})

@app.route('/migrate-data')
def migrate_data():
    """
    Migrate existing data from JSON files to the PlantTag database.
    Visit this URL in your browser to start the migration.
    """
    try:
        saved_index_path = os.path.join(app.root_path, SAVED_INDEX_FILE)
        print_log_path = os.path.join(app.root_path, PRINT_LOG_FILE)
        
        # Check if files exist
        if not os.path.exists(saved_index_path):
            return jsonify({
                "success": False,
                "error": f"Saved index file not found at: {saved_index_path}"
            }), 404
            
        if not os.path.exists(print_log_path):
            return jsonify({
                "success": False,
                "error": f"Print log file not found at: {print_log_path}"
            }), 404
        
        # Perform migration
        count = plant_tag_db.migrate_from_json(
            saved_index_path=saved_index_path,
            print_log_path=print_log_path
        )
        
        return jsonify({
            "success": True,
            "message": f"Successfully migrated {count} tags to the database",
            "tags_migrated": count
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Migration failed: {str(e)}"
        }), 500

@app.route('/print_existing_label', methods=['POST'])
def print_existing_label():
    """
    Print an existing saved label by filename.
    """
    data = request.get_json()
    filename = data.get('filename')
    count = data.get('count', 1)
    
    if not filename:
        return jsonify({'error': 'No filename provided'}), 400
    
    # Validate filename to prevent directory traversal
    if not filename.startswith('label_') or not filename.endswith('.png'):
        return jsonify({'error': 'Invalid filename'}), 400
    
    # Construct full path to the label
    label_path = os.path.join(app.root_path, 'static/labels/generated_labels', filename)
    
    if not os.path.exists(label_path):
        return jsonify({'error': 'Label file not found'}), 404
    
    try:
        # Print the existing label
        print_label_file(label_path, count)
        
        # Log the print job
        append_to_print_log(f"existing_{filename}", count)
        
        return jsonify({'success': True, 'message': f'Printed {count} copies of {filename}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    main()
    # Register tag management routes
    register_tag_routes(app)
    app.run(debug=True)
