class QueueModule {
    constructor(container) {
        this.container = container;
        this.queue = [];
        
        this.render();
        this.initializeEventListeners();
    }

    render() {
        this.container.innerHTML = `
            <div class="queue-container">
                <h2>Print Queue</h2>
                <div class="queue-list" id="queue-list">
                    <p class="empty-queue-message">Queue is empty</p>
                </div>
                <div class="queue-controls">
                    <button id="print-queue-btn" disabled>Print All</button>
                    <button id="clear-queue-btn" disabled>Clear Queue</button>
                </div>
            </div>
        `;
    }

    initializeEventListeners() {
        const printQueueBtn = this.container.querySelector('#print-queue-btn');
        const clearQueueBtn = this.container.querySelector('#clear-queue-btn');

        printQueueBtn.addEventListener('click', () => this.printQueue());
        clearQueueBtn.addEventListener('click', () => this.clearQueue());

        // Subscribe to events from other modules
        window.eventBus.subscribe('addToQueue', (labelData) => this.addToQueue(labelData));
    }

    addToQueue(labelData) {
        // Add a unique ID to each queue item
        const queueItem = {
            ...labelData,
            id: 'queue-' + Date.now() + '-' + Math.random().toString(36).substring(2, 9)
        };
        
        this.queue.push(queueItem);
        this.updateQueueDisplay();
    }

    removeFromQueue(itemId) {
        this.queue = this.queue.filter(item => item.id !== itemId);
        this.updateQueueDisplay();
    }

    updateQueueDisplay() {
        const queueList = this.container.querySelector('#queue-list');
        const printQueueBtn = this.container.querySelector('#print-queue-btn');
        const clearQueueBtn = this.container.querySelector('#clear-queue-btn');
        
        if (this.queue.length === 0) {
            queueList.innerHTML = '<p class="empty-queue-message">Queue is empty</p>';
            printQueueBtn.disabled = true;
            clearQueueBtn.disabled = true;
            return;
        }

        printQueueBtn.disabled = false;
        clearQueueBtn.disabled = false;
        
        queueList.innerHTML = this.queue.map(item => `
            <div class="queue-item" data-id="${item.id}">
                <div class="queue-item-preview">
                    <img src="${item.image_path || '/static/label-templates/label_base.png'}" alt="Label preview" onerror="this.src='/static/label-templates/label_base.png'">
                </div>
                <div class="queue-item-details">
                    <p><strong>${item.main_text || 'Untitled'}</strong></p>
                    <p>${item.midtext || ''} ${item.subtext ? '- ' + item.subtext : ''}</p>
                </div>
                <div class="queue-item-actions">
                    <button class="queue-remove-btn" data-id="${item.id}">Remove</button>
                    <button class="queue-print-btn" data-id="${item.id}">Print</button>
                </div>
            </div>
        `).join('');

        // Add event listeners to the newly created buttons
        queueList.querySelectorAll('.queue-remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const itemId = e.target.dataset.id;
                this.removeFromQueue(itemId);
            });
        });

        queueList.querySelectorAll('.queue-print-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const itemId = e.target.dataset.id;
                const item = this.queue.find(i => i.id === itemId);
                if (item) {
                    this.printItem(item);
                    // Don't remove from queue automatically, let user decide when to remove
                }
            });
        });
    }

    printQueue() {
        if (this.queue.length === 0) return;
        
        const count = this.queue.length;
        let successCount = 0;
        
        // Print each item in sequence
        const printNextItem = (index) => {
            if (index >= this.queue.length) {
                window.app.showToast(`Printed ${successCount} of ${count} labels.`);
                return;
            }
            
            const item = this.queue[index];
            this.printItem(item)
                .then(success => {
                    if (success) successCount++;
                    printNextItem(index + 1);
                })
                .catch(() => {
                    printNextItem(index + 1);
                });
        };
        
        printNextItem(0);
    }
    
    printItem(item) {
        // We'll simulate printing by using the session's preview image
        return fetch('/print_label', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_id: window.sessionId,
                count: 1,
                label_data: {
                    main_text: item.main_text,
                    midtext: item.midtext,
                    subtext: item.subtext,
                    template_name: item.template_name || 'Default Label Template'
                }
            })
        })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                window.app.showToast(`Error: ${data.error}`);
                return false;
            }
            window.app.showToast('Printed one label.');
            return true;
        })
        .catch(err => {
            console.error('Print error:', err);
            window.app.showToast('Error printing label. Please try again.');
            return false;
        });
    }

    clearQueue() {
        this.queue = [];
        this.updateQueueDisplay();
        window.app.showToast('Queue cleared.');
    }
}
