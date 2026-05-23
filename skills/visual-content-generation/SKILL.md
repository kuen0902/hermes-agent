---
name: visual-content-generation
description: "Umbrella skill for AI-guided visual content creation (infographics, comics, article illustrations, and stylized art)."
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [visual-content, ai-art, infographics, comics, illustration, pixel-art]
---

# Visual Content Generation

This umbrella skill covers structured workflows for generating rich visual assets using Multimodal AI and Image Generation tools.

## 1. Structured Illustrations (Baoyu Framework)
- **Article Illustrator**: Generate consistent illustrations (Type × Style × Palette) for technical or narrative content.
- **Comics (baoyu-comic)**: Create educational or biographical knowledge comics with narrative flow.
- **Infographics (baoyu-infographic)**: Build high-density information graphics (21 layouts × 21 styles).

## 2. Stylized Art Generation
- **Pixel Art**: Generate art with era-specific palettes (NES, PICO-8, Game Boy).
- **Humanizing AI Content**: Techniques for stripping "AI-isms" and adding a genuine voice to generated descriptions and alt-text.

## Core Workflow
1. **Analyze Content**: Parse the source material (article, script, or data).
2. **Select Dimensions**: Choose Layout/Type, Style, and Palette.
3. **Draft Prompts**: Construct structured prompts specifically for the active backend (e.g., FAL FLUX).
4. **Generate & Iterate**: Use `image_generate`, download via `curl`, and refine as needed.
