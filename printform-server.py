#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify, send_from_directory
from PIL import Image, ImageDraw, ImageFont, ImageWin
import os
import csv
import json
import re
import codecs
import win32print
import win32ui
from datetime import datetime
import random
import string

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

# Paths for your base image + label JSON
label_base_name = 'static/label-templates/label_base.png'
label_template_name = 'static/label-templates/label_template.json'

###############################################################################
# A dictionary to remember each user's session data:
#   key = session_id
#   val = {
#       "formdata": { ...latest fields... },
#       "label_template": { ... },
#       "date_created": "YYYY-MM-DDTHH:MM:SS",
#       "preview_filename": "preview_<session_id>.png",
#       "printer_dpi": 305,  # if needed
#       "recommended_name": "whatever_filename_you_want.png"
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
    """Adds the form values to print_history.csv."""
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
    the template and request form data.
    """
    img = Image.open(label_base_name)
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

            # Build the actual font path from font_base
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
    img = offset_image(img, dx, dy)
    return img

def print_label_file(image_path, copies):
    """Prints the given image `copies` times on Windows using win32print."""
    if copies <= 0:
        return  # ignore zero or negative

    abs_path = os.path.join(app.root_path, image_path.lstrip('/'))
    if not os.path.exists(abs_path):
        # If file doesn't exist, just return
        return

    hprinter = win32print.OpenPrinter(PRINTER_NAME)
    printer_dc = win32ui.CreateDC()
    printer_dc.CreatePrinterDC(PRINTER_NAME)

    dpi_x = printer_dc.GetDeviceCaps(88)  # HORZRES
    dpi_y = printer_dc.GetDeviceCaps(90)  # VERTRES

    image = Image.open(abs_path)

    # Example dimension: 5" x 1"
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

def append_to_saved_index(entry):
    """
    Appends a record to saved-label-index.json, creating if needed.
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
    """
    session_id = request.form.get('session_id', '')
    if not session_id:
        return jsonify({"error": "No session_id provided"}), 400

    # Load label template
    with open(label_template_name, 'r') as f:
        base_template = json.load(f)
    # Put 'name' first
    template = {
        "name": os.path.basename(label_template_name),
        **base_template
    }

    # Offsets
    template['offsets'][0] += int(request.form.get('x-offset', 0))
    template['offsets'][1] += int(request.form.get('y-offset', 0))

    # Identify field names
    fieldnames = [field["name"] for field in template['fields']]
    formdata = {name: request.form.get(name, '') for name in fieldnames}

    # Save to CSV if desired
    save_to_csv(fieldnames)

    # Generate the label in memory
    img = generate_png(template)

    # Single preview file path
    preview_filename = f"preview_{session_id}.png"
    abs_preview_path = os.path.join(app.root_path, PREVIEW_FOLDER, preview_filename)

    # Save/overwrite
    img.save(abs_preview_path)

    # Build a server-relative path with forward slashes
    server_relative_path = '/' + os.path.relpath(abs_preview_path, app.root_path)
    server_relative_path = server_relative_path.replace('\\', '/')

    # Store all data in temp_label_store for this session
    temp_label_store[session_id] = {
        "formdata": formdata,
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
    Expects:
      session_id,
      count
    """
    data = request.get_json() or request.form
    session_id = data.get('session_id', '')
    count = int(data.get('count', 0))

    if not session_id or count <= 0:
        return jsonify({"message": "Nothing to print."}), 200

    # Construct the path: /static/preview_images/preview_<session_id>.png
    preview_filename = f"preview_{session_id}.png"
    server_relative_path = f"/{PREVIEW_FOLDER}/{preview_filename}"
    print_label_file(server_relative_path, count)

    return jsonify({
        "message": f"Printed {count} copies of preview image for session {session_id}."
    })

@app.route('/save_label', methods=['POST'])
def save_label():
    """
    Moves the single preview file for this session from `preview_images` to
    `static/generated_labels/` and appends an entry to saved-label-index.json.
    """
    data = request.get_json() or request.form
    session_id = data.get('session_id', '')

    if not session_id:
        return jsonify({"error": "No session_id provided"}), 400

    preview_filename = f"preview_{session_id}.png"
    abs_preview_path = os.path.join(app.root_path, PREVIEW_FOLDER, preview_filename)

    if not os.path.exists(abs_preview_path):
        return jsonify({"error": "Preview file not found."}), 404

    # Build final name. If you want something dynamic from formdata, do it here.
    # For example, use the main_text if available:
    entry_data = temp_label_store.get(session_id, None)
    if not entry_data:
        # If lost, fallback
        entry_data = {
            "formdata": {},
            "label_template": {},
            "date_created": datetime.now().isoformat()
        }

    # Example: build a name from the formdata
    main_text = entry_data["formdata"].get("main_text", "label")
    sanitized_main_text = sanitize_string(main_text).lower()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    final_filename = f"label_{sanitized_main_text}_{timestamp}.png"

    abs_final_path = os.path.join(app.root_path, FINAL_LABELS_DIR, final_filename)
    os.rename(abs_preview_path, abs_final_path)

    new_rel_path = '/' + os.path.relpath(abs_final_path, app.root_path)
    new_rel_path = new_rel_path.replace('\\', '/')

    # Build a record for saved-label-index
    record = {
        "filepath": new_rel_path,
        "date_created": entry_data["date_created"],
        "formdata": entry_data["formdata"],
        "label_template": entry_data["label_template"]
    }
    append_to_saved_index(record)

    return jsonify({
        "message": f"Label saved to {new_rel_path}",
        "saved_path": new_rel_path
    })

# Optional route if you want to let users manually download
@app.route('/download_image/<path:filename>')
def download_image(filename):
    return send_from_directory(FINAL_LABELS_DIR, filename, as_attachment=True)

# If you want to serve the preview folder directly for debugging
@app.route('/static/preview_images/<path:filename>')
def serve_preview_images(filename):
    return send_from_directory(PREVIEW_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
