from flask import Flask, render_template, jsonify, request, send_from_directory
import os
import json
import csv
import re
import shutil
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# Configuration paths
PREVIEW_FOLDER = 'static/preview_images'
os.makedirs(PREVIEW_FOLDER, exist_ok=True)

FINAL_LABELS_DIR = 'static/generated_labels'
os.makedirs(FINAL_LABELS_DIR, exist_ok=True)

SAVED_INDEX_FILE = 'saved-label-index.json'
PRINT_LOG_FILE = 'print-log.json'

# Session storage for label data
temp_label_store = {}

###############################################################################
# UTILITY FUNCTIONS
###############################################################################

def sanitize_string(s):
    """Removes special characters and replaces spaces with dashes."""
    return re.sub(r'[^a-zA-Z0-9\s]', '', s).replace(' ', '-')

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

def save_to_csv(fieldnames, form_data):
    """Adds the form values to print_history.csv, if desired."""
    with open('print_history.csv', mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if csvfile.tell() == 0:
            writer.writeheader()
        values_dict = {name: form_data.get(name, '') for name in fieldnames}
        writer.writerow(values_dict)

def generate_png(template, form_data):
    """
    Generates the label image in memory according to
    the template and form data.
    """
    label_base_path = template.get('base_image') or "static/label-templates/label_base.png"
    
    img = Image.open(label_base_path)
    d = ImageDraw.Draw(img)

    for field in template['fields']:
        name = field['name']
        x, y = field['x'], field['y']
        data = field['data']
        text = form_data.get(name, '')

        if data['type'] == 'text':
            font_base = data['style'].get('font-base', 'arial.ttf')
            font_size = data['style'].get('size', 48)
            bold = data['style'].get('bold', False)
            italic = data['style'].get('italic', False)
            spacing = data['style'].get('spacing', 1)

            # Build the actual font path
            if bold and italic:
                font_path = font_base.replace(".ttf", "bi.ttf")
            elif bold:
                font_path = font_base.replace(".ttf", "bd.ttf")
            elif italic:
                font_path = font_base.replace(".ttf", "i.ttf")
            else:
                font_path = font_base

            font = ImageFont.truetype(f"static/fonts/{font_path}", font_size)
            d.text((x, y), text, font=font, fill=(0, 0, 0), spacing=spacing)

    # Apply offsets
    dx, dy = template["offsets"]
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
    Appends a record to print-log.json containing the form data and template
    used to generate the label. These are loaded from temp_label_store.
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

    log_entry = {
        "session_id": session_id,
        "count": copies,
        "formdata": used_formdata,
        "label_template": label_template,
        "unix_time": int(datetime.now().timestamp()),
        "time": datetime.now().isoformat()
    }
    logs.append(log_entry)

    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2)

def load_templates():
    """
    Loads all template files in static/label-templates that match label_template*.json,
    returning a dict keyed by each file's 'label' property.
    """
    templates = {}

    # Locate all template files in this directory
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
    templates = load_templates()
    return jsonify(templates)

