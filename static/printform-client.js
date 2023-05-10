var template = {
    "fields": [
        {
            "x": 136,
            "y": 5,
            "name": "main_text",
            "data": {
                "type": "text",
                "text": "MAIN_TEXT",
                "style": {
                    "font": "arialbd.ttf",
                    "size": 56,
                    "bold": false,
                    "italic": false,
                    "spacing": 5
                }
            }
        },
        {
            "x": 136,
            "y": 86,
            "name": "subtext",
            "data": {
                "type": "text",
                "text": "SUBTEXT",
                "style": {
                    "font": "ariali.ttf",
                    "size": 48,
                    "bold": false,
                    "italic": false,
                    "spacing": 1
                }
            }
        }
    ]
}


// Class declarations

class TextFieldManager {
    constructor(container) {
        this.fields = []
        this.container = container

        this.templateData = {
            x: 0,
            y: 0,
            id: 0,
            type: "text",
            enabled: true,
            data: {
                text: "Sample Text",
                basefont: "arial",
                size: 48,
                bold: false,
                italic: false,
            }
        }


    }
    addField() {

        newID = this.generateFieldID()


        newField = new TextField()



        // if(this.fields.length > 1) {
        //     this.enableDeleteButtons
        // }
        // else this.disableDeleteButtons
    }
    generateFieldID() {
        let length = 4
        let chars = "0123456789ABCDEF"
        let id = "";
        for (let i = 0; i < length; i++) {
            const randomIndex = Math.floor(Math.random() * chars.length);
            id += chars[randomIndex];
        }
        return id;
    }
    getFieldByID(id) {
        for(let field in this.fields) {
            if(field.id == id) return field
        }
    }
}

class TextField {
    constructor(manager, data) {
        this.manager = manager;
        this.data = data

        this.element = this.createFieldHTMLElement();

        // Keyed to the same values present in data
        this.inputs = {
            text: element.querySelector(".field-text"),
            xPos: element.querySelector(".x-pos"),
            yPos: element.querySelector(".y-pos"),
            font: element.querySelector(".font-dropdown"),
            fontSize: element.querySelector(".font-size"),
            bold: element.querySelector(".bold-toggle"),
            italic: element.querySelector(".italic-toggle"),
            enabled: element.querySelector(".enable-toggle"),
        };

        for(input of this.inputs) {
            input.addEventListener('input', update);
        }
    
        this.deleteButtonEnabled = false


        this.attachEventListeners();

        this.updateHTMLFromData()
    }

    setData(newData) {
        this.data = newData
        this.updateHTMLFromData()
    }

    createFieldHTMLElement() {
        const fieldTemplate = document.querySelector(".field");
        const field = fieldTemplate.cloneNode(true);
        field.id = `field-${this.id}`;

        this.applyFieldData(field, this.data);

        this.container.appendChild(field);
        return field;
    }

    attachEventListeners() {
        this.element.querySelector(".delete-btn").addEventListener('click', () => {
            this.onDelete(this);
        });

        // Add your other event listeners here, e.g.:
        // this.fieldElement.querySelector(".field-text").addEventListener("input", (event) => {
        //     this.updateData("text", event.target.value);
        // });

        // ...
    }

    updateHTMLFromData() {
        for(let name in this.inputs) {
            let input = this.inputs[name]
            input.value = data[name]
        }
    }
    updateDataFromHTML() {
        this.data.data[property] = value;
    }

    remove() {
        this.container.removeChild(this.element);
    }

    getData() {
        return this.data;
    }
}




// Element constants:

var fieldManager = new TextFieldManager(document.getElementById("field-list"))
const addFieldButton = document.getElementById("add-field-btn");
const saveImageButtton = document.getElementById("save-btn")

//////////////////////




function init() {

    // ADD LISTENERS //////////////////////////////////////

    //saveImageButtton.addEventListener('input', saveDefault);
    

    addFieldButton.addEventListener("click", () => {

        let textFields = []
    
        const fieldData = {
            x: 0,
            y: 0,
            id: fields.length + 1,
            type: "text",
            data: {
                text: "Sample Text",
                basefont: "arial",
                size: 48,
                bold: false,
                italic: false
            }
        };
    
        const field = new InputField(fields.length + 1, fieldsContainer, fieldData, (field) => {
            // On delete, remove the field from the fields array and from the DOM.
            fields = fields.filter(f => f !== field);
            field.remove();
        });
    
        fields.push(field);
        
        // Add event listeners and other logic here, e.g.:
        // field.querySelector(".field-text").addEventListener("input", (event) => {
        //     updateTemplate(field.id, "text", event.target.value);
        // });
    
        // ...
    
        fields.appendChild(field);
        //checkDeleteButtons();
    });


    // Initialize field IDs, event listeners, and delete buttons
    const initialField = document.querySelector(".field");
    initialField.id = `field-${fieldCounter}`;
    template.fields.push({
        x: 0,
        y: 0,
        id: fieldCounter,
        type: "text",
        data: {
            text: "Sample Text",
            basefont: "arial",
            size: 48,
            bold: false,
            italic: false
        }
    });
    fieldCounter++;



    console.log(template)
    
    // Add event listeners and other logic for the initial field, e.g.:
    // initialField.querySelector(".field-text").addEventListener("input", (event) => {
    //     updateTemplate(initialField.id, "text", event.target.value);
    // });
    
    // ...
    
    checkDeleteButtons();


}
document.addEventListener('DOMContentLoaded', init);

