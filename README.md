# Plant Tag Printer Application

A modern web application for managing and printing plant tags, featuring a modular architecture with real-time updates and an efficient three-panel layout.

## System Architecture

The application is built using a modular architecture with three main components that communicate through an event bus system. The interface is divided into three simultaneously visible panels for maximum efficiency:

```
+----------------+----------------+
|                |    Search     |
|    Editor      +----------------+
|                |    Queue      |
+----------------+----------------+
```

### Core Components

#### EventBus (`static/js/EventBus.js`)
- Central communication system that enables module-to-module interaction
- Implements a publish-subscribe pattern
- Allows modules to operate independently while maintaining synchronized state

### Modules

#### 1. Editor Module (`static/modules/editor/editor.js`)
**Purpose**: Primary interface for creating and editing plant tags
- Located in the left panel (50% of screen width)
- Provides form inputs for plant tag data
- Supports template selection and customization
- Real-time preview of tag layout
- Validation of input data

#### 2. Search Module (`static/modules/search/search.js`)
**Purpose**: Quick access to existing plant tag templates and saved tags
- Located in the top-right quarter
- Search functionality with filters
- Display of search results in a scrollable list
- Preview capabilities for existing tags
- Quick-load functionality to editor

#### 3. Queue Module (`static/modules/queue/queue.js`)
**Purpose**: Manages the printing queue and print jobs
- Located in the bottom-right quarter
- Displays current queue status
- Shows print job progress
- Allows queue management (reorder, remove, pause)
- Print status notifications

### File Structure

```
├── templates/
│   └── printform-client.html    # Main HTML template
├── static/
│   ├── main.css                 # Global styles and layout
│   ├── js/
│   │   ├── EventBus.js         # Core communication system
│   │   └── app.js              # Main application logic
│   └── modules/
│       ├── editor/
│       │   ├── editor.js
│       │   └── editor.css
│       ├── search/
│       │   ├── search.js
│       │   └── search.css
│       └── queue/
│           ├── queue.js
│           └── queue.css
└── README.md                    # This documentation
```

### Styling and Layout

The application features a modern, clean design with:
- Responsive layout that maintains optimal proportions
- Each module contained in a floating card with subtle shadows
- Custom scrollbars for better visual integration
- Light color scheme with clear visual hierarchy
- Consistent spacing and padding throughout

#### CSS Structure
- `main.css`: Global styles, layout grid, and common components
- Module-specific CSS files for encapsulated styling
- Standardized form elements and interactive components
- Responsive design considerations

### User Interface Features

1. **Global Features**
   - Toast notification system for user feedback
   - Consistent styling across all modules
   - Custom scrollbars for better UX
   - Responsive buttons and form elements

2. **Editor Panel**
   - Form inputs for plant data
   - Template selection interface
   - Real-time preview
   - Validation feedback

3. **Search Panel**
   - Search input field
   - Filter options
   - Results display
   - Quick actions

4. **Queue Panel**
   - Active queue display
   - Job progress indicators
   - Queue management controls
   - Status updates

## Technical Implementation

### Event Communication

Modules communicate through the EventBus using predefined events:
- `tag.created`: When a new tag is created in the editor
- `tag.updated`: When an existing tag is modified
- `queue.updated`: When the print queue changes
- `search.results`: When new search results are available

### Styling Methodology

The application uses a systematic approach to styling:
- BEM-like class naming convention
- Modular CSS with component isolation
- Consistent spacing using a 4px/8px grid
- Standardized color palette
- Reusable component classes

### Browser Compatibility

The application is designed to work in modern browsers with support for:
- Flexbox layout
- CSS Grid
- Custom scrollbars
- CSS animations
- Modern JavaScript features

## Getting Started

1. Clone the repository
2. Ensure all static files are properly served
3. Open `printform-client.html` in a modern web browser

## Future Enhancements

Planned features and improvements:
- Batch tag creation
- Template management system
- Print preview functionality
- Queue export/import
- Advanced search filters
- User preferences storage 