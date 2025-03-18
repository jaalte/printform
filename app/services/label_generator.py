from PIL import Image, ImageDraw, ImageFont
from typing import Dict
import os
from ..models.label import LabelTemplate
from ..config.settings import PREVIEW_FOLDER, BASE_DIR

class LabelGenerator:
    @staticmethod
    def generate_png(template: LabelTemplate, form_data: Dict) -> Image.Image:
        """Generates the label image according to template and form data."""
        label_base_path = template.base_image or os.path.join(BASE_DIR, "static", "label-templates", "label_base.png")
        
        img = Image.open(label_base_path)
        d = ImageDraw.Draw(img)

        for field in template.fields:
            name = field.name
            x, y = field.x, field.y
            data = field.data
            text = form_data.get(name, '')

            if data['type'] == 'text':
                font_base = data['style']['font-base']
                font_size = data['style']['size']
                bold = data['style'].get('bold', False)
                italic = data['style'].get('italic', False)
                spacing = data['style'].get('spacing', 1)

                # Build font path based on style
                if bold and italic:
                    font_path = font_base.replace(".ttf", "bi.ttf")
                elif bold:
                    font_path = font_base.replace(".ttf", "bd.ttf")
                elif italic:
                    font_path = font_base.replace(".ttf", "i.ttf")
                else:
                    font_path = font_base

                # Convert to absolute path if relative
                if not os.path.isabs(font_path):
                    font_path = os.path.join(BASE_DIR, "static", "fonts", font_path)

                try:
                    font = ImageFont.truetype(font_path, font_size)
                    d.text((x, y), text, font=font, fill=(0, 0, 0), spacing=spacing)
                except OSError as e:
                    print(f"Warning: Could not load font {font_path}: {e}")
                    # Fallback to default font
                    font = ImageFont.load_default()
                    d.text((x, y), text, font=font, fill=(0, 0, 0), spacing=spacing)

        # Apply offsets
        dx, dy = template.offsets
        return LabelGenerator.offset_image(img, dx, dy)

    @staticmethod
    def offset_image(img: Image.Image, dx: int, dy: int) -> Image.Image:
        """Offsets the image by (dx, dy), cropping or padding with white as needed."""
        left = max(0, -dx)
        top = max(0, -dy)
        right = img.width - max(0, dx)
        bottom = img.height - max(0, dy)
        cropped_img = img.crop((left, top, right, bottom))

        paste_x = max(0, dx)
        paste_y = max(0, dy)
        offset_img = Image.new('RGB', (img.width, img.height), (255, 255, 255))
        offset_img.paste(cropped_img, (paste_x, paste_y))

        return offset_img

    @staticmethod
    def save_preview(img: Image.Image, session_id: str) -> str:
        """Saves the preview image and returns its path."""
        preview_filename = f"preview_{session_id}.png"
        preview_path = os.path.join(PREVIEW_FOLDER, preview_filename)
        img.save(preview_path)
        return preview_path