"""
Phase 01 — OCR Service

Uses Claude's vision capability to extract structured text from uploaded photos
of whiteboards, instructor notes, field assessments, and training materials.
"""
from __future__ import annotations

import base64
import logging
from pathlib import Path

import anthropic

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

_SYSTEM = """\
You are an OCR assistant for military training documents. Extract ALL visible text from the image
faithfully. If the image shows a whiteboard, notes, or evaluation form, preserve the structure.
Then provide a brief "extracted_context" field describing what type of document this appears to be.

Return JSON: {"extracted_text": "...", "extracted_context": "...", "confidence": 0.0-1.0}
"""


def extract_text_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """
    Run OCR on image_bytes using Claude Vision.

    Returns:
        {"extracted_text": str, "extracted_context": str, "confidence": float}
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — OCR unavailable")
        return {
            "extracted_text": "[OCR unavailable — set ANTHROPIC_API_KEY]",
            "extracted_context": "unknown",
            "confidence": 0.0,
        }

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=2048,
            system=_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": "Extract all text from this image."},
                    ],
                }
            ],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        import json
        return json.loads(raw)
    except Exception as exc:
        logger.error("OCR failed: %s", exc)
        return {"extracted_text": f"OCR error: {exc}", "extracted_context": "error", "confidence": 0.0}


def save_upload_locally(file_bytes: bytes, filename: str) -> str:
    """Save uploaded file to data_local/uploads/ and return relative path."""
    settings = get_settings()
    upload_dir = Path(settings.data_local_dir) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename
    dest.write_bytes(file_bytes)
    return str(dest)
