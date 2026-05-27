"""Qwen2-VL adapter via HuggingFace transformers.

This is the production-target adapter the brief asks for. It is intentionally
behind a lazy import so the demo runs without GPU dependencies installed.

To enable:
  1. Uncomment transformers / torch / accelerate in requirements.txt
  2. Install on a GPU host
  3. Set OCR_BACKEND=qwen_vl in .env

On a CPU-only machine the model will load extremely slowly. For Nougat
(a math-specialised alternative), swap Qwen2-VL-7B for facebook/nougat-base
and update the processor calls accordingly.
"""
from __future__ import annotations

from pathlib import Path


_model = None
_processor = None


def _load_model():
    """Lazy load Qwen2-VL. Raises an informative error if HF deps aren't present."""
    global _model, _processor
    if _model is not None:
        return _model, _processor

    try:
        import torch  # noqa: F401
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
    except ImportError as e:
        raise RuntimeError(
            "Qwen-VL adapter requires `transformers` and `torch`. "
            "Either install them (see requirements.txt comments) or set "
            "OCR_BACKEND=hosted in your .env to use the hosted Claude vision adapter."
        ) from e

    model_id = "Qwen/Qwen2-VL-7B-Instruct"
    _processor = AutoProcessor.from_pretrained(model_id)
    _model = Qwen2VLForConditionalGeneration.from_pretrained(
        model_id, torch_dtype="auto", device_map="auto"
    )
    return _model, _processor


TRANSCRIBE_PROMPT = (
    "You are an OCR system specialised in handwritten student exam answers, "
    "including math, derivations and free text. Transcribe the handwritten "
    "content in the image LITERALLY. Use LaTeX for math. Preserve line breaks. "
    "Mark illegible segments as [illegible]. Output the transcript only."
)


def transcribe(image_path: str) -> str:
    from PIL import Image

    model, processor = _load_model()
    image = Image.open(image_path).convert("RGB")

    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": TRANSCRIBE_PROMPT},
        ],
    }]
    text_prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=[text_prompt], images=[image], return_tensors="pt").to(model.device)

    out_ids = model.generate(**inputs, max_new_tokens=1500)
    out_trimmed = [o[len(i):] for i, o in zip(inputs.input_ids, out_ids)]
    text = processor.batch_decode(out_trimmed, skip_special_tokens=True)[0]
    return text.strip()
