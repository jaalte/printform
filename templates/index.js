function logMessage(message, color) {
    var log = document.getElementById("log");
    var span = document.createElement("span");
    if(color) span.style.color = color;
    span.appendChild(document.createTextNode(message));
    log.appendChild(span);
    log.appendChild(document.createElement("br"));
    log.scrollTop = log.scrollHeight;
    console.log("AAA")
}

window.logMessage = logMessage;

console.log("AAA")