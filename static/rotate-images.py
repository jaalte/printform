#!/usr/bin/env python3
import os
from PIL import Image

def rotate_images(source_dir, target_dir, angle=180):
    # Create target directory if it doesn't exist
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # Process each file in the source directory
    for filename in os.listdir(source_dir):
        # Construct full file path
        original_path = os.path.join(source_dir, filename)
        if os.path.isfile(original_path):
            # Open the image
            with Image.open(original_path) as img:
                # Rotate the image
                rotated = img.rotate(angle)
                # Construct new filename and path
                new_filename = f'r_{filename}'
                rotated_path = os.path.join(target_dir, new_filename)
                # Save the rotated image
                rotated.save(rotated_path)
                print(f'Rotated image saved as: {rotated_path}')
                
                # Preserve the timestamps of the original file
                original_stat = os.stat(original_path)
                os.utime(rotated_path, (original_stat.st_atime, original_stat.st_mtime))

# Directory names
source_directory = 'generated_labels'
target_directory = 'generated_labels_rotated'

# Rotate the images
rotate_images(source_directory, target_directory)
