class SearchModule {
    constructor(container) {
        this.container = container;
        this.render();
        this.initializeEventListeners();
    }

    render() {
        this.container.innerHTML = `
            <div class="search-container">
                <h2>Search Saved Labels</h2>
                <div class="search-controls">
                    <input type="text" id="search-input" placeholder="Search labels...">
                    <button id="search-btn">Search</button>
                </div>
                
                <div class="search-results">
                    <!-- Results will be populated here -->
                </div>
            </div>
        `;
    }

    initializeEventListeners() {
        const searchBtn = this.container.querySelector('#search-btn');
        const searchInput = this.container.querySelector('#search-input');

        searchBtn.addEventListener('click', () => this.performSearch());
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });
    }

    performSearch() {
        const searchInput = this.container.querySelector('#search-input');
        const query = searchInput.value.trim();
        
        if (!query) {
            window.app.showToast('Please enter a search term');
            return;
        }

        fetch('/search_labels', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ query })
        })
        .then(r => r.json())
        .then(results => this.displayResults(results))
        .catch(err => {
            console.error('Search error:', err);
            window.app.showToast('Error performing search');
        });
    }

    displayResults(results) {
        const resultsContainer = this.container.querySelector('.search-results');
        
        if (!results || results.length === 0) {
            resultsContainer.innerHTML = '<p>No results found</p>';
            return;
        }

        resultsContainer.innerHTML = results.map(result => `
            <div class="search-result">
                <div class="result-preview">
                    <img src="${result.preview_path}" alt="Label preview" onerror="this.src='/static/label-templates/label_base.png'">
                </div>
                <div class="result-details">
                    <p><strong>Main Text:</strong> ${result.main_text || 'N/A'}</p>
                    <p><strong>Cultivar:</strong> ${result.midtext || 'N/A'}</p>
                    <p><strong>Subtext:</strong> ${result.subtext || 'N/A'}</p>
                    <p><small>Created: ${new Date(result.date_created).toLocaleString()}</small></p>
                </div>
                <div class="result-actions">
                    <button class="load-btn" data-result='${JSON.stringify(result)}'>
                        Load in Editor
                    </button>
                    <button class="queue-btn" data-result='${JSON.stringify(result)}'>
                        Add to Queue
                    </button>
                </div>
            </div>
        `).join('');

        // Add event listeners to the newly created buttons
        resultsContainer.querySelectorAll('.load-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const resultData = JSON.parse(e.target.dataset.result);
                // Create a simplified data object with just what the editor needs
                const editorData = {
                    main_text: resultData.main_text,
                    midtext: resultData.midtext,
                    subtext: resultData.subtext,
                    template_name: resultData.template_name || 'Default Label Template'
                };
                window.eventBus.publish('loadInEditor', editorData);
                window.app.showToast('Loaded label into editor');
            });
        });

        resultsContainer.querySelectorAll('.queue-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const resultData = JSON.parse(e.target.dataset.result);
                // Create a data object with label info and image path
                const queueData = {
                    main_text: resultData.main_text,
                    midtext: resultData.midtext,
                    subtext: resultData.subtext,
                    image_path: resultData.preview_path,
                    date_created: resultData.date_created
                };
                window.eventBus.publish('addToQueue', queueData);
                window.app.showToast('Added to queue');
            });
        });
    }
}
