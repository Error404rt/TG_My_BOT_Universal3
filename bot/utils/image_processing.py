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
    img = img.convert('L')
    
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
                       size=300, n_shades=16, invert=False, 
                       spiral_r1_f=1, thick_f=0.95, col_line=(0, 0, 0), 
                       col_bg=(255, 255, 255)):
    """
    Create a spiral image effect where the image is rendered on a spiral line.
    The spiral line gets thicker for darker areas and thinner for lighter areas.
    """
    try:
        gray_img, gray_array = process_image_to_grayscale(image_path, size, n_shades, invert)
        
        # Create output image
        output = Image.new('RGB', (size, size), col_bg)
        draw = ImageDraw.Draw(output, 'RGBA')
        
        # Generate spiral coordinates
        spiral_r1 = 0.5 * spiral_r1_f
        spiral_points = min(5000, size * 20)
        
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
        thin = 0.5
        thick = max(1, int(spiral_thickness * thick_f))
        
        # Draw spiral with varying thickness based on image brightness
        for i in range(len(spiral_pixels) - 1):
            x1, y1 = spiral_pixels[i]
            x2, y2 = spiral_pixels[i + 1]
            
            # Get brightness at this point
            if 0 <= x1 < size and 0 <= y1 < size:
                brightness = gray_array[y1, x1]
                normalized_brightness = brightness / 255.0
                line_thickness = int(thin + (thick - thin) * (1 - normalized_brightness))
                line_thickness = max(1, line_thickness)
                
                draw.line([(x1, y1), (x2, y2)], fill=col_line, width=line_thickness)
        
        return output
    
    except Exception as e:
        logger.error(f"Error creating spiral image: {e}")
        raise


def create_square_grid_image(image_path, grid_size=50, size=300, n_shades=16, 
                            invert=False, col_line=(0, 0, 0), col_bg=(255, 255, 255)):
    """
    Create a square grid image effect.
    The grid lines get thicker for darker areas and thinner for lighter areas.
    """
    try:
        gray_img, gray_array = process_image_to_grayscale(image_path, size, n_shades, invert)
        
        # Create output image
        output = Image.new('RGB', (size, size), col_bg)
        draw = ImageDraw.Draw(output, 'RGBA')
        
        # Create square grid
        cell_size = size // grid_size
        thin = 0.5
        thick = 2
        
        for y in range(0, size, cell_size):
            for x in range(0, size, cell_size):
                if y < size and x < size:
                    brightness = gray_array[y, x]
                    normalized = brightness / 255.0
                    line_thickness = int(thin + (thick - thin) * (1 - normalized))
                    line_thickness = max(1, line_thickness)
                    
                    # Draw square
                    x1, y1 = x, y
                    x2, y2 = min(x + cell_size, size), min(y + cell_size, size)
                    draw.rectangle([x1, y1, x2, y2], outline=col_line, width=line_thickness)
        
        return output
    
    except Exception as e:
        logger.error(f"Error creating square grid image: {e}")
        raise


def create_hexagon_grid_image(image_path, grid_size=50, size=300, n_shades=16, 
                             invert=False, col_line=(0, 0, 0), col_bg=(255, 255, 255)):
    """
    Create a hexagon grid image effect.
    The hexagon lines get thicker for darker areas and thinner for lighter areas.
    """
    try:
        gray_img, gray_array = process_image_to_grayscale(image_path, size, n_shades, invert)
        
        # Create output image
        output = Image.new('RGB', (size, size), col_bg)
        draw = ImageDraw.Draw(output, 'RGBA')
        
        # Create hexagon grid
        hex_size = size / grid_size
        thin = 0.5
        thick = 2
        
        for y in range(0, size, int(hex_size * 1.5)):
            for x in range(0, size, int(hex_size * 1.5)):
                if y < size and x < size:
                    brightness = gray_array[min(y, size-1), min(x, size-1)]
                    normalized = brightness / 255.0
                    line_thickness = int(thin + (thick - thin) * (1 - normalized))
                    line_thickness = max(1, line_thickness)
                    
                    # Draw hexagon
                    hex_points = create_hexagon_points(x, y, hex_size)
                    if hex_points:
                        draw.polygon(hex_points, outline=col_line, width=line_thickness)
        
        return output
    
    except Exception as e:
        logger.error(f"Error creating hexagon grid image: {e}")
        raise


