"""
TAK Server CoT subscriber.

Opens a persistent TCP (or TLS) connection to a TAK Server, streams CoT SA
messages, and auto-updates SoldierPosition records when a soldier's ATAK device
reports its location.

Soldiers are matched by:
  1. Soldier.tak_uid  == CoT uid  (exact device UID)
  2. Soldier.name (case-insensitive) contains CoT callsign  (fallback)

The subscriber runs as an asyncio background task started in main.py lifespan.
It silently no-ops when TAK_SERVER_HOST is not configured.
"""
from __future__ import annotations

import asyncio
import logging
import ssl
from datetime import datetime, timezone

from backend.app.db.database import get_session_factory
from backend.app.db.models import Soldier, SoldierPosition
from backend.app.services.cot_parser import CotPosition, parse_cot_stream

logger = logging.getLogger(__name__)

_RECONNECT_DELAY = 10  # seconds between reconnect attempts
_READ_SIZE       = 4096


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _upsert_position(cot: CotPosition) -> None:
    """Write CoT position into SoldierPosition — runs in a sync DB session."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        # Match by explicit tak_uid first, then callsign substring
        soldier = (
            db.query(Soldier).filter(Soldier.tak_uid == cot.uid).first()
            or db.query(Soldier).filter(
                Soldier.is_active == True,
                Soldier.name.ilike(f"%{cot.callsign}%"),
            ).first()
        )
        if not soldier:
            return

        pos = db.query(SoldierPosition).filter(SoldierPosition.soldier_id == soldier.id).first()
        if pos:
            pos.lat    = cot.lat
            pos.lon    = cot.lon
            # Keep existing MGRS / operational_status — only coordinates are auto-updated
        else:
            pos = SoldierPosition(
                soldier_id=soldier.id,
                lat=cot.lat,
                lon=cot.lon,
                operational_status="available",
            )
            db.add(pos)
        db.commit()
        logger.debug("Position updated: %s → (%.5f, %.5f)", soldier.name, cot.lat, cot.lon)
    except Exception as exc:
        logger.error("DB error updating position for uid=%s: %s", cot.uid, exc)
        db.rollback()
    finally:
        db.close()


async def _handle_stream(reader: asyncio.StreamReader) -> None:
    buffer = ""
    while True:
        data = await reader.read(_READ_SIZE)
        if not data:
            raise ConnectionResetError("TAK Server closed connection")
        buffer += data.decode("utf-8", errors="ignore")
        events, buffer = parse_cot_stream(buffer)
        for cot in events:
            if cot.is_friendly:
                # Offload DB write to thread pool so we don't block the event loop
                await asyncio.get_event_loop().run_in_executor(None, _upsert_position, cot)


async def run_tak_subscriber(host: str, port: int, use_tls: bool = False, cert_path: str = "") -> None:
    """
    Persistent TAK Server subscriber. Call from asyncio context.
    Reconnects automatically on any error.
    """
    ssl_ctx = None
    if use_tls:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        if cert_path:
            ssl_ctx.load_cert_chain(cert_path)

    logger.info("TAK subscriber starting → %s:%d (TLS=%s)", host, port, use_tls)

    while True:
        try:
            reader, writer = await asyncio.open_connection(host, port, ssl=ssl_ctx)
            logger.info("TAK Server connected: %s:%d", host, port)
            try:
                await _handle_stream(reader)
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
        except (ConnectionRefusedError, ConnectionResetError, OSError) as exc:
            logger.warning("TAK subscriber disconnected (%s) — retry in %ds", exc, _RECONNECT_DELAY)
        except asyncio.CancelledError:
            logger.info("TAK subscriber cancelled")
            return
        except Exception as exc:
            logger.error("TAK subscriber unexpected error: %s", exc)

        await asyncio.sleep(_RECONNECT_DELAY)
