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

###############################################################################
# CONFIG / PATHS
###############################################################################
app = Flask(__name__)

# Adjust printer name to match your Windows printer
PRINTER_NAME = "TEC B-SX5T (305 dpi)"

# Single preview folder and file naming for each session
PREVIEW_FOLDER = 'static/preview_images'
os.makedirs(PREVIEW_FOLDER, exist_ok=True)

# Where permanent files are saved if user chooses "Save Label"
FINAL_LABELS_DIR = 'static/generated_labels'
os.makedirs(FINAL_LABELS_DIR, exist_ok=True)

# Index file that tracks all saved labels
SAVED_INDEX_FILE = 'saved-label-index.json'

# Print log file that will track print jobs
PRINT_LOG_FILE = 'print-log.json'

# Paths for label template JSON
label_template_path = 'static/label-templates/label_template.json'

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

def save_to_csv(fieldnames):
    """Adds the form values to print_history.csv, if desired."""
    with open('print_history.csv', mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if csvfile.tell() == 0:
            writer.writeheader()
        values = [request.form.get(name, '') for name in fieldnames]
        values_dict = dict(zip(fieldnames, values))
        writer.writerow(values_dict)

def generate_png(template):
    """
    Generates the label image in memory according to
    the template and request.form data.
    """
    label_base_path = template['base_image'] or "static/label-templates/label_base.png"
    
    img = Image.open(label_base_path)
    d = ImageDraw.Draw(img)

    for field in template['fields']:
        name = field['name']
        x, y = field['x'], field['y']
        data = field['data']
        text = request.form.get(name, '')

        if data['type'] == 'text':
            font_base = data['style']['font-base']
            font_size = data['style']['size']
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

            font = ImageFont.truetype(font_path, font_size)
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
        "formdata": used_formdata,        # the data used in generate_png
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

@app.route('/preview_label', methods=['POST'])
def preview_label():
    """
    Generate/update a single "preview" image in `static/preview_images/`
    for the given session_id. Overwrites the same file each time.
    Also saves 'used_formdata' and 'label_template' in temp_label_store.
    """
    session_id = request.form.get('session_id', '')
    if not session_id:
        return jsonify({"error": "No session_id provided"}), 400

    # Load label template
    with open(label_template_path, 'r') as f:
        base_template = json.load(f)

    template = {
        "name": os.path.basename(label_template_path),
        **base_template
    }

    # Incorporate offset adjustments
    template['offsets'][0] += int(request.form.get('x-offset', 0))
    template['offsets'][1] += int(request.form.get('y-offset', 0))

    # Identify relevant field names
    fieldnames = [field["name"] for field in template['fields']]
    used_formdata = {name: request.form.get(name, '') for name in fieldnames}

    # Optionally log to CSV
    save_to_csv(fieldnames)

    # Generate the in-memory label
    img = generate_png(template)

    # Construct the preview file path
    preview_filename = f"preview_{session_id}.png"
    abs_preview_path = os.path.join(app.root_path, PREVIEW_FOLDER, preview_filename)
    img.save(abs_preview_path)

    server_relative_path = '/' + os.path.relpath(abs_preview_path, app.root_path)
    server_relative_path = server_relative_path.replace('\\', '/')

    # Store data for later retrieval by /print_label
    temp_label_store[session_id] = {
        "used_formdata": used_formdata,       # data used to generate the label
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
    Prints the single preview image for a session, repeated 'count' times.
    Uses the form data & template from temp_label_store[session_id].
    """
    data = request.get_json() or request.form
    session_id = data.get('session_id', '')
    count = int(data.get('count', 0))

    if not session_id or count <= 0:
        return jsonify({"message": "Nothing to print."}), 200

    preview_filename = f"preview_{session_id}.png"
    server_relative_path = f"/{PREVIEW_FOLDER}/{preview_filename}"
    print_label_file(server_relative_path, count, session_id=session_id)

    return jsonify({
        "message": f"Printed {count} copies of preview image for session {session_id}."
    })

@app.route('/save_label', methods=['POST'])
def save_label():
    """
    Copies the single preview file for this session from preview_images to
    static/generated_labels, then appends an entry to saved-label-index.json.
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

    # Combine them with underscores (skip fields if you prefer)
    # Here, we include them all in order:
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

if __name__ == '__main__':
    app.run(debug=True)