@app.route('/preview_label', methods=['POST'])
def preview_label():
    """
    Generate/update a single "preview" image in `static/preview_images/`
    for the given session_id. Overwrites the same file each time.
    Also saves 'used_formdata' and 'label_template' in temp_label_store.
    """
    data = request.get_json() or request.form
    session_id = data.get('session_id', '')
    label_data = data.get('label_data', {})
    
    if not session_id:
        return jsonify({"error": "No session_id provided"}), 400

    # Check if user provided a template_name
    chosen_template_name = label_data.get('template_name', '')

    if chosen_template_name:
        # If user selected a template from the dropdown
        all_templates = load_templates()
        if chosen_template_name not in all_templates:
            return jsonify({"error": f"Unknown template_name: {chosen_template_name}"}), 400
        template = all_templates[chosen_template_name]
    else:
        # fallback to default template
        template_path = "static/label-templates/label_template_default.json"
        with open(template_path, 'r', encoding='utf-8') as f:
            base_template = json.load(f)
        template = {
            "name": os.path.basename(template_path),
            **base_template
        }

    # Incorporate offset adjustments
    template['offsets'][0] += int(label_data.get('x-offset', 0))
    template['offsets'][1] += int(label_data.get('y-offset', 0))

    # Identify relevant field names and collect form data
    fieldnames = [field["name"] for field in template['fields']]
    used_formdata = {name: label_data.get(name, '') for name in fieldnames}

    # Optionally log to CSV
    save_to_csv(fieldnames, label_data)

    # Generate the in-memory label
    img = generate_png(template, label_data)

    # Construct the preview file path
    preview_filename = f"preview_{session_id}.png"
    abs_preview_path = os.path.join(app.root_path, PREVIEW_FOLDER, preview_filename)
    img.save(abs_preview_path)

    server_relative_path = f"/{PREVIEW_FOLDER}/{preview_filename}"

    # Store data for later retrieval by /print_label
    temp_label_store[session_id] = {
        "used_formdata": used_formdata,
        "label_template": template,
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
    Simulates printing the preview image for a session.
    In a production environment, would actually print to a printer.
    """
    data = request.get_json() or request.form
    session_id = data.get('session_id', '')
    count = int(data.get('count', 0))
    label_data = data.get('label_data', {})

    if not session_id or count <= 0:
        return jsonify({"error": "Invalid session ID or count"}), 400

    # Store updated label data if provided
    if label_data:
        # Update stored form data with the newest values
        if session_id in temp_label_store:
            temp_label_store[session_id]['used_formdata'] = label_data
        else:
            # Create new entry if this is the first time
            temp_label_store[session_id] = {
                "used_formdata": label_data,
                "date_created": datetime.now().isoformat(),
                "preview_filename": f"preview_{session_id}.png"
            }

    # Log the print job
    append_to_print_log(session_id, count)

    return jsonify({
        "message": f"Printed {count} copies of preview image for session {session_id}."
    })

@app.route('/save_label', methods=['POST'])
def save_label():
    """
    Copies the preview file to generated_labels directory and adds to index.
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

    # Build the dynamic filename from multiple fields
    main_text = entry_data["used_formdata"].get("main_text", "label")
    mid_text = entry_data["used_formdata"].get("midtext", "")
    sub_text = entry_data["used_formdata"].get("subtext", "")

    # Sanitize each field before combining
    sanitized_main = sanitize_string(main_text).lower()
    sanitized_mid = sanitize_string(mid_text).lower()
    sanitized_sub = sanitize_string(sub_text).lower()

    # Combine them with underscores
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    final_filename = f"label_{sanitized_main}_{sanitized_mid}_{sanitized_sub}_{timestamp}.png"
    abs_final_path = os.path.join(app.root_path, FINAL_LABELS_DIR, final_filename)

    # Copy instead of moving so we can still print the preview afterward
    shutil.copyfile(abs_preview_path, abs_final_path)

    new_rel_path = f"/{FINAL_LABELS_DIR}/{final_filename}"

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

@app.route('/search_labels', methods=['POST'])
def search_labels():
    """
    Searches saved labels based on a query string.
    """
    data = request.get_json() or request.form
    query = data.get('query', '').lower()

    if not query:
        return jsonify([])

    # Load the saved index
    index_path = os.path.join(app.root_path, SAVED_INDEX_FILE)
    if not os.path.exists(index_path):
        return jsonify([])

    with open(index_path, 'r', encoding='utf-8') as f:
        records = json.load(f)

    # Search through the records
    results = []
    for record in records:
        form_data = record.get('formdata', {})
        main_text = form_data.get('main_text', '').lower()
        midtext = form_data.get('midtext', '').lower()
        subtext = form_data.get('subtext', '').lower()
        
        # If query matches any of the fields
        if (query in main_text or query in midtext or query in subtext):
            results.append({
                'preview_path': record['filepath'],
                'main_text': form_data.get('main_text', ''),
                'midtext': form_data.get('midtext', ''),
                'subtext': form_data.get('subtext', ''),
                'date_created': record.get('date_created', '')
            })

    # Return only the most recent 20 results
    return jsonify(results[-20:])

# Route to serve static files for previews and generated labels
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/static/preview_images/<path:filename>')
def serve_preview_images(filename):
    return send_from_directory(PREVIEW_FOLDER, filename)

@app.route('/static/generated_labels/<path:filename>')
def serve_generated_labels(filename):
    return send_from_directory(FINAL_LABELS_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True) 