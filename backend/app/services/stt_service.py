"""
Phase 01 — Speech-to-Text Service

Uses OpenAI Whisper to transcribe uploaded audio recordings from field assessments,
after-action reviews, and instructor voice logs.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.m4a") -> dict:
    """
    Transcribe audio_bytes using OpenAI Whisper.

    Returns:
        {"transcript": str, "language": str, "duration_seconds": float | None}
    """
    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set — STT unavailable")
        return {
            "transcript": "[Speech-to-text unavailable — set OPENAI_API_KEY]",
            "language": "unknown",
            "duration_seconds": None,
        }

    try:
        import openai
        client = openai.OpenAI(api_key=settings.openai_api_key)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename

        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
        )
        return {
            "transcript": response.text,
            "language": getattr(response, "language", "en"),
            "duration_seconds": getattr(response, "duration", None),
        }
    except Exception as exc:
        logger.error("STT failed: %s", exc)
        return {"transcript": f"Transcription error: {exc}", "language": "unknown", "duration_seconds": None}


def save_audio_locally(audio_bytes: bytes, filename: str) -> str:
    """Save audio to data_local/audio/ and return relative path."""
    settings = get_settings()
    audio_dir = Path(settings.data_local_dir) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    dest = audio_dir / filename
    dest.write_bytes(audio_bytes)
    return str(dest)
