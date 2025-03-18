import json
import os
import shutil
from datetime import datetime
from typing import Dict, List
from ..config.settings import (
    SAVED_INDEX_FILE, PRINT_LOG_FILE, FINAL_LABELS_DIR,
    PREVIEW_FOLDER
)
from ..models.label import LabelSession

class StorageService:
    @staticmethod
    def load_saved_index() -> List[Dict]:
        """Loads the saved label index file."""
        if os.path.exists(SAVED_INDEX_FILE):
            with open(SAVED_INDEX_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    @staticmethod
    def append_to_saved_index(entry: Dict) -> None:
        """Appends a record to saved-label-index.json."""
        records = StorageService.load_saved_index()
        records.append(entry)
        with open(SAVED_INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2)

    @staticmethod
    def load_print_log() -> List[Dict]:
        """Loads the print log file."""
        if os.path.exists(PRINT_LOG_FILE):
            with open(PRINT_LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    @staticmethod
    def log_print_job(session: LabelSession, copies: int) -> None:
        """Logs a print job to print-log.json."""
        logs = StorageService.load_print_log()
        log_entry = {
            "session_id": session.session_id,
            "count": copies,
            "formdata": session.used_formdata,
            "label_template": session.label_template.__dict__,
            "unix_time": int(datetime.now().timestamp()),
            "time": datetime.now().isoformat()
        }
        logs.append(log_entry)
        with open(PRINT_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2)

    @staticmethod
    def save_label(preview_path: str, session: LabelSession) -> str:
        """Saves a label from preview to final storage."""
        if not os.path.exists(preview_path):
            raise FileNotFoundError("Preview file not found.")

        # Build filename from form data
        from ..utils.string_utils import sanitize_string
        main_text = session.used_formdata.get("main_text", "label")
        mid_text = session.used_formdata.get("midtext", "")
        sub_text = session.used_formdata.get("subtext", "")

        sanitized_main = sanitize_string(main_text).lower()
        sanitized_mid = sanitize_string(mid_text).lower()
        sanitized_sub = sanitize_string(sub_text).lower()

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        final_filename = f"label_{sanitized_main}_{sanitized_mid}_{sanitized_sub}_{timestamp}.png"
        final_path = os.path.join(FINAL_LABELS_DIR, final_filename)

        # Copy preview to final location
        shutil.copyfile(preview_path, final_path)

        # Create index entry
        record = {
            "filepath": f"/static/generated_labels/{final_filename}",
            "date_created": session.date_created.isoformat(),
            "formdata": session.used_formdata,
            "label_template": session.label_template.__dict__
        }
        StorageService.append_to_saved_index(record)

        return final_path