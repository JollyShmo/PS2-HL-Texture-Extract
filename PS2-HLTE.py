# Texture Extraction Script #
# --------------------------#
# This script extracts textures from a binary file, assumed to be in a custom format
# (such as used by certain PS2 or other older games).
# The extraction is based on searching for texture names and associated data patterns
# inside the binary file, processing texture palettes (256 colors) and pixel indices.
# The script then saves each texture as an indexed color image (.bmp) with the texture's
# sanitized name.
#
# The key operations of the script include:
# 1. Searching for texture names that start with 'psx_'.
# 2. Extracting the 256-color palette (RGB values only, ignoring alpha).
# 3. Decoding texture pixel indices (which reference the palette).
# 4. Creating an image from the extracted indices and palette, and saving the image.
#
# Assumptions:
# - Texture names are preceded by a 'psx_' identifier.
# - Each texture data section starts with the bytes 'FF FF FF 80' and includes
#   a size pattern with width and height.
# - Each texture uses a 256-color palette.
# - The size pattern before the texture data contains width and height (2 bytes each).
#
# Required Libraries:
# - numpy (for handling arrays of pixel indices)
# - PIL (Python Imaging Library) to generate and save images
#--------------------------------------------------------------#

import numpy as np
from PIL import Image
import re

def sanitize_filename(filename):
    """Sanitize filenames by replacing invalid characters."""
    return re.sub(r'[\x00]', '_', filename)

def extract_palette(texture_data, num_colors=256):
    """Extract a palette from the texture data. Assuming 256-color palette."""
    palette = []
    for i in range(num_colors):
        # Extract each color as 4 bytes (RGBA format)
        start = i * 4
        color = texture_data[start:start+4]
        r, g, b, a = color
        palette.append((r, g, b))  # Discard alpha, keep RGB only
    return palette

def extract_texture_indices(texture_data, palette, width, height):
    """Extract indices of the palette for each pixel in the texture."""
    indices = np.zeros((height, width), dtype=np.uint8)
    
    for y in range(height):
        for x in range(width):
            # Each pixel is 1 byte, so we get the palette index for each pixel
            pixel_idx = texture_data[y * width + x]
            indices[y, x] = pixel_idx
    
    return indices

def extract_textures(file_path):
    with open(file_path, "rb") as file:
        data = file.read()

    start = 0
    texture_count = 0

    # Search for all names starting with 'psx_' (70 73 78 5F)
    while start < len(data):
        # Look for the texture name prefix 'psx_' (70 73 78 5F)
        name_start = data.find(b'\x70\x73\x78\x5F', start)
        if name_start != -1:
            name_start = data.find(b'\x67\x6D\x61\x6E', start)
        
        if name_start == -1:
            break  # No more texture names found

        print(f"Found texture name start at offset {name_start:#x}")

        # Now extract the texture name (null-terminated string after 'psx_')
        name_end = name_start + 4
        while name_end + 3 < len(data) and data[name_end:name_end + 3] != b'\x00\x00\x00':  # Null-terminated string with 3 zeros
            name_end += 1
        
        texture_name = data[name_start:name_end].decode('ascii', errors='ignore')

        # Sanitize texture name to remove null characters or invalid characters
        texture_name = sanitize_filename(texture_name)

        # Skip textures with names ending in '.BMP'
        if texture_name.endswith('.BMP'):
            print(f"Skipping texture {texture_name} (BMP file)")
            start = name_end  # Move to the next texture
            continue

        print(f"Texture name: {texture_name}")

        # Move to the next part of the file to search for the texture data (after the name)
        start = name_end

        # Now search for the texture data associated with this name
        # Look for texture data (starts with 'FF FF FF 80')
        texture_start = data.find(b'\xFF\xFF\xFF\x80', start)
        
        if texture_start == -1:
            break  # No more textures found

        print(f"Found texture data at offset {texture_start:#x}")

        # Search for the next texture name prefix 'psx_' or the end of the file
        next_texture_start = data.find(b'\x70\x73\x78\x5F', texture_start + 4)

        # If no other texture is found, end of file is the endpoint
        texture_end = next_texture_start if next_texture_start != -1 else len(data)

        print(f"Texture end found at offset {texture_end:#x}")

        # Extract texture data from the texture start to the next texture start or the end of the file
        texture_data = data[texture_start:texture_end]

        # Extract the 4-byte size pattern
        size_pattern_start = texture_start - 4
        if size_pattern_start >= 0:
            size_data = data[size_pattern_start:size_pattern_start + 4]  # Extract the 4-byte size pattern
            print(f"Detected raw size data: {size_data.hex()}")

            # Decode the size data (assuming width and height are both 2-byte values in little-endian)
            width = int.from_bytes(size_data[:2], byteorder='little')
            height = int.from_bytes(size_data[2:], byteorder='little')

            print(f"Decoded width: {width}, height: {height}")

            # Handle palette and pixel data extraction
            num_colors = 256  # Assume 256 color palette
            palette = extract_palette(texture_data, num_colors=num_colors)

            # Extract the indices of the palette for each pixel
            indices = extract_texture_indices(texture_data[num_colors * 4:], palette, width, height)

            # Convert the indices to an image (using "P" mode for indexed color images)
            image = Image.fromarray(indices, mode='P')

            # Set the palette in the image
            image.putpalette([component for color in palette for component in color])

            # Optionally save the image with the sanitized texture name (ensure it's saved as 8-bit indexed)
            image.save(f"{texture_name}.bmp")  # .bmp or .png will preserve 8-bit depth
            
            texture_count += 1

# Example usage:
file_path = "gman.dol"  # Replace with your actual file path
extract_textures(file_path)
