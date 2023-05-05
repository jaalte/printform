function logMessage(message, color) {
    var log = document.getElementById("message-log");
    var span = document.createElement("span");
    if(color) span.style.color = color;
    span.appendChild(document.createTextNode(message));
    log.appendChild(span);
    log.appendChild(document.createElement("br"));
    log.scrollTop = log.scrollHeight;
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
}