def create_hexagon_points(cx, cy, size):
    """Create points for a hexagon centered at (cx, cy)"""
    points = []
    for i in range(6):
        angle = i * 60 * np.pi / 180
        x = cx + size * np.cos(angle)
        y = cy + size * np.sin(angle)
        points.append((x, y))
    return points


def create_double_spiral_image(image_path1, image_path2=None, spiral_thickness=2, 
                              spiral_turns=50, size=300, n_shades=16, 
                              col_line1=(255, 0, 0), col_line2=(0, 0, 255), 
                              col_bg=(255, 255, 255)):
    """
    Create a double spiral image effect with two images rendered on the same spiral.
    """
    try:
        gray_img1, gray_array1 = process_image_to_grayscale(image_path1, size, n_shades, False)
        
        # If second image not provided, use inverted first image
        if image_path2 is None:
            gray_img2, gray_array2 = process_image_to_grayscale(image_path1, size, n_shades, True)
        else:
            gray_img2, gray_array2 = process_image_to_grayscale(image_path2, size, n_shades, False)
        
        # Create output image
        output = Image.new('RGB', (size, size), col_bg)
        draw = ImageDraw.Draw(output, 'RGBA')
        
        # Generate spiral coordinates
        spiral_r1 = 0.5
        spiral_points = min(5000, size * 20)
        
        spiral = spiral_coords(
            xo=0.5,
            yo=0.5,
            n_points=int(spiral_points),
            n_turns=spiral_turns,
            r0=0,
            r1=spiral_r1,
            offset_angle=0
        )
        
        spiral_pixels = [(int(x * size), int(y * size)) for x, y in spiral]
        
        thin = 0.5
        thick = max(1, int(spiral_thickness * 0.95))
        
        # Draw first spiral
        for i in range(len(spiral_pixels) - 1):
            x1, y1 = spiral_pixels[i]
            x2, y2 = spiral_pixels[i + 1]
            
            if 0 <= x1 < size and 0 <= y1 < size:
                brightness = gray_array1[y1, x1]
                normalized = brightness / 255.0
                line_thickness = int(thin + (thick - thin) * (1 - normalized))
                line_thickness = max(1, line_thickness)
                draw.line([(x1, y1), (x2, y2)], fill=col_line1, width=line_thickness)
        
        # Draw second spiral (offset)
        offset_spiral = spiral_coords(
            xo=0.5,
            yo=0.5,
            n_points=int(spiral_points),
            n_turns=spiral_turns,
            r0=0.05,
            r1=0.45,
            offset_angle=0
        )
        
        offset_spiral_pixels = [(int(x * size), int(y * size)) for x, y in offset_spiral]
        
        for i in range(len(offset_spiral_pixels) - 1):
            x1, y1 = offset_spiral_pixels[i]
            x2, y2 = offset_spiral_pixels[i + 1]
            
            if 0 <= x1 < size and 0 <= y1 < size:
                brightness = gray_array2[y1, x1]
                normalized = brightness / 255.0
                line_thickness = int(thin + (thick - thin) * (1 - normalized))
                line_thickness = max(1, line_thickness)
                draw.line([(x1, y1), (x2, y2)], fill=col_line2, width=line_thickness)
        
        return output
    
    except Exception as e:
        logger.error(f"Error creating double spiral image: {e}")
        raise


