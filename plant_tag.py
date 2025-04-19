#!/usr/bin/env python3
import os
import json
import hashlib
import sqlite3
import shutil
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union, Any

class PlantTag:
    """
    A class to represent a plant tag, with methods for serialization, 
    comparison, and tracking print history. This serves as a central database
    for confirmed good tags.
    
    Key features:
    - Unique identification of plant tags based on formdata
    - Tracking of print history
    - Version control for tags (different offset adjustments)
    - Serialization to/from database
    - Easy deduplication
    """
    
    DB_PATH = "plant_tags.db"
    FINAL_LABELS_DIR = 'static/generated_labels'
    
    def __init__(self, 
                 formdata: Dict[str, str], 
                 template: Dict[str, Any], 
                 offset_adjustment: Tuple[int, int] = (0, 0),
                 image_path: Optional[str] = None,
                 tag_id: Optional[int] = None,
                 created_date: Optional[str] = None,
                 confirmed: bool = False):
        """
        Initialize a PlantTag instance.
        
        Args:
            formdata: Dictionary containing form field values
            template: Dictionary containing template configuration
            offset_adjustment: Tuple (x, y) of pixel offsets
            image_path: Path to the saved image file
            tag_id: Database ID (set when saved to DB)
            created_date: ISO format date string
            confirmed: Whether this tag has been confirmed as good (printed multiple times)
        """
        self.formdata = formdata
        self.template = template
        self.offset_adjustment = offset_adjustment
        self.image_path = image_path
        self.tag_id = tag_id
        self.created_date = created_date or datetime.now().isoformat()
        self.confirmed = confirmed
        self.print_history = []
    
    def __eq__(self, other):
        """
        Compare two PlantTag objects for equality.
        Tags are considered equal if their formdata and template are the same.
        The offset_adjustment is not considered for basic equality.
        """
        if not isinstance(other, PlantTag):
            return False
        
        # Compare formdata values
        for key in self.formdata:
            if key not in other.formdata or self.formdata[key] != other.formdata[key]:
                return False
                
        # Compare template name (enough to identify template)
        if self.template.get('label') != other.template.get('label'):
            return False
                
        return True
    
    def is_exact_match(self, other):
        """
        Check if another PlantTag is an exact match, including offset adjustments.
        This means the tags would produce identical output.
        """
        if not self.__eq__(other):
            return False
        
        # Also check offset adjustments
        return self.offset_adjustment == other.offset_adjustment
    
    def create_content_hash(self) -> str:
        """
        Create a hash based on formdata and template to uniquely identify this tag.
        Used for deduplication and lookup.
        """
        content = {
            "formdata": self.formdata,
            "template_label": self.template.get('label', '')
        }
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.md5(content_str.encode('utf-8')).hexdigest()
    
    def create_exact_hash(self) -> str:
        """
        Create a hash including offset adjustment - for exact version control.
        """
        content = {
            "formdata": self.formdata,
            "template_label": self.template.get('label', ''),
            "offset_adjustment": self.offset_adjustment
        }
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.md5(content_str.encode('utf-8')).hexdigest()
    
    def add_print_record(self, copies: int, print_date: Optional[str] = None) -> None:
        """
        Add a print record to this tag's history.
        
        Args:
            copies: Number of copies printed
            print_date: ISO format date string (default: now)
        """
        if print_date is None:
            print_date = datetime.now().isoformat()
            
        self.print_history.append({
            "copies": copies,
            "date": print_date,
            "unix_time": int(datetime.fromisoformat(print_date).timestamp())
        })
        
        # If printing multiple copies, mark as confirmed
        if copies > 1:
            self.confirmed = True
    
    def get_total_prints(self) -> int:
        """Get the total number of copies printed for this tag."""
        return sum(record["copies"] for record in self.print_history)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert PlantTag to a dictionary for serialization."""
        return {
            "tag_id": self.tag_id,
            "formdata": self.formdata,
            "template": self.template,
            "offset_adjustment": self.offset_adjustment,
            "image_path": self.image_path,
            "created_date": self.created_date,
            "confirmed": self.confirmed,
            "print_history": self.print_history,
            "content_hash": self.create_content_hash(),
            "exact_hash": self.create_exact_hash()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlantTag':
        """Create a PlantTag instance from a dictionary."""
        tag = cls(
            formdata=data.get("formdata", {}),
            template=data.get("template", {}),
            offset_adjustment=data.get("offset_adjustment", (0, 0)),
            image_path=data.get("image_path"),
            tag_id=data.get("tag_id"),
            created_date=data.get("created_date"),
            confirmed=data.get("confirmed", False)
        )
        tag.print_history = data.get("print_history", [])
        return tag
    
    @classmethod
    def from_session_data(cls, session_data: Dict[str, Any], 
                          image_path: Optional[str] = None) -> 'PlantTag':
        """
        Create a PlantTag from session data format (as used in temp_label_store).
        
        Args:
            session_data: Dictionary from temp_label_store
            image_path: Optional path to saved image
        """
        return cls(
            formdata=session_data.get("used_formdata", {}),
            template=session_data.get("label_template", {}),
            offset_adjustment=session_data.get("offset_adjustment", (0, 0)),
            image_path=image_path,
            created_date=session_data.get("date_created")
        )
    
    def save_image(self, source_path: str) -> str:
        """
        Save/copy the tag image to the final labels directory with a consistent naming scheme.
        
        Args:
            source_path: Source image path
            
        Returns:
            The new image path
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source image not found: {source_path}")
            
        # Generate a filename based on tag content
        main_text = self.formdata.get("main_text", "unknown")
        mid_text = self.formdata.get("midtext", "")
        sub_text = self.formdata.get("subtext", "")
        
        # Clean up text for filename
        def sanitize_string(s):
            """Removes special characters and replaces spaces with dashes."""
            import re
            return re.sub(r'[^a-zA-Z0-9\s]', '', s).replace(' ', '-').lower()
            
        sanitized_main = sanitize_string(main_text)
        sanitized_mid = sanitize_string(mid_text)
        sanitized_sub = sanitize_string(sub_text)
        
        # Create a unique filename with hash to prevent collisions
        content_hash = self.create_content_hash()[:8]  # Use first 8 chars of hash
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"tag_{sanitized_main}_{sanitized_mid}_{sanitized_sub}_{content_hash}_{timestamp}.png"
        
        # Create the destination path
        dest_path = os.path.join(self.FINAL_LABELS_DIR, filename)
        
        # Copy the image
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copyfile(source_path, dest_path)
        
        # Update the image path
        self.image_path = os.path.join("/", self.FINAL_LABELS_DIR, filename).replace("\\", "/")
        
        return self.image_path


