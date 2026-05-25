"""Anonymize a crop by masking regions that may contain student identifiers.

Per Paper 2's privacy design, identifier regions are erased from the crop
BEFORE the image is sent to any external API. Two modes:

  - 'top_strip' (default): paints over the top 8% of the image, where
    name/ID bubbles typically appear on the GRADEOPS template.
  - 'none': pass-through (use when you know the crop is already free of
    identifiers — e.g. the crop was already taken from below the ID area).

In production the anonymizer should read bbox coordinates from the rubric
metadata so it knows exactly which sub-regions contain identifiers.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from PIL import Image, ImageDraw


def anonymize_crop(crop_path: str, output_dir: str, mode: str = "top_strip") -> str:
    """Anonymize a crop and write the result. Returns the new path."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(crop_path).convert("RGB")
    if mode == "none":
        out = output_dir / f"anon_{uuid.uuid4().hex[:10]}.png"
        img.save(str(out), format="PNG")
        return str(out)

    w, h = img.size
    strip_h = int(h * 0.08)
    draw = ImageDraw.Draw(img)
    # Paint white over the top strip to remove any ID/name region
    draw.rectangle([0, 0, w, strip_h], fill="white")
    # Add a thin grey line as a visual marker that anonymization happened
    draw.line([0, strip_h, w, strip_h], fill=(200, 200, 200), width=2)

    out = output_dir / f"anon_{uuid.uuid4().hex[:10]}.png"
    img.save(str(out), format="PNG")
    return str(out)
