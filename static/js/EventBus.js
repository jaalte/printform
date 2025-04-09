class EventBus {
    constructor() {
        this.subscribers = {};
        
        // Create and assign the singleton instance
        if (!window.eventBus) {
            window.eventBus = this;
        }
    }

    /**
     * Subscribe to an event
     * @param {string} event - Event name to subscribe to 
     * @param {function} callback - Function to call when event is published
     */
    subscribe(event, callback) {
        if (!this.subscribers[event]) {
            this.subscribers[event] = [];
        }
        this.subscribers[event].push(callback);
        return () => this.unsubscribe(event, callback); // Return unsubscribe function
    }

    /**
     * Unsubscribe from an event
     * @param {string} event - Event name to unsubscribe from
     * @param {function} callback - Callback to remove
     */
    unsubscribe(event, callback) {
        if (this.subscribers[event]) {
            this.subscribers[event] = this.subscribers[event].filter(cb => cb !== callback);
        }
    }

    /**
     * Publish an event with data
     * @param {string} event - Event name to publish
     * @param {any} data - Data to pass to subscribers
     */
    publish(event, data) {
        if (this.subscribers[event]) {
            this.subscribers[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in subscriber for ${event}:`, error);
                }
            });
        }
    }
}

// Initialize the EventBus
new EventBus();
