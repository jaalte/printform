from flask import Flask, render_template, request, send_file, make_response, jsonify,send_from_directory
from PIL import Image, ImageDraw, ImageFont
import os
import csv
import json
from datetime import datetime

label_base_name = 'label_base.png'
label_template_name = 'label_template.json'

#label_base_name = 'label_base_thin.png'
#label_template_name = 'label_template_thin.json'
# printer_dpi = 305

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

def generate_png(data, main_text, subtext, cultivar):

    main_text, cultivar, subtext = data

    # Load the label template
    with open(label_template_name, 'r') as f:
        template = json.load(f)

    # Open the base image
    img = Image.open(label_base_name)
    d = ImageDraw.Draw(img)

    # Draw the fields on the image
    for field in template['fields']:
        x, y = field['x'], field['y']
        data = field['data']

        if data['type'] == 'text':
            text = data['text'].replace("MAIN_TEXT", main_text).replace("SUBTEXT", subtext).replace("CULTIVAR", subtext)
            font_path = data['style']['font']
            font_size = data['style']['size']
            # bold = data['style'].get('bold', False)
            # italic = data['style'].get('italic', False)
            spacing = data['style'].get('spacing', 1)

            # if bold and italic:
            #     font_path = font_path.replace(".ttf", "bi.ttf")
            # elif bold:
            #     font_path = font_path.replace(".ttf", "b.ttf")
            # elif italic:
            #     font_path = font_path.replace(".ttf", "i.ttf")

            font = ImageFont.truetype(font_path, font_size)
            d.text((x, y), text, font=font, fill=(0, 0, 0), spacing=spacing)

    # Initialize a new image with the same dimensions as the original, filled with white color
    padded_img = Image.new('RGB', (img.width, img.height), (255, 255, 255))

    # Apply the offsets
    if "offsets" in template:
        x_offset, y_offset = template["offsets"]

        x_offset = -x_offset
        y_offset = -y_offset

        # Crop the image based on the offsets
        left = max(0, x_offset)
        upper = max(0, y_offset)
        right = img.width - max(0, -x_offset)
        lower = img.height - max(0, -y_offset)
        img = img.crop((left, upper, right, lower))

        # Calculate the paste position
        paste_x = max(0, -x_offset)
        paste_y = max(0, -y_offset)

        # Paste the cropped image onto the new image
        padded_img.paste(img, (paste_x, paste_y))
        img = padded_img


    return img

    
def save_to_csv(main_text, subtext):
    with open('print_history.csv', mode='a', newline='') as csvfile:
        fieldnames = ['main_text', 'subtext', 'cultivar']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if csvfile.tell() == 0:
            writer.writeheader()
        
        writer.writerow({'main_text': main_text, 'subtext': subtext})
        


@app.route('/generate_label', methods=['POST'])
def generate_label():
    main_text = request.form['main_text']
    subtext = request.form['subtext']

    

    img = generate_png(data)
    save_to_csv(main_text, subtext)

    # Save the image to the 'static/generated_labels' directory with a unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = f'static/generated_labels/label_{timestamp}.png'
    os.makedirs('static/generated_labels', exist_ok=True)
    img.save(image_path)

    # Return the relative path of the image to be used in the browser
    relative_image_path = f'/static/generated_labels/label_{timestamp}.png'

    return jsonify({"message": f"Label generated and saved as {relative_image_path}.", "image_path": relative_image_path})


@app.route('/generated_labels/<path:filename>')
def serve_generated_labels(filename):
    return send_from_directory('generated_labels', filename)
    
    
    
    
    
    


if __name__ == '__main__':
    app.run(debug=True)
