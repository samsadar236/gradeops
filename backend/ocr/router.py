"""OCR router. Picks an adapter based on settings.ocr_backend.

This is the abstraction layer mentioned in the architecture diagram: any
new OCR model (Nougat, TrOCR, a fine-tuned model) plugs in by adding a new
adapter and a new branch here. The grader and the rest of the pipeline
don't change.
"""
from __future__ import annotations

from ..config import settings


def transcribe(image_path: str) -> str:
    """Dispatch to the configured OCR adapter."""
    backend = (settings.ocr_backend or "hosted").lower()
    if backend == "qwen_vl":
        from . import qwen_vl_adapter
        return qwen_vl_adapter.transcribe(image_path)
    # default
    from . import hosted_adapter
    return hosted_adapter.transcribe(image_path)