class PlantTagDatabase:
    """
    Handles storage and retrieval of PlantTag objects using SQLite.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize the PlantTagDatabase.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or PlantTag.DB_PATH
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Create the database and tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create the main plant_tags table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plant_tags (
                tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT NOT NULL,
                exact_hash TEXT NOT NULL,
                formdata TEXT NOT NULL,
                template TEXT NOT NULL,
                offset_adjustment TEXT NOT NULL,
                image_path TEXT,
                created_date TEXT NOT NULL,
                confirmed BOOLEAN NOT NULL DEFAULT 0,
                UNIQUE(exact_hash)
            )
            ''')
            
            # Create the print_history table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS print_history (
                print_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_id INTEGER NOT NULL,
                copies INTEGER NOT NULL,
                print_date TEXT NOT NULL,
                unix_time INTEGER NOT NULL,
                FOREIGN KEY (tag_id) REFERENCES plant_tags (tag_id)
            )
            ''')
            
            conn.commit()
    
    def save_tag(self, tag: PlantTag) -> int:
        """
        Save a PlantTag to the database. If a tag with the same exact_hash exists,
        returns the existing tag_id. Otherwise, inserts a new record.
        
        Args:
            tag: The PlantTag to save
            
        Returns:
            The tag_id (either existing or new)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if an exact match exists
            cursor.execute(
                "SELECT tag_id FROM plant_tags WHERE exact_hash = ?",
                (tag.create_exact_hash(),)
            )
            result = cursor.fetchone()
            
            if result:
                # Exact match exists, return existing tag_id
                tag_id = result['tag_id']
                tag.tag_id = tag_id
                return tag_id
            
            # Insert new tag
            cursor.execute('''
            INSERT INTO plant_tags (
                content_hash, exact_hash, formdata, template, 
                offset_adjustment, image_path, created_date, confirmed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                tag.create_content_hash(),
                tag.create_exact_hash(),
                json.dumps(tag.formdata),
                json.dumps(tag.template),
                json.dumps(tag.offset_adjustment),
                tag.image_path,
                tag.created_date,
                1 if tag.confirmed else 0
            ))
            
            tag_id = cursor.lastrowid
            tag.tag_id = tag_id
            
            # Save print history
            for record in tag.print_history:
                cursor.execute('''
                INSERT INTO print_history (
                    tag_id, copies, print_date, unix_time
                ) VALUES (?, ?, ?, ?)
                ''', (
                    tag_id,
                    record["copies"],
                    record["date"],
                    record["unix_time"]
                ))
            
            conn.commit()
            return tag_id
    
    def add_print_record(self, tag_id: int, copies: int, print_date: Optional[str] = None) -> bool:
        """
        Add a print record for a tag.
        
        Args:
            tag_id: The tag's database ID
            copies: Number of copies printed
            print_date: ISO format date string (default: now)
            
        Returns:
            Success status
        """
        if print_date is None:
            print_date = datetime.now().isoformat()
            
        unix_time = int(datetime.fromisoformat(print_date).timestamp())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Add print record
            cursor.execute('''
            INSERT INTO print_history (
                tag_id, copies, print_date, unix_time
            ) VALUES (?, ?, ?, ?)
            ''', (tag_id, copies, print_date, unix_time))
            
            # If printing multiple copies, mark as confirmed
            if copies > 1:
                cursor.execute(
                    "UPDATE plant_tags SET confirmed = 1 WHERE tag_id = ?",
                    (tag_id,)
                )
            
            conn.commit()
            return True
    
    def get_tag_by_id(self, tag_id: int) -> Optional[PlantTag]:
        """
        Retrieve a PlantTag by its database ID.
        
        Args:
            tag_id: The tag's database ID
            
        Returns:
            PlantTag object or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get tag data
            cursor.execute(
                "SELECT * FROM plant_tags WHERE tag_id = ?",
                (tag_id,)
            )
            tag_row = cursor.fetchone()
            
            if not tag_row:
                return None
                
            # Get print history
            cursor.execute(
                "SELECT copies, print_date, unix_time FROM print_history WHERE tag_id = ? ORDER BY unix_time",
                (tag_id,)
            )
            print_history = [
                {
                    "copies": row["copies"],
                    "date": row["print_date"],
                    "unix_time": row["unix_time"]
                }
                for row in cursor.fetchall()
            ]
            
            # Create PlantTag object
            tag = PlantTag(
                formdata=json.loads(tag_row["formdata"]),
                template=json.loads(tag_row["template"]),
                offset_adjustment=json.loads(tag_row["offset_adjustment"]),
                image_path=tag_row["image_path"],
                tag_id=tag_row["tag_id"],
                created_date=tag_row["created_date"],
                confirmed=bool(tag_row["confirmed"])
            )
            tag.print_history = print_history
            
            return tag
    
    def find_tag_by_content(self, formdata: Dict[str, str], 
                            template_label: str) -> List[PlantTag]:
        """
        Find tags that match the given formdata and template label.
        These would be considered the "same tag" but might have different
        offset adjustments.
        
        Args:
            formdata: Dictionary of form values
            template_label: Template label name
            
        Returns:
            List of matching PlantTag objects
        """
        # Create a temporary tag to generate a content hash
        temp_tag = PlantTag(formdata=formdata, template={"label": template_label})
        content_hash = temp_tag.create_content_hash()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Find tags matching content hash
            cursor.execute(
                "SELECT tag_id FROM plant_tags WHERE content_hash = ? ORDER BY created_date DESC",
                (content_hash,)
            )
            
            matching_tags = []
            for row in cursor.fetchall():
                tag = self.get_tag_by_id(row["tag_id"])
                if tag:
                    matching_tags.append(tag)
            
            return matching_tags
    
    def find_exact_tag(self, formdata: Dict[str, str], template_label: str,
                      offset_adjustment: Tuple[int, int]) -> Optional[PlantTag]:
        """
        Find a tag that exactly matches formdata, template, and offset adjustment.
        
        Args:
            formdata: Dictionary of form values
            template_label: Template label name
            offset_adjustment: Tuple of (x, y) offset values
            
        Returns:
            Matching PlantTag or None
        """
        # Create a temporary tag to generate an exact hash
        temp_tag = PlantTag(
            formdata=formdata, 
            template={"label": template_label},
            offset_adjustment=offset_adjustment
        )
        exact_hash = temp_tag.create_exact_hash()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Find tag matching exact hash
            cursor.execute(
                "SELECT tag_id FROM plant_tags WHERE exact_hash = ?",
                (exact_hash,)
            )
            row = cursor.fetchone()
            
            if row:
                return self.get_tag_by_id(row["tag_id"])
            
            return None
    
    def get_all_tags(self, confirmed_only: bool = False, 
                    limit: int = 100, offset: int = 0) -> List[PlantTag]:
        """
        Retrieve all tags (or confirmed-only) with pagination.
        
        Args:
            confirmed_only: Whether to only include confirmed tags
            limit: Maximum number of tags to return
            offset: Number of tags to skip (for pagination)
            
        Returns:
            List of PlantTag objects
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Construct query
            query = "SELECT tag_id FROM plant_tags"
            params = []
            
            if confirmed_only:
                query += " WHERE confirmed = 1"
                
            query += " ORDER BY created_date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            # Execute query
            cursor.execute(query, params)
            
            # Retrieve tags
            tags = []
            for row in cursor.fetchall():
                tag = self.get_tag_by_id(row["tag_id"])
                if tag:
                    tags.append(tag)
            
            return tags
    
    def search_tags(self, search_text: str, limit: int = 100) -> List[PlantTag]:
        """
        Search for tags containing the specified text in formdata.
        
        Args:
            search_text: Text to search for
            limit: Maximum number of results
            
        Returns:
            List of matching PlantTag objects
        """
        search_pattern = f"%{search_text}%"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # SQLite doesn't have native JSON search, so we use LIKE on the JSON string
            # This is not ideal, but works for our simple case
            try:
                cursor.execute('''
                SELECT tag_id FROM plant_tags 
                WHERE formdata LIKE ? 
                ORDER BY created_date DESC 
                LIMIT ?
                ''', (search_pattern, limit))
                
                # Retrieve matching tags
                tags = []
                for row in cursor.fetchall():
                    tag = self.get_tag_by_id(row["tag_id"])
                    if tag:
                        tags.append(tag)
                
                return tags
            except sqlite3.Error as e:
                print(f"SQLite error in search_tags: {e}")
                # Fallback to in-memory filtering if the database query fails
                cursor.execute("SELECT tag_id FROM plant_tags ORDER BY created_date DESC")
                all_tags = []
                for row in cursor.fetchall():
                    tag = self.get_tag_by_id(row["tag_id"])
                    if tag:
                        # Check if search text appears in any formdata value
                        for value in tag.formdata.values():
                            if search_text.lower() in str(value).lower():
                                all_tags.append(tag)
                                break
                
                return all_tags[:limit]
    
    def get_print_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about printed tags.
        
        Returns:
            Dictionary of statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Total tags
            cursor.execute("SELECT COUNT(*) as count FROM plant_tags")
            total_tags = cursor.fetchone()["count"]
            
            # Confirmed tags
            cursor.execute("SELECT COUNT(*) as count FROM plant_tags WHERE confirmed = 1")
            confirmed_tags = cursor.fetchone()["count"]
            
            # Total prints
            cursor.execute("SELECT SUM(copies) as total FROM print_history")
            result = cursor.fetchone()
            total_prints = result["total"] if result["total"] is not None else 0
            
            # Most printed tag
            cursor.execute('''
            SELECT tag_id, SUM(copies) as total_copies 
            FROM print_history 
            GROUP BY tag_id 
            ORDER BY total_copies DESC 
            LIMIT 1
            ''')
            most_printed_row = cursor.fetchone()
            most_printed = None
            if most_printed_row:
                most_printed_tag = self.get_tag_by_id(most_printed_row["tag_id"])
                if most_printed_tag:
                    most_printed = {
                        "tag": most_printed_tag.to_dict(),
                        "copies": most_printed_row["total_copies"]
                    }
            
            return {
                "total_tags": total_tags,
                "confirmed_tags": confirmed_tags,
                "total_prints": total_prints,
                "most_printed": most_printed
            }
    
    def migrate_from_json(self, saved_index_path: str, print_log_path: str) -> int:
        """
        Migrate data from saved-label-index.json and print-log.json to the database.
        
        Args:
            saved_index_path: Path to saved-label-index.json
            print_log_path: Path to print-log.json
            
        Returns:
            Number of tags migrated
        """
        if not os.path.exists(saved_index_path) or not os.path.exists(print_log_path):
            return 0
            
        # Load saved labels
        with open(saved_index_path, 'r', encoding='utf-8') as f:
            saved_labels = json.load(f)
            
        # Load print logs
        with open(print_log_path, 'r', encoding='utf-8') as f:
            print_logs = json.load(f)
            
        # Map session_ids to print logs
        session_print_logs = {}
        for log in print_logs:
            session_id = log.get("session_id", "unknown")
            if session_id not in session_print_logs:
                session_print_logs[session_id] = []
            session_print_logs[session_id].append(log)
        
        # Process saved labels
        migrated_count = 0
        for label_data in saved_labels:
            # Create PlantTag from saved label
            tag = PlantTag(
                formdata=label_data.get("formdata", {}),
                template=label_data.get("label_template", {}),
                image_path=label_data.get("filepath"),
                created_date=label_data.get("date_created") or datetime.now().isoformat()
            )
            
            # Look for matching print logs
            content_hash = tag.create_content_hash()
            for session_id, logs in session_print_logs.items():
                for log in logs:
                    # Basic comparison to match print logs to saved labels
                    log_tag = PlantTag(
                        formdata=log.get("formdata", {}),
                        template=log.get("label_template", {}),
                        offset_adjustment=log.get("offset_adjustment", (0, 0))
                    )
                    
                    if tag == log_tag:
                        # Add print record
                        tag.add_print_record(
                            copies=log.get("count", 1),
                            print_date=log.get("time")
                        )
            
            # Mark as confirmed if printed multiple times
            if tag.get_total_prints() > 1:
                tag.confirmed = True
                
            # Save to database
            self.save_tag(tag)
            migrated_count += 1
        
        return migrated_count


# Helper functions for integration with the main app

def get_or_create_tag_from_session(session_id, session_data, db=None):
    """
    Get an existing tag or create a new one from session data.
    
    Args:
        session_id: The session ID
        session_data: Data from temp_label_store for this session
        db: Optional PlantTagDatabase instance
        
    Returns:
        (tag, is_new) tuple with the PlantTag and whether it's new
    """
    if db is None:
        db = PlantTagDatabase()
    
    # Extract data
    formdata = session_data.get("used_formdata", {})
    template = session_data.get("label_template", {})
    offset_adjustment = session_data.get("offset_adjustment", (0, 0))
    
    # Check if this exact tag exists
    exact_tag = db.find_exact_tag(
        formdata=formdata,
        template_label=template.get("label", ""),
        offset_adjustment=offset_adjustment
    )
    
    if exact_tag:
        return exact_tag, False
    
    # Create new tag
    new_tag = PlantTag.from_session_data(session_data)
    return new_tag, True


def handle_print_request(session_id, session_data, copies, preview_path, db=None):
    """
    Process a print request and update the tag database.
    
    Args:
        session_id: The session ID
        session_data: Data from temp_label_store
        copies: Number of copies to print
        preview_path: Path to the preview image
        db: Optional PlantTagDatabase instance
        
    Returns:
        PlantTag object that was printed
    """
    if db is None:
        db = PlantTagDatabase()
    
    # Get or create tag
    tag, is_new = get_or_create_tag_from_session(session_id, session_data, db)
    
    # Add print record
    tag.add_print_record(copies)
    
    # If printing multiple copies or tag was previously confirmed, save the image
    if copies > 1 or tag.confirmed:
        abs_preview_path = os.path.join(os.getcwd(), preview_path.lstrip('/'))
        tag.save_image(abs_preview_path)
    
    # Save to database
    db.save_tag(tag)
    
    return tag 