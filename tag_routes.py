#!/usr/bin/env python3
"""
Additional Flask routes for the PlantTag management system.
These routes provide API endpoints for the tag_manager.html interface.

To use these routes, import and register them with your Flask app:

```python
from tag_routes import register_tag_routes
register_tag_routes(app)
```
"""

from flask import jsonify, request, render_template, send_from_directory
import os
import sqlite3
from datetime import datetime
from plant_tag import PlantTag, PlantTagDatabase, handle_print_request

def register_tag_routes(app):
    """
    Register all the tag management routes with the Flask app.
    
    Args:
        app: Flask application instance
    """
    
    @app.route('/tag-manager')
    def tag_manager():
        """Serve the tag management interface."""
        return render_template('tag_manager.html')
    
    @app.route('/api/tags')
    def get_tags():
        """
        API endpoint to get tags with filtering and pagination.
        
        Query parameters:
        - q: Search query
        - confirmed_only: Whether to only include confirmed tags
        - limit: Maximum number of tags to return
        - offset: Number of tags to skip (for pagination)
        """
        try:
            search_query = request.args.get('q', '')
            confirmed_only = request.args.get('confirmed_only', '').lower() == 'true'
            limit = int(request.args.get('limit', 20))
            offset = int(request.args.get('offset', 0))
            
            db = PlantTagDatabase()
            
            # Get total count (for pagination)
            total = 0
            with sqlite3.connect(db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if confirmed_only:
                    total_query = "SELECT COUNT(*) as count FROM plant_tags WHERE confirmed = 1"
                    params = []
                else:
                    total_query = "SELECT COUNT(*) as count FROM plant_tags"
                    params = []
                    
                if search_query:
                    # SQLite LIKE with JSON requires special handling
                    # We're searching in formdata which is a JSON string
                    if len(params) > 0:
                        total_query += " AND formdata LIKE ?"
                    else:
                        total_query += " WHERE formdata LIKE ?"
                    params.append(f"%{search_query}%")
                
                cursor.execute(total_query, params)
                row = cursor.fetchone()
                if row:
                    total = row["count"]
            
            # Get tags based on search and filters
            tags = []
            if search_query:
                # Fixed search implementation
                tags = db.search_tags(search_query, limit)
                if confirmed_only:
                    tags = [tag for tag in tags if tag.confirmed]
            else:
                tags = db.get_all_tags(confirmed_only, limit, offset)
            
            # Return results
            return jsonify({
                "tags": [tag.to_dict() for tag in tags],
                "count": len(tags),
                "total": total,
                "page": offset // limit + 1 if limit > 0 else 1,
                "pages": (total + limit - 1) // limit if limit > 0 else 1
            })
        except Exception as e:
            import traceback
            print(f"Error in get_tags: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                "error": f"Error retrieving tags: {str(e)}",
                "tags": [],
                "count": 0,
                "total": 0
            }), 500
    
    @app.route('/api/tags/<int:tag_id>')
    def get_tag(tag_id):
        """Get details for a specific tag."""
        try:
            db = PlantTagDatabase()
            tag = db.get_tag_by_id(tag_id)
            
            if not tag:
                return jsonify({"error": f"Tag with ID {tag_id} not found"}), 404
            
            return jsonify(tag.to_dict())
        except Exception as e:
            return jsonify({"error": f"Error retrieving tag #{tag_id}: {str(e)}"}), 500
    
    @app.route('/api/tags/<int:tag_id>/print', methods=['POST'])
    def print_tag(tag_id):
        """
        Print a specific tag.
        
        Request body:
        - copies: Number of copies to print
        """
        try:
            data = request.get_json() or {}
            copies = int(data.get('copies', 1))
            
            if copies <= 0:
                return jsonify({"error": "Invalid number of copies"}), 400
                
            db = PlantTagDatabase()
            tag = db.get_tag_by_id(tag_id)
            
            if not tag:
                return jsonify({"error": f"Tag with ID {tag_id} not found"}), 404
                
            # Add print record
            db.add_print_record(tag_id, copies)
            
            # Get updated tag
            tag = db.get_tag_by_id(tag_id)
            
            # Perform the actual printing
            if tag.image_path:
                try:
                    # Import the main module - this avoids the hyphen issue in module names
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("printform_server", 
                                                                 os.path.join(os.getcwd(), "printform-server.py"))
                    printform_server = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(printform_server)
                    
                    # Now use the print_label_file function
                    # Convert relative path to absolute
                    abs_path = os.path.join(os.getcwd(), tag.image_path.lstrip('/'))
                    
                    if os.path.exists(abs_path):
                        printform_server.print_label_file(tag.image_path, copies)
                        message = f"Printed {copies} copies of tag #{tag_id}"
                    else:
                        message = f"Warning: Image file not found at {abs_path}. Tag #{tag_id} recorded as printed {copies} times, but no physical print was made."
                except Exception as e:
                    message = f"Error printing tag: {str(e)}. Tag #{tag_id} recorded as printed {copies} times, but no physical print was made."
            else:
                message = f"Warning: No image path for tag #{tag_id}. Print recorded but no physical print was made."
            
            return jsonify({
                "message": message,
                "tag": tag.to_dict(),
                "total_prints": tag.get_total_prints()
            })
        except ImportError as e:
            return jsonify({"error": f"Error importing print_label_file function: {str(e)}"}), 500
        except Exception as e:
            return jsonify({"error": f"Error printing tag #{tag_id}: {str(e)}"}), 500
    
    @app.route('/api/tags/stats')
    def get_tag_stats():
        """Get statistics about tags and prints."""
        try:
            db = PlantTagDatabase()
            stats = db.get_print_statistics()
            return jsonify(stats)
        except Exception as e:
            return jsonify({"error": f"Error retrieving tag statistics: {str(e)}"}), 500
    
    @app.route('/api/tags/migrate', methods=['POST'])
    def migrate_tags():
        """
        Migrate data from JSON files to the database.
        
        This is typically a one-time operation when first setting up
        the PlantTag system on an existing installation.
        """
        try:
            db = PlantTagDatabase()
            saved_index_path = os.path.join(app.root_path, "saved-label-index.json")
            print_log_path = os.path.join(app.root_path, "print-log.json")
            
            if not os.path.exists(saved_index_path):
                return jsonify({"error": f"Saved index file not found at: {saved_index_path}"}), 404
                
            if not os.path.exists(print_log_path):
                return jsonify({"error": f"Print log file not found at: {print_log_path}"}), 404
            
            count = db.migrate_from_json(saved_index_path, print_log_path)
            
            return jsonify({
                "message": f"Migration complete. {count} tags migrated to database.",
                "tags_migrated": count
            })
        except Exception as e:
            return jsonify({"error": f"Error during migration: {str(e)}"}), 500

    return app 