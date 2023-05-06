
const path = require('path');

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

const fieldTemplate = {
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


var formData = {
    fields: [

    ],
    offset: [0,0]
}

const fields = document.getElementById("fields");
const addFieldButton = document.getElementById("addField");

let fieldCounter = 1;
template = {
    fields: []
};


function init() {
    let inputs = document.getElementsByClassName('input-field')
    for(input of inputs) {
        input.addEventListener('input', update);
    }

    document.getElementById("save-btn").addEventListener('input', saveDefault);


    fields.addEventListener("click", (event) => {
        if (event.target.classList.contains("delete-btn")) {
            const field = event.target.closest(".field");
            fields.removeChild(field);
            template.fields = template.fields.filter(f => f.id !== parseInt(field.id.split("-")[1]));
            checkDeleteButtons();
        }
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
    
    // Add event listeners and other logic for the initial field, e.g.:
    // initialField.querySelector(".field-text").addEventListener("input", (event) => {
    //     updateTemplate(initialField.id, "text", event.target.value);
    // });
    
    // ...
    
    checkDeleteButtons();


}
document.addEventListener('DOMContentLoaded', init);


function saveDefault() {
    console.log("saveDefault NYI")
    return true
}

function update() {

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
    var imageFilePath = path.join(imageDir, filename);
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





function addNewField(fieldObj) {

    if(typeof fieldObj == "undefined") {
        fieldObj = fieldTemplate
    }

}


function createField() {
    const fieldTemplate = document.querySelector(".field");
    const field = fieldTemplate.cloneNode(true);
    field.id = `field-${fieldCounter}`;

    const fieldData = {
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
    };
    template.fields.push(fieldData);

    fieldCounter++;
    return field;
}

function updateTemplate(fieldId, property, value) {
    const field = template.fields.find(f => f.id === fieldId);
    if (field) {
        field.data[property] = value;
    }
}

addFieldButton.addEventListener("click", () => {
    const field = createField();
    
    // Add event listeners and other logic here, e.g.:
    // field.querySelector(".field-text").addEventListener("input", (event) => {
    //     updateTemplate(field.id, "text", event.target.value);
    // });

    // ...

    fields.appendChild(field);
    //checkDeleteButtons();
});

function checkDeleteButtons() {
    const deleteButtons = document.querySelectorAll(".delete-btn");
    if (deleteButtons.length <= 1) {
        deleteButtons.forEach(btn => btn.disabled = true);
    } else {
        deleteButtons.forEach(btn => btn.disabled = false);
    }
}

