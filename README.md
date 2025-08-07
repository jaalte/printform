# PlantTag Management System

## Overview

The PlantTag Management System is an extension to the PrintForm server that provides a robust solution for tracking, managing, and searching plant tags. It introduces a structured database approach with SQLite, a class-based architecture, and a modern web interface for tag management.

**NEW: Auto-Restart System** - The server now includes an intelligent auto-restart system that prevents the search bugs that occur when the server runs for extended periods. The system includes graceful restart handling and a manual restart button in the client interface.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Auto-Restart System](#auto-restart-system)
3. [Database Structure](#database-structure)
4. [Core Components](#core-components)
   - [PlantTag Class](#planttag-class)
   - [PlantTagDatabase Class](#planttagdatabase-class)
   - [Helper Functions](#helper-functions)
5. [URL Routes & API Endpoints](#url-routes--api-endpoints)
6. [Tag Manager Web Interface](#tag-manager-web-interface)
7. [Data Migration](#data-migration)
8. [Integration with Existing Code](#integration-with-existing-code)
9. [Installation Guide](#installation-guide)
10. [Usage Guide](#usage-guide)
11. [Technical Implementation Details](#technical-implementation-details)
12. [Troubleshooting](#troubleshooting)

## Auto-Restart System

### Overview

The auto-restart system addresses search inconsistencies that occur when the server runs for extended periods. It automatically restarts the server every 5 minutes while ensuring critical operations (like saving tags and writing logs) complete safely.

### Key Features

- **Automatic Restart**: Server restarts every 5 minutes to prevent search bugs
- **Graceful Handling**: Uses lock system to prevent restarts during critical operations
- **Manual Restart Button**: Client interface includes a restart button in the top-right corner
- **Operation Tracking**: Shows what operation is currently running when restart is blocked
- **Force Restart Option**: Allows restart even when busy (with user confirmation)

### How It Works

#### Lock System
The system uses a threading lock to prevent restarts during critical operations:

```python
# Global lock to prevent restart during critical operations
restart_lock = threading.Lock()
current_operation = None
restart_timer = None
restart_interval = 300  # 5 minutes in seconds
```

#### Critical Operations Protected
- **Saving Labels**: When writing to `saved-label-index.json`
- **Writing Print Logs**: When writing to `print-log.json`
- **Database Operations**: When adding print records to the database

#### Auto-Restart Timer
The server automatically schedules restarts:

```python
def schedule_restart():
    """Schedule the next auto-restart."""
    global restart_timer
    if restart_timer:
        restart_timer.cancel()
    restart_timer = threading.Timer(restart_interval, perform_restart)
    restart_timer.daemon = True
    restart_timer.start()
```

#### Manual Restart
The client interface includes a restart button that:
- Appears in the top-right corner of the interface
- Provides immediate restart capability
- Shows lock status with user-friendly messages
- Allows force restart when server is busy

### Client Interface Integration

The restart button is positioned in the top-right corner for easy access:

```html
<div class="restart-server-container">
  <div class="restart-server-tab" id="restart-server-btn">
    🔄 Restart Server
  </div>
</div>
```

### Lock Messages

When the server is busy, users see descriptive messages like:
- "The server is waiting for action 'saving label to index' to complete. Restart anyways?"
- "The server is waiting for action 'writing print log' to complete. Restart anyways?"

### Configuration

The restart interval can be adjusted by modifying:

```python
restart_interval = 300  # 5 minutes in seconds
```

### Signal Handling

The system handles restart signals gracefully:

```python
def signal_handler(signum, frame):
    """Handle restart signals gracefully."""
    print(f"[{datetime.now().isoformat()}] Received restart signal, shutting down gracefully...")
    sys.exit(0)
```

## System Architecture

The PlantTag system implements a three-tier architecture:

1. **Data Layer**: SQLite database with two tables for tags and print history
2. **Business Logic Layer**: Python classes and helper functions
3. **Presentation Layer**: Flask API endpoints and HTML/JS web interface

This design provides clear separation of concerns while maintaining the ability to recreate labels pixel-perfectly through comprehensive data storage.

Key architectural features:
- **Content-based Identification**: Tags are identified by their content (formdata + template) using hash functions
- **Version Control**: Multiple versions of the same tag with different offset adjustments can exist
- **Confirmed Tags**: Tags printed in batches (multiple copies) are automatically marked as "confirmed"
- **Client-side Filtering**: Fast, responsive search with automatic background refresh

## Database Structure

The system uses SQLite through the `sqlite3` module, with two main tables:

### plant_tags Table

| Column | Type | Description |
|--------|------|-------------|
| tag_id | INTEGER | Primary key, auto-incrementing |
| content_hash | TEXT | Hash based on formdata and template |
| exact_hash | TEXT | Hash including offset adjustments |
| formdata | TEXT | JSON string of form values |
| template | TEXT | JSON string of the template configuration |
| offset_adjustment | TEXT | JSON string of (x,y) offsets |
| image_path | TEXT | Path to saved PNG image |
| created_date | TEXT | ISO format date string |
| confirmed | BOOLEAN | Whether tag is confirmed (multiple prints) |

### print_history Table

| Column | Type | Description |
|--------|------|-------------|
| print_id | INTEGER | Primary key, auto-incrementing |
| tag_id | INTEGER | Foreign key to plant_tags |
| copies | INTEGER | Number of copies printed |
| print_date | TEXT | ISO format date of printing |
| unix_time | INTEGER | Unix timestamp for sorting |

The database is automatically created when the system first runs, with necessary tables and relationships established.

## Core Components

### PlantTag Class

The `PlantTag` class represents a single plant tag with comprehensive methods for:

- **Equality Comparison**: 
  - `__eq__`: Checks if two tags have the same content (ignoring offset adjustments)
  - `is_exact_match`: Checks if two tags are identical including offset adjustments

- **Hash Generation**:
  - `create_content_hash`: Generates a hash based on formdata and template
  - `create_exact_hash`: Generates a hash including offset adjustments

- **Print History**:
  - `add_print_record`: Adds a print history entry with copies and date
  - `get_total_prints`: Calculates total copies printed

- **Serialization**:
  - `to_dict`: Converts tag to a dictionary for JSON
  - `from_dict`: Class method to create tag from dictionary
  - `from_session_data`: Creates tag from session data format

- **Image Management**:
  - `save_image`: Saves/copies image with consistent naming scheme

#### Key Attributes:

```python
self.formdata = formdata              # Dictionary of form values
self.template = template              # Template configuration
self.offset_adjustment = offset_adjustment  # (x,y) pixel offsets
self.image_path = image_path          # Path to saved image
self.tag_id = tag_id                  # Database ID
self.created_date = created_date      # ISO format creation date
self.confirmed = confirmed            # Whether tag is "confirmed"
self.print_history = []               # List of print records
```

### PlantTagDatabase Class

The `PlantTagDatabase` class handles all database operations:

- **Database Initialization**:
  - `_ensure_db_exists`: Creates tables if they don't exist

- **Tag Management**:
  - `save_tag`: Saves a tag to the database (handles deduplication)
  - `get_tag_by_id`: Retrieves a tag by ID
  - `find_tag_by_content`: Finds tags matching content hash
  - `find_exact_tag`: Finds tag with exact match

- **Print History**:
  - `add_print_record`: Adds a print record for a tag

- **Querying**:
  - `get_all_tags`: Gets all tags with pagination and filtering
  - `search_tags`: Searches for tags containing text
  - `get_print_statistics`: Gets statistics about prints and tags

- **Migration**:
  - `migrate_from_json`: Migrates data from JSON files to database

### Helper Functions

Several helper functions simplify integration with the main application:

- `get_or_create_tag_from_session`: Gets existing tag or creates a new one from session data
- `handle_print_request`: Processes a print request and updates the database

## URL Routes & API Endpoints

The following routes are added to the Flask application:

### Web Interface

- **`/tag-manager`**: Main tag management interface

### API Endpoints

- **`/api/tags`**: Lists tags with filtering and pagination
  - Query parameters: `q`, `confirmed_only`, `limit`, `offset`
  - Response: JSON with tags, count, pagination info

- **`/api/tags/<tag_id>`**: Gets details for a specific tag
  - Response: JSON representation of the tag

- **`/api/tags/<tag_id>/print`**: Prints a specific tag
  - Request body: `copies` (number to print)
  - Response: Print status and updated tag info

- **`/api/tags/stats`**: Gets statistics about tags and prints
  - Response: Counts of total tags, confirmed tags, and total prints

- **`/api/tags/migrate`**: Migrates data from JSON files to database
  - Response: Migration status and count

- **`/migrate-data`**: Convenience route for one-click migration

## Tag Manager Web Interface

The Tag Manager provides a modern, responsive interface for managing plant tags:

### Features

- **Real-time Search**: Client-side filtering as you type
- **Automatic Data Refresh**: Updates data after periods of inactivity
- **Filtering**: Option to view only confirmed tags
- **Pagination**: Efficient viewing of large tag collections
- **Statistics Dashboard**: Shows counts of tags and prints
- **Print Integration**: One-click printing of any tag

### Technical Implementation

- **Client-side Filtering**: Fast search without server requests
- **Debouncing**: Prevents excessive requests during typing
- **Layout Stability**: Prevents jittering when content changes
- **Visual Feedback**: Loading indicators and clear error messages
- **Responsive Design**: Works well on different screen sizes

### State Management

The tag manager maintains a client-side state object:

```javascript
const state = {
    currentPage: 1,
    totalPages: 1,
    limit: 12,
    query: '',
    confirmedOnly: false,
    allTags: [],
    filteredTags: [],
    isInitialLoad: true,
    lastRefreshTime: 0
};
```

This state controls pagination, filtering, and data freshness.

## Data Migration

The system provides tools to migrate existing data from JSON files:

### Migration Process

1. Data is read from `saved-label-index.json` and `print-log.json`
2. Tags are created from saved labels with appropriate attributes
3. Print logs are matched to tags based on content
4. Tags printed multiple times are marked as "confirmed"
5. All data is saved to the SQLite database

### Migration Endpoint

Visit `/migrate-data` in a browser to start migration. This endpoint provides a JSON response with:
- Success status
- Number of tags migrated
- Any error messages if applicable

## Integration with Existing Code

The PlantTag system integrates with the existing PrintForm server with minimal changes:

### Required Imports

```python
from tag_routes import register_tag_routes
from plant_tag import PlantTagDatabase
```

### Database Initialization

```python
# Initialize PlantTag database
plant_tag_db = PlantTagDatabase()
```

### Route Registration

```python
# Register tag management routes
register_tag_routes(app)
```

## Installation Guide

### Prerequisites

- Python 3.6 or higher
- Flask web framework
- SQLite3
- PIL (Pillow) for image processing
- Win32print and Win32ui for Windows printing

### Files Required

1. **`plant_tag.py`**: Core classes and database handling
2. **`tag_routes.py`**: Flask routes for the tag management API
3. **`templates/tag_manager.html`**: Web interface for tag management

### Installation Steps

1. **Place Files in Project Directory**

   Copy the files to your PrintForm project directory:
   ```
   /your_project/
   ├── printform-server.py
   ├── plant_tag.py         # New file
   ├── tag_routes.py        # New file
   ├── templates/
   │   ├── printform-client.html
   │   └── tag_manager.html # New file
   └── static/
       ├── preview_images/
       └── generated_labels/
   ```

2. **Update Main Server File**

   Add the following imports to `printform-server.py`:
   ```python
   from tag_routes import register_tag_routes
   from plant_tag import PlantTagDatabase
   ```

   Initialize the PlantTag database:
   ```python
   # Initialize PlantTag database
   plant_tag_db = PlantTagDatabase()
   ```

   Register the tag routes before starting the server:
   ```python
   if __name__ == '__main__':
       main()
       # Register tag management routes
       register_tag_routes(app)
       app.run(debug=True)
   ```

3. **Migrate Existing Data**

   After starting the server, navigate to:
   ```
   http://localhost:5000/migrate-data
   ```
   
   This will convert your existing JSON data to the new database format.

4. **Verify Installation**

   Access the tag manager to verify everything is working:
   ```
   http://localhost:5000/tag-manager
   ```

## Technical Implementation Details

### Database Implementation

The system uses SQLite with prepared statements to prevent SQL injection. Some key technical details:

#### Database Connection Management

```python
with sqlite3.connect(self.db_path) as conn:
    conn.row_factory = sqlite3.Row  # Enable dictionary-like row access
    cursor = conn.cursor()
    # ... SQL operations ...
    conn.commit()  # Auto-commits on successful exit from with block
```

#### Hashing Strategy

Two-level hashing strategy enables efficient lookup and deduplication:

```python
def create_content_hash(self):
    content = {
        "formdata": self.formdata,
        "template_label": self.template.get('label', '')
    }
    content_str = json.dumps(content, sort_keys=True)
    return hashlib.md5(content_str.encode('utf-8')).hexdigest()
```

This makes it possible to find "similar" tags with different offsets.

### Client-Side Search Implementation

The search is optimized using a debouncing technique:

```javascript
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}
```

This prevents excessive searches while typing, providing a smooth user experience.

### Auto-Refresh Strategy

Data freshness is maintained through:

1. **Timestamp Tracking**: Records when data was last fetched
   ```javascript
   state.lastRefreshTime = Date.now();
   ```

2. **Inactivity Detection**: Listens for user events
   ```javascript
   document.addEventListener('click', registerUserActivity);
   document.addEventListener('keypress', registerUserActivity);
   document.addEventListener('scroll', registerUserActivity);
   ```

3. **Auto-Refresh Timer**: Refreshes after inactivity
   ```javascript
   autoRefreshTimer = setTimeout(() => {
       loadTags(true); // Force refresh
   }, AUTO_REFRESH_INTERVAL);
   ```

### Image Processing

When saving images, a consistent naming scheme uses a combination of:
- Main text, mid text, and subtext from the form data
- A content hash fragment for uniqueness
- A timestamp

This ensures images are organized logically while preventing collisions.

## Usage Guide

### Viewing and Managing Tags

1. Start the PrintForm server
2. Visit `/tag-manager` in your browser
3. Use the search box to find specific tags
4. Check "Show confirmed tags only" to filter for confirmed tags
5. Click "Print" on any tag to print a copy

### Printing Flow

1. When printing multiple copies, tags are automatically marked as "confirmed"
2. These confirmed tags represent your "good" tags with correct offset adjustments
3. All print history is tracked for future reference

### Search Tips

- Search is performed across all fields (main_text, midtext, subtext, etc.)
- Results update in real-time as you type
- The interface automatically refreshes data after periods of inactivity

## Troubleshooting

### Auto-Restart System Issues

If you encounter issues with the auto-restart system:

1. **Server Not Restarting**: Check the console output for restart messages. The server should log restart attempts every 5 minutes.

2. **Restart Button Not Working**: 
   - Check browser console for JavaScript errors
   - Verify the server is running and accessible
   - Try refreshing the page

3. **Server Stuck in Lock**: If the server appears to be stuck:
   - Check console for lock messages
   - Wait for the current operation to complete
   - Use the force restart option if necessary

4. **Search Still Hanging**: If search issues persist despite auto-restart:
   - The auto-restart should prevent this, but if it occurs, use the manual restart button
   - Check if the restart interval needs adjustment (currently 5 minutes)

### Database Issues

If you encounter database problems:
1. Check that the `plant_tags.db` file exists and has the correct permissions
2. Try using the SQLite command-line tool to inspect the database directly
3. If the database becomes corrupted, delete it and use `/migrate-data` to rebuild from JSON

### Search Problems

If search doesn't work properly:
1. Check the browser console for JavaScript errors
2. Try refreshing the page to reload all data
3. Clear your browser cache if old JavaScript is cached
4. **NEW**: Use the restart button if search hangs - this is the primary fix for search issues

### Print Errors

If printing fails:
1. Check that the printer is connected and available
2. Verify that the image path exists on the server
3. Look for detailed error messages in the alert dialog

### Auto-Restart Configuration

To adjust the auto-restart behavior:

1. **Change Restart Interval**: Modify `restart_interval = 300` in `printform-server.py` (value in seconds)
2. **Disable Auto-Restart**: Comment out the `schedule_restart()` call in the `main()` function
3. **Adjust Lock Timeout**: Modify the timeout values in `perform_restart()` and `restart_server()` functions 