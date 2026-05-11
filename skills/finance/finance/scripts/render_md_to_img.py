import os
import textwrap
import sys
from PIL import Image, ImageDraw, ImageFont

def render_md_to_img(file_path, output_path=None):
    """
    High-precision Markdown renderer for the System Architect persona.
    Ensures CJK alignment, dynamic height, and iTerm-style aesthetics.
    """
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Config
    width = 1100
    line_spacing = 10
    top_pad = 60
    left_pad = 50
    bg_color = (18, 18, 18)
    
    # Font Fallbacks
    font_paths = [
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/PingFang.ttc"
    ]
    font_path = next((p for p in font_paths if os.path.exists(p)), None)
    
    try:
        f_h1 = ImageFont.truetype(font_path, 28)
        f_reg = ImageFont.truetype(font_path, 18)
    except:
        f_h1 = f_reg = ImageFont.load_default()

    # Pass 1: Detailed Layout & Height calculation
    layout = []
    total_h = top_pad
    for line in lines:
        line = line.rstrip()
        if not line:
            total_h += 20
            continue
            
        if line.startswith('#'):
            layout.append(('TEXT', line, f_h1, (0, 200, 255)))
            total_h += 45 + line_spacing
        elif '|' in line:
            layout.append(('TEXT', line, f_reg, (180, 255, 180)))
            total_h += 35 + line_spacing
        elif line.startswith('---'):
            layout.append(('HR', None, None, None))
            total_h += 25
        else:
            # Wrap normal text
            wrapped = textwrap.wrap(line, width=85)
            for wl in wrapped:
                layout.append(('TEXT', wl, f_reg, (235, 235, 235)))
                total_h += 30 + line_spacing

    final_h = total_h + 100
    img = Image.new('RGB', (width, int(final_h)), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Window Style Header
    draw.rectangle([0, 0, width, 40], fill=(40, 40, 40))
    # Red, Yellow, Green dots
    draw.ellipse([15, 12, 27, 24], fill=(255, 95, 86))
    draw.ellipse([40, 12, 52, 24], fill=(255, 189, 46))
    draw.ellipse([65, 12, 77, 24], fill=(39, 201, 63))
    
    # Drawing content
    curr_y = top_pad
    for entry in layout:
        type, text, font, color = entry
        if type == 'TEXT':
            draw.text((left_pad, curr_y), text, fill=color, font=font)
            curr_y += (45 if font == f_h1 else 30) + line_spacing
        elif type == 'HR':
            draw.rectangle([left_pad, curr_y+10, width-left_pad, curr_y+11], fill=(80, 80, 80))
            curr_y += 25

    if not output_path:
        output_path = os.path.expanduser("~/.hermes/scratch/render_output.png")
    
    img.save(output_path)
    print(f"MEDIA:{output_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        render_md_to_img(sys.argv[1])
