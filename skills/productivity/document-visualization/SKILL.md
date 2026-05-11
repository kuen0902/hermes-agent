---
name: document-visualization
description: High-precision rendering of Markdown and documents into images using Python/PIL.
thumbnail: 🖼️
---

# Document Visualization

Skills for rendering Markdown and other text documents into high-quality, perfectly aligned images. This is the preferred method for viewing `.md` files to ensure perfect CJK character support and table alignment.

## 🚀 Trigger Conditions
- User asks to "open", "view", or "read" a `.md` file.
- The default workflow for this user (replacing `mdcat`).
- Visualizing itineraries, financial reports, or logs.

## 🛠️ Key Workflows

### 1. High-Precision Markdown Render
Used as the default replacement for `mdcat`. 
- **Font**: Must use `/System/Library/Fonts/PingFang.ttc` or `/Library/Fonts/Arial Unicode.ttf`.
- **Theme**: Dark iTerm2-style with "traffic light" dots.
- **Dynamic Height**: Calculate `len(lines) * line_height + margins` to prevent clipping.

### 3. Dynamic Long-Screenshot Engine
For logs or financial reports exceeding one screen height:
- **Measure First**: Read the file and calculate required height based on wrapped lines: `y_total = top_margin + (wrapped_line_count * line_height) + bottom_margin`.
- **Line Wrapping**: Always use `textwrap` to ensure long paragraphs don't clip horizontally.
- **Safety Buffer**: Add 100-200px of extra buffer at the bottom to ensure the "Architech Summary" or timestamp is never cut off.

## 🏆 Case Study: 2026-05-10
The user praised the "Perfect" capture of a 45-line worklog. Key success factors:
1. Dynamic pixel-perfect coordinate mapping.
2. Distinct coloring for Headers (Cyan), Tables (Green), and HR lines (Gray).
3. Using `/Library/Fonts/Arial Unicode.ttf` as the primary CJK engine for high compatibility.

## ⚠️ Pitfalls & Preferences
- **Alignment**: Never rely on `\t` or spaces for tables. Use absolute X-coordinates in `draw.text((x, y), ...)`.
- **Garbled Text**: Standard terminal tools often fail on CJK + Emoji. This PIL method is the "failsafe" workaround.
- **Storage**: **CRITICAL**: Do NOT save these to the User's Desktop or permanent directories. Save to `~/.hermes/scratch/`, display with the `MEDIA:` protocol, and consider them ephemeral.
- **No Explanation**: The user prefers the result immediately. Do not explain the rendering process unless it fails.

## 📝 Templates
- `templates/render_md_v2.py`: The robust long-screenshot engine script.