def create_triangle_grid_image(image_path, grid_size=50, size=300, n_shades=16, 
                              invert=False, col_line=(0, 0, 0), col_bg=(255, 255, 255)):
    """
    Create a triangle grid image effect.
    """
    try:
        gray_img, gray_array = process_image_to_grayscale(image_path, size, n_shades, invert)
        
        # Create output image
        output = Image.new('RGB', (size, size), col_bg)
        draw = ImageDraw.Draw(output, 'RGBA')
        
        # Create triangle grid
        cell_size = size // grid_size
        thin = 0.5
        thick = 2
        
        for y in range(0, size, cell_size):
            for x in range(0, size, cell_size):
                if y < size and x < size:
                    brightness = gray_array[y, x]
                    normalized = brightness / 255.0
                    line_thickness = int(thin + (thick - thin) * (1 - normalized))
                    line_thickness = max(1, line_thickness)
                    
                    # Draw triangle
                    x1, y1 = x, y
                    x2, y2 = x + cell_size, y
                    x3, y3 = x + cell_size // 2, y + cell_size
                    
                    triangle = [(x1, y1), (x2, y2), (x3, y3)]
                    draw.polygon(triangle, outline=col_line, width=line_thickness)
        
        return output
    
    except Exception as e:
        logger.error(f"Error creating triangle grid image: {e}")
        raise


def create_diamond_grid_image(image_path, grid_size=50, size=300, n_shades=16, 
                             invert=False, col_line=(0, 0, 0), col_bg=(255, 255, 255)):
    """
    Create a diamond/rhombus grid image effect.
    """
    try:
        gray_img, gray_array = process_image_to_grayscale(image_path, size, n_shades, invert)
        
        # Create output image
        output = Image.new('RGB', (size, size), col_bg)
        draw = ImageDraw.Draw(output, 'RGBA')
        
        # Create diamond grid
        cell_size = size // grid_size
        thin = 0.5
        thick = 2
        
        for y in range(0, size, cell_size):
            for x in range(0, size, cell_size):
                if y < size and x < size:
                    brightness = gray_array[y, x]
                    normalized = brightness / 255.0
                    line_thickness = int(thin + (thick - thin) * (1 - normalized))
                    line_thickness = max(1, line_thickness)
                    
                    # Draw diamond
                    cx = x + cell_size // 2
                    cy = y + cell_size // 2
                    diamond = [
                        (cx, y),
                        (x + cell_size, cy),
                        (cx, y + cell_size),
                        (x, cy)
                    ]
                    draw.polygon(diamond, outline=col_line, width=line_thickness)
        
        return output
    
    except Exception as e:
        logger.error(f"Error creating diamond grid image: {e}")
        raise


def create_pentagon_grid_image(image_path, grid_size=50, size=300, n_shades=16, 
                              invert=False, col_line=(0, 0, 0), col_bg=(255, 255, 255)):
    """
    Create a pentagon grid image effect.
    """
    try:
        gray_img, gray_array = process_image_to_grayscale(image_path, size, n_shades, invert)
        
        # Create output image
        output = Image.new('RGB', (size, size), col_bg)
        draw = ImageDraw.Draw(output, 'RGBA')
        
        # Create pentagon grid
        pentagon_size = size / grid_size
        thin = 0.5
        thick = 2
        
        for y in range(0, size, int(pentagon_size * 1.5)):
            for x in range(0, size, int(pentagon_size * 1.5)):
                if y < size and x < size:
                    brightness = gray_array[min(y, size-1), min(x, size-1)]
                    normalized = brightness / 255.0
                    line_thickness = int(thin + (thick - thin) * (1 - normalized))
                    line_thickness = max(1, line_thickness)
                    
                    # Draw pentagon
                    pentagon_points = create_pentagon_points(x, y, pentagon_size)
                    if pentagon_points:
                        draw.polygon(pentagon_points, outline=col_line, width=line_thickness)
        
        return output
    
    except Exception as e:
        logger.error(f"Error creating pentagon grid image: {e}")
        raise


def create_pentagon_points(cx, cy, size):
    """Create points for a pentagon centered at (cx, cy)"""
    points = []
    for i in range(5):
        angle = (i * 72 - 90) * np.pi / 180
        x = cx + size * np.cos(angle)
        y = cy + size * np.sin(angle)
        points.append((x, y))
    return points


def save_image_to_bytes(image, format='PNG'):
    """
    Save PIL Image to bytes.
    """
    img_bytes = io.BytesIO()
    image.save(img_bytes, format=format)
    img_bytes.seek(0)
    return img_bytes.getvalue()

