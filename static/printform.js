


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



function init() {
    let inputs = document.getElementsByClassName('input-field')
    for(input of inputs) {
        input.addEventListener('input', update);
    }

    document.getElementById("save-btn").addEventListener('input', saveDefault);

}
document.addEventListener('DOMContentLoaded', init);


function saveDefault() {
    console.log("saveDefault NYI")
    return true
}

function update() {

    


    updateImage()
    return true
}

function updateImage() {
    console.log("updateImage()")

    offsets = [

    ]
}


function addNewField(fieldObj) {

    if(typeof fieldObj == "undefined") {
        fieldObj = fieldTemplate
    }

}



const fields = document.getElementById("fields");
const addFieldButton = document.getElementById("addField");

let fieldCounter = 1;
template = {
    fields: []
};

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
    checkDeleteButtons();
});

function checkDeleteButtons() {
    const deleteButtons = document.querySelectorAll(".delete-btn");
    if (deleteButtons.length <= 1) {
        deleteButtons.forEach(btn => btn.disabled = true);
    } else {
        deleteButtons.forEach(btn => btn.disabled = false);
    }
}

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