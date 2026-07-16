"""Tests for Excel backup/sync."""

from datetime import date, datetime
from pathlib import Path

from core import HourAdjustment, Session, Settings
from excel_sync import (
    export_full_backup,
    export_to_excel,
    import_from_excel,
    should_sync_today,
    sync_to_excel_if_needed,
)
from storage import dump_state, load_payload, save_data


def test_should_sync_today() -> None:
    assert should_sync_today(None, date(2026, 6, 17)) is True
    assert should_sync_today("2026-06-17", date(2026, 6, 17)) is False
    assert should_sync_today("2026-06-16", date(2026, 6, 17)) is True


def test_excel_roundtrip(tmp_path: Path, monkeypatch) -> None:
    import excel_sync

    monkeypatch.setattr(excel_sync, "DATA_DIR", tmp_path)
    monkeypatch.setattr(excel_sync, "EXCEL_FILE", tmp_path / "work_hours_backup.xlsx")
    monkeypatch.setattr("storage.DATA_DIR", tmp_path)
    monkeypatch.setattr("storage.DATA_FILE", tmp_path / "work_sessions.json")

    settings = Settings()
    sessions = [
        Session("s1", datetime(2026, 6, 17, 9, 0), datetime(2026, 6, 17, 11, 0)),
        Session("s2", datetime(2026, 6, 17, 14, 0), datetime(2026, 6, 17, 16, 0)),
    ]
    adjustments = [
        HourAdjustment(
            id="a1",
            at=datetime(2026, 6, 17, 20, 0),
            hours_delta=0.5,
            reason="مهمة عاجلة",
            created_at=datetime(2026, 6, 17, 20, 5),
            hour_type="overtime",
        )
    ]
    save_data(dump_state(settings, sessions, None, adjustments=adjustments))

    export_to_excel(settings, sessions, None, adjustments=adjustments)
    restored_settings, restored_sessions, restored_adjustments, active_id = import_from_excel()

    assert restored_settings == settings
    assert len(restored_sessions) == 2
    assert restored_sessions[0].id == "s1"
    assert len(restored_adjustments) == 1
    assert restored_adjustments[0].hours_delta == 0.5
    assert restored_adjustments[0].reason == "مهمة عاجلة"
    assert restored_adjustments[0].hour_type == "overtime"
    assert active_id is None


def test_full_export_writes_custom_path(tmp_path: Path, monkeypatch) -> None:
    import excel_sync

    monkeypatch.setattr(excel_sync, "DATA_DIR", tmp_path)
    monkeypatch.setattr(excel_sync, "EXCEL_FILE", tmp_path / "work_hours_backup.xlsx")
    monkeypatch.setattr("storage.DATA_DIR", tmp_path)
    monkeypatch.setattr("storage.DATA_FILE", tmp_path / "work_sessions.json")

    settings = Settings()
    sessions = [
        Session("s1", datetime(2026, 6, 17, 9, 0), datetime(2026, 6, 17, 11, 0)),
    ]
    json_file = tmp_path / "work_sessions.json"
    save_data(dump_state(settings, sessions, None, adjustments=[]))

    destination = tmp_path / "exports" / "full_backup.xlsx"
    excel_path, json_copy = export_full_backup(
        settings,
        sessions,
        None,
        destination,
        adjustments=[],
        json_source=json_file,
    )

    assert excel_path.exists()
    assert json_copy is not None
    assert json_copy.exists()
    assert excel_path != excel_sync.EXCEL_FILE


def test_daily_sync_runs_once(tmp_path: Path, monkeypatch) -> None:
    import excel_sync

    monkeypatch.setattr(excel_sync, "DATA_DIR", tmp_path)
    monkeypatch.setattr(excel_sync, "EXCEL_FILE", tmp_path / "work_hours_backup.xlsx")
    monkeypatch.setattr("storage.DATA_DIR", tmp_path)
    monkeypatch.setattr("storage.DATA_FILE", tmp_path / "work_sessions.json")

    settings = Settings()
    sessions: list[Session] = []
    save_data(dump_state(settings, sessions, None, adjustments=[]))

    first = sync_to_excel_if_needed(settings, sessions, None, today=date(2026, 6, 17))
    second = sync_to_excel_if_needed(settings, sessions, None, today=date(2026, 6, 17))

    assert first is not None
    assert second is None
    assert load_payload()["last_excel_sync_date"] == "2026-06-17"
