from flask import Blueprint, request, jsonify, send_from_directory
from ..models.label import LabelSession
from ..services.label_generator import LabelGenerator
from ..services.printer_service import PrinterService
from ..services.storage_service import StorageService
from ..services.template_service import TemplateService
from ..config.settings import PREVIEW_FOLDER, FINAL_LABELS_DIR
import os

label_routes = Blueprint('label', __name__)

# In-memory store for active sessions
temp_label_store = {}

@label_routes.route('/preview_label', methods=['POST'])
def preview_label():
    """Generate/update a preview image for the given session."""
    session_id = request.form.get('session_id', '')
    if not session_id:
        return jsonify({"error": "No session_id provided"}), 400

    # Get template
    chosen_template_name = request.form.get('template_name', '')
    try:
        template = TemplateService.get_template(chosen_template_name)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Incorporate offset adjustments
    template.offsets[0] += int(request.form.get('x-offset', 0))
    template.offsets[1] += int(request.form.get('y-offset', 0))

    # Get form data
    fieldnames = [field.name for field in template.fields]
    used_formdata = {name: request.form.get(name, '') for name in fieldnames}

    # Generate and save preview
    img = LabelGenerator.generate_png(template, used_formdata)
    preview_path = LabelGenerator.save_preview(img, session_id)

    # Store session data
    session = LabelSession.create(session_id, used_formdata, template)
    temp_label_store[session_id] = session

    return jsonify({
        "message": f"Preview updated for session {session_id}.",
        "image_path": f"/static/preview_images/{session.preview_filename}"
    })

@label_routes.route('/print_label', methods=['POST'])
def print_label():
    """Print the preview image for a session."""
    data = request.get_json() or request.form
    session_id = data.get('session_id', '')
    count = int(data.get('count', 0))

    if not session_id or count <= 0:
        return jsonify({"message": "Nothing to print."}), 200

    session = temp_label_store.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    preview_path = f"{PREVIEW_FOLDER}/{session.preview_filename}"
    try:
        PrinterService.print_label(preview_path, count, session)
        return jsonify({
            "message": f"Printed {count} copies of preview image for session {session_id}."
        })
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

@label_routes.route('/save_label', methods=['POST'])
def save_label():
    """Save the preview image as a permanent label."""
    data = request.get_json() or request.form
    session_id = data.get('session_id', '')

    if not session_id:
        return jsonify({"error": "No session_id provided"}), 400

    session = temp_label_store.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    preview_path = f"{PREVIEW_FOLDER}/{session.preview_filename}"
    try:
        final_path = StorageService.save_label(preview_path, session)
        return jsonify({
            "message": f"Label saved to {final_path}",
            "saved_path": f"/static/generated_labels/{os.path.basename(final_path)}"
        })
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404

@label_routes.route('/download_image/<path:filename>')
def download_image(filename):
    """Download a saved image."""
    return send_from_directory(FINAL_LABELS_DIR, filename, as_attachment=True)

@label_routes.route('/static/preview_images/<path:filename>')
def serve_preview_images(filename):
    """Serve preview images."""
    return send_from_directory(PREVIEW_FOLDER, filename) 