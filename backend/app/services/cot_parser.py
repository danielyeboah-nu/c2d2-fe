"""
CoT (Cursor on Target) XML parser.

Extracts position, callsign, and UID from CoT SA (Situational Awareness) events
broadcast by ATAK devices via TAK Server.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class CotPosition:
    uid:       str
    callsign:  str
    cot_type:  str    # e.g. "a-f-G-U-C" = atom/friendly/ground/unit/combat
    lat:       float
    lon:       float
    hae:       float  # height above ellipsoid (metres)
    is_friendly: bool


def parse_cot(xml_str: str) -> CotPosition | None:
    """
    Parse a raw CoT XML string into a CotPosition.
    Returns None if the message is not a position SA event or is malformed.
    """
    try:
        root = ET.fromstring(xml_str.strip())
    except ET.ParseError:
        return None

    if root.tag != "event":
        return None

    uid      = root.get("uid", "")
    cot_type = root.get("type", "")

    # Only process atom SA events (a-f-* friendly, a-h-* hostile, a-u-* unknown)
    if not cot_type.startswith("a-"):
        return None

    point = root.find("point")
    if point is None:
        return None

    try:
        lat = float(point.get("lat", "0"))
        lon = float(point.get("lon", "0"))
        hae = float(point.get("hae", "0"))
    except ValueError:
        return None

    # Extract callsign from <detail><contact callsign="..."/>
    callsign = uid  # fallback to UID if no callsign
    detail = root.find("detail")
    if detail is not None:
        contact = detail.find("contact")
        if contact is not None:
            callsign = contact.get("callsign", uid)

    return CotPosition(
        uid=uid,
        callsign=callsign,
        cot_type=cot_type,
        lat=lat,
        lon=lon,
        hae=hae,
        is_friendly=cot_type.startswith("a-f-"),
    )


def parse_cot_stream(buffer: str) -> tuple[list[CotPosition], str]:
    """
    Extract all complete CoT events from a TCP stream buffer.
    Returns (list_of_parsed_positions, remaining_buffer).
    """
    events: list[CotPosition] = []

    while True:
        start = buffer.find("<event")
        if start == -1:
            break
        end = buffer.find("</event>", start)
        if end == -1:
            break  # incomplete event — wait for more data
        end += len("</event>")
        xml_str = buffer[start:end]
        buffer  = buffer[end:]

        cot = parse_cot(xml_str)
        if cot:
            events.append(cot)

    return events, buffer
