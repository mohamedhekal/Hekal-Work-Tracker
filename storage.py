"""JSON persistence for sessions and settings."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from core import HourAdjustment, Session, Settings
from paths import get_data_dir


DATA_DIR = get_data_dir()
DATA_FILE = DATA_DIR / "work_sessions.json"


def _default_payload() -> dict:
    return {
        "settings": asdict(Settings()),
        "sessions": [],
        "adjustments": [],
        "active_session_id": None,
        "last_excel_sync_date": None,
    }


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def load_payload() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        payload = _default_payload()
        save_data(payload)
        return payload

    with DATA_FILE.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    payload.setdefault("last_excel_sync_date", None)
    payload.setdefault("adjustments", [])
    return payload


def load_data() -> tuple[Settings, list[Session], list[HourAdjustment], str | None]:
    payload = load_payload()

    settings = Settings(**payload.get("settings", {}))
    settings.validate()

    sessions: list[Session] = []
    for item in payload.get("sessions", []):
        sessions.append(
            Session(
                id=item["id"],
                start=_parse_datetime(item["start"]),
                end=_parse_datetime(item["end"]) if item.get("end") else None,
            )
        )

    adjustments: list[HourAdjustment] = []
    for item in payload.get("adjustments", []):
        adjustments.append(
            HourAdjustment(
                id=item["id"],
                at=_parse_datetime(item["at"]),
                hours_delta=float(item["hours_delta"]),
                reason=str(item.get("reason", "")),
                created_at=_parse_datetime(item["created_at"]),
                hour_type=str(item.get("hour_type", "standard")),
            )
        )

    return settings, sessions, adjustments, payload.get("active_session_id")


def save_data(payload: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def dump_state(
    settings: Settings,
    sessions: list[Session],
    active_session_id: str | None,
    *,
    adjustments: list[HourAdjustment] | None = None,
    last_excel_sync_date: str | None = None,
) -> dict:
    payload = load_payload()
    if adjustments is None:
        adjustments_payload = payload.get("adjustments", [])
    else:
        adjustments_payload = [
            {
                "id": a.id,
                "at": a.at.isoformat(timespec="seconds"),
                "hours_delta": a.hours_delta,
                "reason": a.reason,
                "created_at": a.created_at.isoformat(timespec="seconds"),
                "hour_type": a.hour_type,
            }
            for a in adjustments
        ]
    return {
        "settings": asdict(settings),
        "sessions": [
            {
                "id": s.id,
                "start": s.start.isoformat(timespec="seconds"),
                "end": s.end.isoformat(timespec="seconds") if s.end else None,
            }
            for s in sessions
        ],
        "adjustments": adjustments_payload,
        "active_session_id": active_session_id,
        "last_excel_sync_date": (
            last_excel_sync_date
            if last_excel_sync_date is not None
            else payload.get("last_excel_sync_date")
        ),
    }


def new_session_id() -> str:
    return str(uuid.uuid4())


def new_adjustment_id() -> str:
    return str(uuid.uuid4())
