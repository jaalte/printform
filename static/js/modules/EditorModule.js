class EditorModule {
    constructor(container) {
        this.container = container;
        this.allTemplates = {};
        this.debounceTimer = null;
        this.DEBOUNCE_DELAY = 200;
        
        this.render();
        this.initializeEventListeners();
        this.loadTemplates();
    }

    render() {
        this.container.innerHTML = `
            <h1>Plant Tag Printer</h1>
            <form id="label-form">
                <div class="input-group">
                    <label for="template-select">Template:</label>
                    <select id="template-select" name="template_name">
                        <!-- Options get populated by JS -->
                    </select>
                </div>

                <div class="form-container">
                    <div class="data-inputs-container">
                        <strong>Text Entry</strong>
                        <div class="input-group">
                            <label for="main_text">Main Text:</label>
                            <input type="text" id="main_text" name="main_text" class="debounced-field">
                        </div>
                        <div class="input-group">
                            <label for="midtext">Cultivar:</label>
                            <input type="text" id="midtext" name="midtext" class="debounced-field">
                        </div>
                        <div class="input-group">
                            <label for="subtext">Subtext:</label>
                            <input type="text" id="subtext" name="subtext" class="debounced-field">
                        </div>
                    </div>

                    <div class="offset-controls">
                        <strong>Offsets</strong>
                        <div class="input-group">
                            <label for="x-offset">X:</label>
                            <input type="number" id="x-offset" name="x-offset" class="debounced-field" value="0" step="7">
                            <button type="button" id="x-offset-down" class="offset-btn">←</button>
                            <button type="button" id="x-offset-up" class="offset-btn">→</button>
                        </div>
                        <div class="input-group">
                            <label for="y-offset">Y:</label>
                            <input type="number" id="y-offset" name="y-offset" class="debounced-field" value="0" step="1">
                        </div>
                    </div>
                </div>

                <img id="label-image" src="/static/label-templates/label_base.png" alt="Label Preview" onerror="this.src='/static/label-templates/label_base.png'">

                <div id="print-controls">
                    <label for="print-count">Print Count:</label>
                    <input type="number" id="print-count" name="print-count" value="1" min="0" step="1">

                    <button type="button" id="print-one-btn">Print One</button>
                    <button type="button" id="print-batch-btn">Print Batch</button>
                    <button type="button" id="save-label-btn">Save Label</button>
                    <button type="button" id="add-to-queue-btn">Add to Queue</button>
                </div>
            </form>
        `;
    }

    initializeEventListeners() {
        // Template selection
        this.templateSelect = this.container.querySelector('#template-select');
        this.templateSelect.addEventListener('change', () => {
            this.updateFormLabels(this.templateSelect.value);
            this.updatePreview();
        });

        // Debounced fields
        this.container.querySelectorAll('.debounced-field').forEach(field => {
            field.addEventListener('input', () => this.debouncedPreview());
        });

        // Offset buttons
        this.container.querySelector('#x-offset-down').addEventListener('click', () => this.adjustOffset('x', -1));
        this.container.querySelector('#x-offset-up').addEventListener('click', () => this.adjustOffset('x', 1));

        // Print controls
        this.container.querySelector('#print-one-btn').addEventListener('click', () => this.printOne());
        this.container.querySelector('#print-batch-btn').addEventListener('click', () => this.printBatch());
        this.container.querySelector('#save-label-btn').addEventListener('click', () => this.saveLabel());
        this.container.querySelector('#add-to-queue-btn').addEventListener('click', () => this.addToQueue());

        // Scroll wheel handlers for numeric inputs
        this.container.querySelectorAll('input[type="number"]').forEach(numberInput => {
            numberInput.addEventListener('wheel', (e) => this.handleScrollWheel(e, numberInput));
        });
    }

    loadTemplates() {
        fetch('/get_templates')
            .then(resp => resp.json())
            .then(templates => {
                this.allTemplates = templates;
                this.templateSelect.innerHTML = '';

                Object.keys(templates).forEach(key => {
                    const opt = document.createElement('option');
                    opt.value = key;
                    opt.textContent = key;
                    this.templateSelect.appendChild(opt);
                });

                if (Object.keys(templates).length > 0) {
                    const defaultTemplate = Object.keys(templates)[0];
                    this.templateSelect.value = defaultTemplate;
                    this.updateFormLabels(defaultTemplate);
                    
                    // Set default offsets from template if available
                    const tmpl = templates[defaultTemplate];
                    if (tmpl && tmpl.offsets) {
                        const xOffsetInput = this.container.querySelector('#x-offset');
                        const yOffsetInput = this.container.querySelector('#y-offset');
                        xOffsetInput.value = tmpl.offsets[0] || 0;
                        yOffsetInput.value = tmpl.offsets[1] || 0;
                    }
                }

                this.updatePreview();
            })
            .catch(err => {
                console.error('Error loading templates:', err);
                window.app.showToast('Error loading templates. Please refresh the page.');
            });
    }

    updateFormLabels(templateName) {
        const tmpl = this.allTemplates[templateName];
        if (!tmpl || !tmpl.fields) return;

        tmpl.fields.forEach(field => {
            const el = this.container.querySelector(`#${field.name}`);
            if (el) {
                const labelEl = el.parentElement.querySelector('label');
                if (labelEl) {
                    // Use the label from the template or default to the name
                    const labelText = field.label || field.name;
                    labelEl.textContent = labelText + ":";
                }
            }
        });
    }

    debouncedPreview() {
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        this.debounceTimer = setTimeout(() => this.updatePreview(), this.DEBOUNCE_DELAY);
    }

    updatePreview() {
        const labelForm = this.container.querySelector('#label-form');
        const formData = new FormData(labelForm);
        const labelData = Object.fromEntries(formData.entries());
        const labelImage = this.container.querySelector('#label-image');

        // Ensure offset values are included
        const xOffset = this.container.querySelector('#x-offset').value || 0;
        const yOffset = this.container.querySelector('#y-offset').value || 0;
        labelData['x-offset'] = xOffset;
        labelData['y-offset'] = yOffset;
        
        fetch('/preview_label', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_id: window.sessionId,
                label_data: labelData
            })
        })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                console.error('Preview error:', data.error);
                window.app.showToast(`Error generating preview: ${data.error}`);
                return;
            }
            if (data.image_path) {
                const cacheBuster = new Date().getTime();
                labelImage.src = `${data.image_path}?v=${cacheBuster}`;
                labelImage.style.display = 'block';
            }
        })
        .catch(err => {
            console.error('Preview error:', err);
            window.app.showToast('Error generating preview. Please try again.');
        });
    }

    adjustOffset(axis, direction) {
        const input = this.container.querySelector(`#${axis}-offset`);
        const stepVal = parseFloat(input.step) || 1;
        const newVal = (parseFloat(input.value) || 0) + (stepVal * direction);
        
        input.value = Number.isInteger(stepVal) ? 
            String(Math.round(newVal)) : 
            String(parseFloat(newVal));
            
        this.debouncedPreview();
    }

    handleScrollWheel(e, input) {
        e.preventDefault();
        const stepValue = parseFloat(input.step) || 1;
        let currentVal = parseFloat(input.value) || 0;
        
        currentVal += e.deltaY < 0 ? stepValue : -stepValue;
        
        input.value = Number.isInteger(stepValue) ?
            String(Math.round(currentVal)) :
            String(parseFloat(currentVal));
            
        this.debouncedPreview();
    }

    printOne() {
        const labelForm = this.container.querySelector('#label-form');
        const formData = new FormData(labelForm);
        const labelData = Object.fromEntries(formData.entries());
        const printCount = this.container.querySelector('#print-count');
        const countVal = parseInt(printCount.value) || 1;
        
        fetch('/print_label', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_id: window.sessionId,
                count: 1,
                label_data: labelData
            })
        })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                window.app.showToast(`Error: ${data.error}`);
                return;
            }
            if (countVal > 0) {
                printCount.value = countVal - 1;
            }
            window.app.showToast('Printed one label.');
        })
        .catch(err => {
            console.error(err);
            window.app.showToast('Error printing label. Please try again.');
        });
    }

    printBatch() {
        const labelForm = this.container.querySelector('#label-form');
        const formData = new FormData(labelForm);
        const labelData = Object.fromEntries(formData.entries());
        const printCount = this.container.querySelector('#print-count');
        const countVal = parseInt(printCount.value) || 0;
        
        if (countVal <= 0) {
            window.app.showToast("Can't print batch, no labels queued.");
            return;
        }

        fetch('/print_label', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_id: window.sessionId,
                count: countVal,
                label_data: labelData
            })
        })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                window.app.showToast(`Error: ${data.error}`);
                return;
            }
            printCount.value = 0;
            window.app.showToast(`Printed batch of ${countVal} labels.`);
        })
        .catch(err => {
            console.error(err);
            window.app.showToast('Error printing batch. Please try again.');
        });
    }

    saveLabel() {
        fetch('/save_label', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ session_id: window.sessionId })
        })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                window.app.showToast(`Error: ${data.error}`);
            } else {
                window.app.showToast(`Saved to: ${data.saved_path}`);
            }
        })
        .catch(err => console.error(err));
    }

    addToQueue() {
        const labelForm = this.container.querySelector('#label-form');
        const formData = new FormData(labelForm);
        const labelData = Object.fromEntries(formData.entries());
        
        // Publish event for Queue module to handle
        window.eventBus.publish('addToQueue', labelData);
    }

    // Method to load data into the editor (called from Search module)
    loadData(data) {
        Object.entries(data).forEach(([key, value]) => {
            const input = this.container.querySelector(`#${key}`);
            if (input) {
                input.value = value;
            }
        });
        this.updatePreview();
    }
}
