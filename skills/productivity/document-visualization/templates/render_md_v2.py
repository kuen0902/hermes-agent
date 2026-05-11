import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

def render_md_to_image(file_path, output_path, width=1200):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return f"Error: {e}"

    # Setup
    line_spacing = 12
    margin_top, margin_left, margin_bottom = 70, 50, 100
    bg_color = (15, 15, 15)
    
    font_path = "/Library/Fonts/Arial Unicode.ttf"
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/STHeiti Light.ttc"
    
    try:
        f_h1 = ImageFont.truetype(font_path, 30)
        f_h2 = ImageFont.truetype(font_path, 24)
        f_reg = ImageFont.truetype(font_path, 18)
    except:
        f_h1 = f_h2 = f_reg = ImageFont.load_default()

    # Pass 1: Height calculation
    y_offset = margin_top
    draw_data = []
    for line in lines:
        line = line.strip()
        if not line:
            y_offset += 25
            continue
        
        # Style logic
        color = (230,230,230)
        f = f_reg
        if line.startswith('# '):
            f, color, y_offset = f_h1, (0, 200, 255), y_offset + 10
        elif line.startswith('## '):
            f, color, y_offset = f_h2, (255, 255, 100), y_offset + 5
        elif '|' in line:
            color = (170, 255, 170)
        
        draw_data.append((line, y_offset, f, color))
        y_offset += 32 + line_spacing

    # Create image
    img = Image.new('RGB', (width, int(y_offset + margin_bottom)), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # OS Header
    draw.rectangle([0, 0, width, 45], fill=(40, 40, 40))
    # Dots (Red, Yellow, Green)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        draw.ellipse([15+i*25, 13, 30+i*25, 28], fill=c)
    
    # Draw content
    for text, y, font, color in draw_data:
        draw.text((margin_left, y), text, fill=color, font=font)

    img.save(output_path)
    return f"MEDIA:{output_path}"
