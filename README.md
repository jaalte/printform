# PlantTag Management System

## Overview

The PlantTag Management System is an extension to the PrintForm server that provides a robust solution for tracking, managing, and searching plant tags. It introduces a structured database approach with SQLite, a class-based architecture, and a modern web interface for tag management.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Database Structure](#database-structure)
3. [Core Components](#core-components)
   - [PlantTag Class](#planttag-class)
   - [PlantTagDatabase Class](#planttagdatabase-class)
   - [Helper Functions](#helper-functions)
4. [URL Routes & API Endpoints](#url-routes--api-endpoints)
5. [Tag Manager Web Interface](#tag-manager-web-interface)
6. [Data Migration](#data-migration)
7. [Integration with Existing Code](#integration-with-existing-code)
8. [Installation Guide](#installation-guide)
9. [Usage Guide](#usage-guide)
10. [Technical Implementation Details](#technical-implementation-details)
11. [Troubleshooting](#troubleshooting)

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

### Print Errors

If printing fails:
1. Check that the printer is connected and available
2. Verify that the image path exists on the server
3. Look for detailed error messages in the alert dialog 