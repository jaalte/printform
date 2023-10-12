from flask import Flask, render_template, request, send_file, make_response, jsonify,send_from_directory, url_for
from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
import csv
import json
import re
from datetime import datetime
import codecs
import code128
from pylibdmtx.pylibdmtx import encode
import qrcode


label_base_name = 'static/label-templates/label_base.png'
label_template_name = 'static/label-templates/label_template.json'

#label_base_name = 'label_base_thin.png'
#label_template_name = 'label_template_thin.json'
# printer_dpi = 305

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('printform-client.html')

@app.route('/generate_label', methods=['POST'])
def generate_label():

    # Load the label template
    with open(label_template_name, 'r') as f:
        template = json.load(f)

    fieldnames = [field["name"] for field in template['fields']]
    
    #template['offsets'] = [0,0]

    template['offsets'][0] += int(request.form['x-offset'])
    template['offsets'][1] += int(request.form['y-offset'])

    formdata = dict()
    for name in fieldnames:
        formdata[name] = request.form[name]

    print(formdata)



    sanitized_formdata = [sanitize_string(value).lower() for value in formdata.values()]

    img = generate_png(template)
    save_to_csv(fieldnames)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = 'label_' + '-'.join(sanitized_formdata) + '-' + timestamp + '.png'

    # Save the image to the 'static/generated_labels' directory with a unique filename
    image_path = f'static/generated_labels/{filename}'
    os.makedirs('static/generated_labels', exist_ok=True)
    img.save(image_path)

    # Return the relative path of the image to be used in the browser
    relative_image_path = '/'+image_path

    return jsonify({"message": f"Label generated and saved as {relative_image_path}.", "image_path": relative_image_path})

@app.route('/save_image', methods=['POST'])
def save_image(img,filepath):
    img.save(filepath)
    return jsonify({"message": f"Image saved as {filepath}."})

@app.route('/download_image/<path:filename>')
def download_image(filename):
    return send_from_directory('static/generated_labels', filename, as_attachment=True, attachment_filename=filename)

def sanitize_string(s):
    return re.sub(r'[^a-zA-Z0-9\s]', '', s).replace(' ', '-')

def unescape_string(s):
    return codecs.decode(s, 'unicode_escape')


def generate_png(template):

    # Open the base image
    img = Image.open(label_base_name)
    d = ImageDraw.Draw(img)

    # Draw the fields on the image
    for field in template['fields']:
        name = field['name']
        x, y = field['x'], field['y']
        data = field['data']

        text = request.form[name]
        #if name == 'cultivar': text = f"\'{text}\'"

        if data['type'] == 'text':
            font_base = data['style']['font-base']
            font = ""
            font_size = data['style']['size']
            bold = data['style'].get('bold', False)
            italic = data['style'].get('italic', False)
            spacing = data['style'].get('spacing', 1)

            if bold and italic:
                font = font_base.replace(".ttf", "bi.ttf")
            elif bold:
                font = font_base.replace(".ttf", "bd.ttf")
            elif italic:
                font = font_base.replace(".ttf", "i.ttf")
            else:
                font = font_base
            
            font = ImageFont.truetype(font, font_size)
            d.text((x, y), text, font=font, fill=(0, 0, 0), spacing=spacing)
            #custom_draw_text(d, (x,y), text, font, fill=(0,0,0))
    
    # Apply text offsets
    dx, dy = template["offsets"]
    img = offset_image(img,dx,dy)

    # # Generate QR Code with higher error correction
    # qr = qrcode.QRCode(
    #     version=1,
    #     error_correction=qrcode.constants.ERROR_CORRECT_H,
    #     box_size=20,
    #     border=4,
    # )
    
    # qr.add_data('tag-TTTTTT-000')
    # qr.make(fit=True)
    # qr_img = qr.make_image(fill='black', back_color='white').convert('RGB')

    # # Resize QR code to fit 80% of the main image height
    # multiplier = 0.8
    # qr_new_size = int(img.height * multiplier)
    # qr_img = qr_img.resize((qr_new_size, qr_new_size), Image.NEAREST)

    # # Calculate y-position to center the QR code vertically
    # y_position = (img.height - qr_new_size) // 2

    # # Paste the QR code into the main image
    # img.paste(qr_img, (0, y_position))

    return img


def offset_image(img, dx, dy):
    # Crop the image based on the offsets
    left = max(0, -dx)
    top = max(0, -dy)
    right = img.width - max(0, dx)
    bottom = img.height - max(0, dy)
    cropped_img = img.crop((left, top, right, bottom))

    # Calculate the paste position
    paste_x = max(0, dx)
    paste_y = max(0, dy)

    # Paste into a new image with the same dimensions as the original, filled with white color
    offset_img = Image.new('RGB', (img.width, img.height), (255, 255, 255))
    offset_img.paste(cropped_img, (paste_x, paste_y))

    return offset_img

def custom_draw_text(draw, position, text, font, fill=(0, 0, 0), spacing=4, tab_width=4):
    x, y = position
    original_x = x
    for char in text:
        if char == '\n':
            y += font.getsize("A")[1] + spacing  # Move down one line
            x = original_x  # Reset x position
        elif char == '\t':
            x += font.getsize(' ' * tab_width)[0]  # Move right for a tab
        else:
            draw.text((x, y), char, font=font, fill=fill)
            x += font.getsize(char)[0]  # Update x position based on character width

def save_to_csv(fieldnames):
    with open('print_history.csv', mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if csvfile.tell() == 0:
            writer.writeheader()
                
        values = [request.form[name] for name in fieldnames]
        values_dict = {k: v for k, v in zip(fieldnames, values)}
        
        writer.writerow(values_dict)
        

@app.route('/generated_labels/<path:filename>')
def serve_generated_labels(filename):
    return send_from_directory('generated_labels', filename)
    
    
    
    
    
    


if __name__ == '__main__':
    app.run(debug=True)
