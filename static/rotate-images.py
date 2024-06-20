#!/usr/bin/env python3
import os
from PIL import Image
from datetime import datetime

def resize_and_rotate_images(source_dir, target_dir, angle=180, scale=0.8):
    # Create target directory if it doesn't exist
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # Timestamp before 2024-05-06 (Unix timestamp format)
    cutoff_timestamp = datetime(2024, 5, 6).timestamp()

    # Process each file in the source directory
    for filename in os.listdir(source_dir):
        # Construct full file path
        original_path = os.path.join(source_dir, filename)
        # Check if it is a file and an image
        if os.path.isfile(original_path) and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            file_timestamp = os.path.getmtime(original_path)
            # Only process files before the cutoff timestamp
            if file_timestamp < cutoff_timestamp:
                try:
                    with Image.open(original_path) as img:
                        # Resize the image by 80%
                        new_size = (int(img.width * scale), int(img.height * scale))
                        resized = img.resize(new_size, Image.ANTIALIAS)

                        # Calculate vertical offset to center the image
                        vertical_offset = (img.height - new_size[1]) // 2

                        # Create a new image with a white background
                        new_img = Image.new("RGB", img.size, "white")
                        new_img.paste(resized, (0, vertical_offset))  # Pasting resized image centered vertically

                        # Rotate the image
                        rotated = new_img.rotate(angle)

                        # Construct new filename and path
                        new_filename = f'r_{filename}'
                        rotated_path = os.path.join(target_dir, new_filename)

                        # Save the rotated image
                        rotated.save(rotated_path)
                        print(f'Processed and saved: {rotated_path}')
                        
                        # Preserve the timestamps of the original file
                        os.utime(rotated_path, (os.path.getatime(original_path), os.path.getmtime(original_path)))
                except Exception as e:
                    print(f'Error processing {filename}: {e}')
            else:
                print(f'Skipped {filename} due to timestamp {file_timestamp} not meeting cutoff {cutoff_timestamp}')
        else:
            print(f'Skipped {filename}: Not an image file or not a file')

# Directory names
source_directory = 'generated_labels'
target_directory = 'generated_labels_rotated'

# Resize and rotate the images
resize_and_rotate_images(source_directory, target_directory)
