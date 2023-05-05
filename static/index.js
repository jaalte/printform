function logMessage(message, color) {
    var log = document.getElementById("message-log");
    var span = document.createElement("span");
    if(color) span.style.color = color;
    span.appendChild(document.createTextNode(message));
    log.appendChild(span);
    log.appendChild(document.createElement("br"));
    log.scrollTop = log.scrollHeight;
}

document.getElementById('label-form').addEventListener('submit', function (event) {
    event.preventDefault();

    const formData = new FormData(event.target);

    fetch('/generate_label', {
      method: 'POST',
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        const labelImage = document.getElementById('label-image');
        labelImage.src = data.image_path;
        labelImage.style.display = 'block';

        logMessage(data.message,"#00FF00")
      });
  });

  document.getElementById('label-form').addEventListener('submit', function (event) {
    event.preventDefault();

    const formData = new FormData(event.target);

    // Triggers a function with the same endpoint in the python script
    fetch('/update', {
      method: 'POST',
      body: formData,
    }) // Some magic to process the resposne
      .then((response) => response.json())
      .then((data) => {
        // Works with the returned data
        const labelImage = document.getElementById('label-image');
        labelImage.src = data.image_path;
        labelImage.style.display = 'block';
      });
  });

