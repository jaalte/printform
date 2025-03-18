import os

# Flask app configuration
FLASK_APP_NAME = 'printform'
DEBUG = True

# Printer configuration
PRINTER_NAME = "TEC B-SX5T (305 dpi)"

# Directory paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PREVIEW_FOLDER = os.path.join(BASE_DIR, 'static', 'preview_images')
FINAL_LABELS_DIR = os.path.join(BASE_DIR, 'static', 'generated_labels')
TEMPLATE_DIR = os.path.join(BASE_DIR, 'static', 'label-templates')

# File paths
SAVED_INDEX_FILE = 'saved-label-index.json'
PRINT_LOG_FILE = 'print-log.json'
DEFAULT_TEMPLATE = os.path.join(TEMPLATE_DIR, 'label_template_default.json')

# Create necessary directories
os.makedirs(PREVIEW_FOLDER, exist_ok=True)
os.makedirs(FINAL_LABELS_DIR, exist_ok=True)