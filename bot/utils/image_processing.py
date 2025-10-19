
"""
Image processing utilities for creating spiral and other artistic effects.
Translated from R code at: https://github.com/cj-holmes/photos-on-spirals
"""

import numpy as np
from PIL import Image, ImageDraw
import io
import logging
from scipy import ndimage

logger = logging.getLogger(__name__)


def spiral_coords(xo, yo, n_points, n_turns, r0, r1, offset_angle):
    """
    Create spiral coordinates.
    
    Args:
        xo: Spiral origin x coordinate
        yo: Spiral origin y coordinate
        n_points: Number of points on whole spiral (equally spaced in angle)
        n_turns: Number of turns in spiral
        r0: Spiral inner radius
        r1: Spiral outer radius
        offset_angle: Offset angle for start of spiral (in degrees)
    
    Returns:
        List of (x, y) tuples representing spiral coordinates
    """
    b = (r1 - r0) / (2 * np.pi * n_turns)
    l = np.linspace(0, 2 * np.pi * n_turns, n_points)
    
    offset_rad = offset_angle * (np.pi / 180)
    
    x = (r0 + (b * l)) * np.cos(l + offset_rad) + xo
    y = (r0 + (b * l)) * np.sin(l + offset_rad) + yo
    
    return list(zip(x, y))


def process_image_to_grayscale(image_path, size=300, n_shades=16, invert=False):
    """
    Process image: resize, crop to square, convert to grayscale, quantize, and flip.
    
    Args:
        image_path: Path to image file or PIL Image object
        size: Size of the square output (default 300)
        n_shades: Number of gray shades (default 16)
        invert: Whether to invert the image (default False)
    
    Returns:
        PIL Image object (grayscale, quantized) and numpy array
    """
    if isinstance(image_path, Image.Image):
        img = image_path
    else:
        img = Image.open(image_path)
    
    # Resize image
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    
    # Convert to grayscale
    img = img.convert("L")
    
    # Quantize to reduce number of shades
    img = img.quantize(colors=n_shades)
    
    # Flip vertically
    img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    
    # Invert if needed
    if invert:
        img = Image.eval(img, lambda x: 255 - x)
    
    gray_array = np.array(img)
    return img, gray_array


def create_spiral_image(image_path, spiral_thickness=2, spiral_turns=50, 
                       size=500, n_shades=256, invert=False, 
                       spiral_r1_f=1, thick_f=0.95, col_line=(0, 0, 0), 
                       col_bg=(255, 255, 255)):
    """
    Create a spiral image effect where the image is rendered on a spiral line.
    The spiral line gets thicker for darker areas and thinner for lighter areas.
    """
    try:
        gray_img, gray_array = process_image_to_grayscale(image_path, size, n_shades, invert)
        
        # Create output image
        output = Image.new("RGB", (size, size), col_bg)
        draw = ImageDraw.Draw(output, "RGBA")
        
        # Generate spiral coordinates
        spiral_r1 = 0.5 * spiral_r1_f
        spiral_points = min(15000, size * 30)
        
        spiral = spiral_coords(
            xo=0.5,
            yo=0.5,
            n_points=int(spiral_points),
            n_turns=spiral_turns,
            r0=0,
            r1=spiral_r1,
            offset_angle=0
        )
        
        # Normalize spiral coordinates to pixel space
        spiral_pixels = [(int(x * size), int(y * size)) for x, y in spiral]
        
        # Calculate thickness values based on image brightness
        # New approach: Modulate the color of the spiral line itself.
        # This will make the spiral lines darker or lighter based on the underlying image.
        for i in range(len(spiral_pixels) - 1):
            x1, y1 = spiral_pixels[i]
            x2, y2 = spiral_pixels[i + 1]
            if 0 <= x1 < size and 0 <= y1 < size:
                brightness = gray_array[y1, x1]
                normalized_brightness = brightness / 255.0
                
                # Interpolate color from black to white based on brightness
                # Darker pixels in the original image will result in darker spiral lines
                # Lighter pixels in the original image will result in lighter spiral lines
                line_color_value = int(255 * normalized_brightness)
                
                draw.line([(x1, y1), (x2, y2)], fill=(line_color_value, line_color_value, line_color_value), width=spiral_thickness)
        
        return output
    
    except Exception as e:
        logger.error(f"Error creating spiral image: {e}")
        raise

def save_image_to_bytes(image, format='PNG'):
    """
    Save PIL Image to bytes.
    """
    img_bytes = io.BytesIO()
    image.save(img_bytes, format=format)
    img_bytes.seek(0)
    return img_bytes.getvalue()