function getFields() {
    const fieldElements = document.querySelectorAll("#field-list .TextField");
    const fieldsContainer = document.getElementById("fields");
    for (let i = 0; i < fieldElements.length; i++) {
        const fieldData = processFieldData(fieldElements[i], i);
        const field = new TextField(i, fieldsContainer, fieldData, (field) => {
            // On delete, remove the field from the template and from the DOM.
            template.fields = template.fields.filter(f => f.id !== field.id);
            field.remove();
            checkDeleteButtons();
        });
        fieldsContainer.appendChild(field.fieldElement);
        template.fields.push(fieldData);
    }
}




function saveDefault() {
    console.log("saveDefault NYI")
    return true
}

function update() {

    var textFieldElements = document.getElementsByClassName("TextField")



    tagData = parseInputs()

    labelOffset = [

    ]

    updateImage(tagData)
    return true
}

function updateImage(tagData) {
    console.log("updateImage()")

    offsets = [
         document.getElementById("x-offset").value,
         document.getElementById("y-offset").value,
    ]

    console.log("Offsets: " + offsets)

    filepath = generateFilePath(tagData)
    print(filepath)
}

function generateFilePath(tagData) {
    var sanitizedTagData = Object.values(tagData).map(value => sanitizeString(value).toLowerCase());
    var timestamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '');
    var filename = `label_${sanitizedTagData.join('-')}-${timestamp}.png`;
  
    var imageDir = '/static/generated_labels/';
    var imageFilePath = imageDir + filename
    return imageFilePath
}

function sanitizeString(s) {
    s = s.toString()
    return s.replace(/[^a-zA-Z0-9\s]/g, '').replace(/ /g, '-');
}


// mine



// its


function getFieldElements() {
    return Array.from(document.querySelectorAll(".field"));
}

function processFieldData(fieldElement, index) {
    const textField = fieldElement.querySelector(".field-text");
    const positionX = fieldElement.querySelector(".x-pos");
    const positionY = fieldElement.querySelector(".y-pos");
    const fontDropdown = fieldElement.querySelector(".font-dropdown");
    const fontSizeInput = fieldElement.querySelector(".font-size");
    const boldCheckbox = fieldElement.querySelector(".bold-toggle");
    const italicCheckbox = fieldElement.querySelector(".italic-toggle");
    const enabledCheckbox = fieldElement.querySelector(".enable-toggle");

    return {
        x: parseInt(positionX.value),
        y: parseInt(positionY.value),
        id: index,
        type: "text",
        enabled: enabledCheckbox.checked,
        data: {
            text: textField.value,
            basefont: fontDropdown.value,
            size: parseInt(fontSizeInput.value),
            bold: boldCheckbox.checked,
            italic: italicCheckbox.checked
        }
    };
}

function applyFieldData(fieldElement, fieldData) {
    const textField = fieldElement.querySelector(".field-text");
    const positionX = fieldElement.querySelector(".x-pos");
    const positionY = fieldElement.querySelector(".y-pos");
    const fontDropdown = fieldElement.querySelector(".font-dropdown");
    const fontSizeInput = fieldElement.querySelector(".font-size");
    const boldCheckbox = fieldElement.querySelector(".bold-toggle");
    const italicCheckbox = fieldElement.querySelector(".italic-toggle");
    const enabledCheckbox = fieldElement.querySelector(".enable-toggle");

    textField.value = fieldData.data.text;
    positionX.value = fieldData.x;
    positionY.value = fieldData.y;
    fontDropdown.value = fieldData.data.basefont;
    fontSizeInput.value = fieldData.data.size;
    boldCheckbox.checked = fieldData.data.bold;
    italicCheckbox.checked = fieldData.data.italic;
    enabledCheckbox.checked = fieldData.enabled;
}

 
function parseInputs() {
    const fieldElements = getFieldElements();
    let data = fieldElements.map((fieldElement, index) => processFieldData(fieldElement, index));
    console.log(data)
    return data
}



function updateTemplate(fieldId, property, value) {
    const field = template.fields.find(f => f.id === fieldId);
    if (field) {
        field.data[property] = value;
    }
}

function checkDeleteButtons() {
    const deleteButtons = document.querySelectorAll(".delete-btn");
    if (deleteButtons.length <= 1) {
        deleteButtons.forEach(btn => btn.disabled = true);
    } else {
        deleteButtons.forEach(btn => btn.disabled = false);
    }
}

