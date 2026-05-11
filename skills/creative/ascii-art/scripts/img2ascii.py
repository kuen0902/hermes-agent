import sys
import os
try:
    from PIL import Image
except ImportError:
    print("Error: Pillow not installed. Run: python3 -m pip install pillow --break-system-packages")
    sys.exit(1)

def img_to_ascii(img_path, width=80, palette_type="standard"):
    # Standard palette: characters from darkest to lightest
    PALETTES = {
        "standard": ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."],
        "block": ["█", "▓", "▒", "░", " "],
        "minimal": ["#", "o", ".", " "]
    }
    
    chars = PALETTES.get(palette_type, PALETTES["standard"])
    
    try:
        img = Image.open(img_path)
    except Exception as e:
        print(f"Error opening image: {e}")
        return

    # Maintain aspect ratio (ASCII characters are usually ~2x taller than wide)
    w, h = img.size
    aspect_ratio = h / w
    new_height = int(aspect_ratio * width * 0.5)
    img = img.resize((width, new_height), Image.Resampling.LANCZOS)
    
    # Convert to grayscale
    img = img.convert("L")
    
    # Use robust pixel access
    pixels = list(img.getdata())
    
    # Map pixels to characters
    range_width = 256 // len(chars)
    ascii_str = "".join([chars[min(p // range_width, len(chars)-1)] for p in pixels])
    
    # Format into lines
    ascii_image = "\n".join([ascii_str[i:(i + width)] for i in range(0, len(ascii_str), width)])
    print(ascii_image)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 img2ascii.py <path_to_image> [width] [palette]")
        sys.exit(1)
    
    path = sys.argv[1]
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    palette = sys.argv[3] if len(sys.argv) > 3 else "standard"
    
    img_to_ascii(path, width, palette)
