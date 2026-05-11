# Perfect Alignment Rendering for CJK Financial Reports

When creating terminal-style screenshots for financial reports (like TSMC Q1), standard Markdown renderers (`mdcat`, `glow`) often fail significantly due to the mixed width of **Chinese Characters**, **English Text**, and **Table Emojis** (🚀, 📈, ✅, 💎, ⭐).

## The "Pragmatic Architect" Solution

When a user complains that "the table is messy" or "misaligned", immediately switch to a custom PIL (Pillow) drawing script or the `rich` library.

### PIL Rendering Template (Perfect Alignment)

```python
from PIL import Image, ImageDraw, ImageFont
import os

# 1. Define high-compat CJK font paths
font_paths = ["/Library/Fonts/Arial Unicode.ttf", "/System/Library/Fonts/STHeiti Light.ttc"]
# ... load font_main, font_bold ...

# 2. Draw Table Headers with fixed X-coordinates
headers = [("項目 (Project)", 55), ("數值 (NT$)", 380), ("YoY 增減", 580), ("狀態 (Status)", 780)]
for text, x in headers:
    draw.text((x, y), text, fill=(120, 255, 255), font=font_main)

# 3. Draw Data Rows using the SAME X-coordinates
rows = [("營收 (Revenue)", "1,134.10 B", "+35.1%", "🚀 強勁成長")]
for item, val, yoy, status in rows:
    draw.text((55, y), item, fill=(245, 245, 245), font=font_main)
    draw.text((380, y), val, fill=(100, 255, 100), font=font_main)
    draw.text((580, y), yoy, fill=(255, 255, 100), font=font_main)
    draw.text((780, y), status, fill=(255, 100, 255), font=font_main)
```

## Key Learnings & Strategic Updates (2026-05-10)

### 1. The Dynamic Height Rule (Anti-Clipping)
Never use fixed canvas heights (e.g., 600px). Analyze the line count and content complexity to calculate the required vertical span dynamically.
- `height = (len(lines) * step) + padding`
- Use `textwrap.wrap(width=80)` for long paragraphs to prevent horizontal overflow.

### 2. The "No-Artifact" Protocol
The user explicitly forbids saving these screenshots to the Desktop or permanent dirs unless for email/archival purposes.
- Generate in `~/.hermes/scratch/`.
- Display via `MEDIA:`.

### 3. Default Transition
`mdcat` is officially downgraded to "legacy". High-precision image rendering is now the MANDATORY default for `.md` files to ensure perfect table alignment and clear CJK display.

## Reliable Font Chain (macOS)
1. `/Library/Fonts/Arial Unicode.ttf` (Highest compatibility for symbols/CJK)
2. `/System/Library/Fonts/STHeiti Light.ttc` or `Medium.ttc`
3. `/System/Library/Fonts/PingFang.ttc`

## Python Rendering Logic (V2 - Dynamic)
```python
import textwrap
# ... setup fonts ...
# Pass 1: Total height calculation
total_height = margin_top
for line in lines:
    if line.startswith('#'): total_height += 50
    elif '|' in line: total_height += 35
    else:
        # Wrap paragraphs
        wrapped = textwrap.wrap(line, width=85)
        total_height += len(wrapped) * 32
# Pass 2: Render to canvas
img = Image.new('RGB', (width, total_height + margin_bottom), color=(18, 18, 18))
```

