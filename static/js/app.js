class App {
    constructor() {
        // Initialize the EventBus first if it doesn't exist
        if (!window.eventBus) {
            window.eventBus = new EventBus();
        }
        
        // Initialize modules
        this.modules = {
            editor: new EditorModule(document.getElementById('editor-module')),
            search: new SearchModule(document.getElementById('search-module')),
            queue: new QueueModule(document.getElementById('queue-module'))
        };
        
        this.showToast = this.showToast.bind(this);
        
        // Set up inter-module communication
        this.setupEventSubscriptions();
    }

    setupEventSubscriptions() {
        // Handle loading data from search into editor
        window.eventBus.subscribe('loadInEditor', (data) => {
            if (this.modules.editor) {
                this.modules.editor.loadData(data);
            }
        });
    }

    showToast(msg) {
        const toastMessage = document.getElementById('toast-message');
        toastMessage.textContent = msg;
        toastMessage.style.display = 'block';
        setTimeout(() => {
            toastMessage.style.display = 'none';
        }, 3000);
    }
}

// Generate a random session ID on page load
window.sessionId = Array.from(crypto.getRandomValues(new Uint8Array(8)))
    .map(b => b.toString(16).padStart(2, '0')).join('');

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
