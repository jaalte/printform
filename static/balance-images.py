#!/usr/bin/env python3
import os
import numpy as np
from PIL import Image

# Adjust this ratio as needed:
target_midpoint_ratio = 0.6

# Define your source and destination directories here:
src_dir = "./generated_labels"
dst_dir = "./generated_labels_balanced"

os.makedirs(dst_dir, exist_ok=True)

def find_top_whitespace(arr_gray):
    """
    Given a 2D numpy array (grayscale),
    returns the number of rows from the top
    that are fully white (>= 250).
    """
    # We can do this with a vectorized approach:
    # For each row index in [0..height), check if that row is all white.
    # The first row that is not all white stops the count.
    mask = np.all(arr_gray >= 250, axis=1)  # shape = (height,)
    # np.argmax(mask==False) will give the first index where row is not all-white
    # but we must handle the case if everything is white
    first_nonwhite = np.argmax(~mask)
    # If there's no nonwhite row, first_nonwhite will be 0. We need to check if mask is all True
    if np.all(mask):
        return arr_gray.shape[0]  # entire image is white
    return first_nonwhite

def find_bottom_whitespace(arr_gray):
    """
    Given a 2D numpy array (grayscale),
    returns the number of rows from the bottom
    that are fully white (>= 250).
    """
    # Reverse the array vertically, do the same approach
    mask = np.all(arr_gray[::-1] >= 250, axis=1)  # shape = (height,)
    first_nonwhite = np.argmax(~mask)
    if np.all(mask):
        return arr_gray.shape[0]
    return first_nonwhite

def process_image(src_path, dst_path):
    """
    Reads a PNG image from src_path, measures top and bottom whitespace,
    calculates the content's midpoint, then offsets the content vertically
    so that its midpoint lines up with target_midpoint_ratio.
    Writes the result to dst_path.
    """

    # Open the image in RGB so we can easily manipulate color values
    img = Image.open(src_path).convert("RGB")
    width, height = img.size

    # Convert to grayscale for whitespace scanning
    gray = img.convert("L")
    arr_gray = np.array(gray, dtype=np.uint8)

    # 1) Find how many rows from top/bottom are purely white
    top_whitespace = find_top_whitespace(arr_gray)
    bottom_whitespace = find_bottom_whitespace(arr_gray)

    # 2) Define the bounding region of the actual content
    label_top = top_whitespace
    label_bottom = height - bottom_whitespace - 1
    
    # If the entire image is white, just save as-is
    if label_bottom < label_top:
        # Means there's no actual content
        # Just re-save the white image
        img.save(dst_path)
        return
    
    # 3) Calculate the current vertical midpoint of the label content
    label_center = (label_top + label_bottom) / 2.0

    # 4) Determine the target center in pixel coordinates
    # e.g. if the image is 300px tall and ratio is 0.6, target_center = 0.6 * (300 - 1)
    target_center = target_midpoint_ratio * (height - 1)

    # 5) Calculate how many pixels we need to shift
    offset = int(round(target_center - label_center))

    # 6) Create a new white image array
    new_img_arr = np.full((height, width, 3), 255, dtype=np.uint8)

    # 7) Extract only the bounding box region from the old image
    old_img_arr = np.array(img)
    bounding_box = old_img_arr[label_top:label_bottom+1, :, :]  # shape: (bbox_height, width, 3)
    
    # 8) Identify which pixels in bounding_box are non-white
    #    "white" here is if all channels >= 250
    box_mask = np.any(bounding_box < 250, axis=2)  # shape: (bbox_height, width)

    # 9) We'll place these pixels into the new image at the offset location
    bbox_height = bounding_box.shape[0]

    # We get coordinates of all nonwhite pixels in the bounding region
    rows, cols = np.where(box_mask)  # these are relative to the bounding box
    # The absolute row in the new image is:
    new_rows = rows + label_top + offset

    # 10) Filter out any that fall outside [0, height)
    valid_mask = (new_rows >= 0) & (new_rows < height)
    valid_new_rows = new_rows[valid_mask]
    valid_cols = cols[valid_mask]
    # For indexing the bounding_box, we also filter "rows" the same way
    valid_old_rows = rows[valid_mask]

    # 11) Copy nonwhite pixels from bounding_box to new_img_arr
    new_img_arr[valid_new_rows, valid_cols] = bounding_box[valid_old_rows, valid_cols]

    # 12) Convert back to a PIL image and save
    new_img = Image.fromarray(new_img_arr, mode="RGB")
    new_img.save(dst_path)

def main():
    # Process each PNG in the source directory
    for filename in os.listdir(src_dir):
        if not filename.lower().endswith(".png"):
            continue

        src_path = os.path.join(src_dir, filename)
        dst_path = os.path.join(dst_dir, filename)
        process_image(src_path, dst_path)

if __name__ == "__main__":
    main()
