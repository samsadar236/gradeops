"""Detect and crop answer regions from a page image.

Two modes:
  - Template-marker mode: looks for fiducial markers (filled black squares)
    at the corners of the answer sheet, then crops the rectangle they bound.
    This is the production path, matching the Vanhoyweghen et al. (2026)
    sheet layout (Figure 7 in that paper).
  - Fallback mode: if no markers are found, treat the whole page as one
    answer region. Useful for ad-hoc demos and for scans of arbitrary
    exam papers that don't follow the GRADEOPS template.

For a fully production setup, the question-to-crop binding (Q1 vs Q2a) is
determined by detecting labeled regions inside the marker rectangle. Here
we expose a simple `detect_answer_regions` that returns one box per page
(the fallback), but the structure supports multi-region pages.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def _find_corner_markers(gray: np.ndarray) -> list[tuple[int, int]] | None:
    """Locate the four corner fiducial markers (filled black squares).

    Returns four (x, y) centroids or None if fewer than 4 are found.
    """
    # Threshold to isolate dark regions
    _, bw = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    h, w = gray.shape
    img_area = h * w
    candidates: list[tuple[int, int, int]] = []  # (x, y, area)

    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        area = cw * ch
        # Marker heuristics: ~square, small fraction of page, dark fill
        if area < img_area * 0.0001 or area > img_area * 0.01:
            continue
        ratio = cw / max(ch, 1)
        if not 0.7 < ratio < 1.4:
            continue
        # Mostly-filled black?
        roi = bw[y:y + ch, x:x + cw]
        fill = roi.mean() / 255.0
        if fill < 0.6:
            continue
        candidates.append((x + cw // 2, y + ch // 2, area))

    if len(candidates) < 4:
        return None

    # Pick the candidates closest to the four corners of the page.
    corners = [(0, 0), (w, 0), (0, h), (w, h)]
    chosen: list[tuple[int, int]] = []
    used = set()
    for cx, cy in corners:
        best = None
        best_d = float("inf")
        for i, (x, y, _) in enumerate(candidates):
            if i in used:
                continue
            d = (x - cx) ** 2 + (y - cy) ** 2
            if d < best_d:
                best_d = d
                best = (i, x, y)
        if best is None:
            return None
        used.add(best[0])
        chosen.append((best[1], best[2]))
    return chosen  # [TL, TR, BL, BR]


def detect_answer_regions(page_image_path: str) -> list[dict]:
    """Return a list of {bbox, question_id} for each detected answer region.

    Falls back to a single full-page region if markers are absent.
    """
    img = cv2.imread(page_image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read image: {page_image_path}")
    h, w = img.shape

    markers = _find_corner_markers(img)
    if markers is not None:
        xs = [m[0] for m in markers]
        ys = [m[1] for m in markers]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        # Pad inward 1% so the markers themselves aren't included
        pad = int(min(w, h) * 0.01)
        return [{
            "bbox": {"x": x0 + pad, "y": y0 + pad,
                     "w": (x1 - x0) - 2 * pad, "h": (y1 - y0) - 2 * pad},
            "question_id": "Q1",
        }]

    # Fallback: whole page is one answer region
    return [{
        "bbox": {"x": 0, "y": 0, "w": w, "h": h},
        "question_id": "Q1",
    }]


def crop_region(page_image_path: str, bbox: dict, output_dir: str) -> str:
    """Crop the given bbox from the page image and save as PNG."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(page_image_path)
    x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
    crop = img.crop((x, y, x + w, y + h))
    out = output_dir / f"crop_{uuid.uuid4().hex[:10]}.png"
    crop.save(str(out), format="PNG")
    return str(out)
