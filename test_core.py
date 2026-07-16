"""Tests for salary calculation logic."""

from datetime import date, datetime

from core import (
    HourAdjustment,
    Session,
    Settings,
    allocate_session_breakdown,
    calculate_day_summary,
    calculate_period_summary,
    period_bounds_for_date,
)


def test_period_bounds_default_start_day() -> None:
    start, end, label = period_bounds_for_date(date(2026, 2, 10), 17)
    assert start == date(2026, 1, 17)
    assert end == date(2026, 2, 16)
    assert label == "2026-01"

    start, end, label = period_bounds_for_date(date(2026, 2, 20), 17)
    assert start == date(2026, 2, 17)
    assert end == date(2026, 3, 16)
    assert label == "2026-02"


def test_multiple_sessions_same_day() -> None:
    settings = Settings()
    sessions = [
        Session("1", datetime(2026, 6, 17, 9, 0), datetime(2026, 6, 17, 11, 0)),
        Session("2", datetime(2026, 6, 17, 14, 0), datetime(2026, 6, 17, 17, 30)),
    ]
    summary = calculate_day_summary(date(2026, 6, 17), sessions, settings)
    assert round(summary.total_hours, 2) == 5.5
    assert summary.standard_hours == 4.0
    assert round(summary.overtime_hours, 2) == 1.5
    assert summary.earnings == 4 * 10 + 1.5 * 35


def test_period_summary_totals() -> None:
    settings = Settings()
    sessions = [
        Session("1", datetime(2026, 1, 20, 10, 0), datetime(2026, 1, 20, 14, 0)),
        Session("2", datetime(2026, 2, 1, 9, 0), datetime(2026, 2, 1, 13, 0)),
    ]
    period = calculate_period_summary(sessions, settings, date(2026, 2, 5))
    assert period.start == date(2026, 1, 17)
    assert period.end == date(2026, 2, 16)
    assert period.total_hours == 8.0
    assert period.earnings == 80.0


def test_session_breakdown_assigns_overtime_after_standard() -> None:
    settings = Settings(standard_daily_hours=4.0)
    sessions = [
        Session("1", datetime(2026, 6, 17, 9, 0), datetime(2026, 6, 17, 12, 0)),
        Session("2", datetime(2026, 6, 17, 13, 0), datetime(2026, 6, 17, 16, 0)),
    ]
    rows = allocate_session_breakdown(sessions, settings)
    assert round(rows[0].standard_hours, 2) == 3.0
    assert round(rows[0].overtime_hours, 2) == 0.0
    assert round(rows[1].standard_hours, 2) == 1.0
    assert round(rows[1].overtime_hours, 2) == 2.0


def test_hour_adjustment_adds_to_day_total() -> None:
    settings = Settings()
    sessions = [
        Session("1", datetime(2026, 6, 17, 9, 0), datetime(2026, 6, 17, 11, 0)),
    ]
    adjustments = [
        HourAdjustment(
            id="a1",
            at=datetime(2026, 6, 17, 0, 0),
            hours_delta=1.5,
            reason="عمل إضافي خارج التطبيق",
            created_at=datetime(2026, 6, 17, 18, 5),
            hour_type="standard",
        )
    ]
    summary = calculate_day_summary(
        date(2026, 6, 17), sessions, settings, adjustments=adjustments
    )
    assert round(summary.total_hours, 2) == 3.5
    assert round(summary.adjustment_hours, 2) == 1.5
    assert summary.standard_hours == 3.5
    assert summary.overtime_hours == 0.0


def test_hour_adjustment_deducts_from_day_total() -> None:
    settings = Settings()
    sessions = [
        Session("1", datetime(2026, 6, 17, 9, 0), datetime(2026, 6, 17, 14, 0)),
    ]
    adjustments = [
        HourAdjustment(
            id="a1",
            at=datetime(2026, 6, 17, 0, 0),
            hours_delta=-1.0,
            reason="استراحة غير مسجلة",
            created_at=datetime(2026, 6, 17, 20, 5),
            hour_type="standard",
        )
    ]
    summary = calculate_day_summary(
        date(2026, 6, 17), sessions, settings, adjustments=adjustments
    )
    # 5h session => 4 standard + 1 OT, then -1 standard => 3 standard + 1 OT
    assert round(summary.total_hours, 2) == 4.0
    assert round(summary.standard_hours, 2) == 3.0
    assert round(summary.overtime_hours, 2) == 1.0
    assert round(summary.adjustment_hours, 2) == -1.0


def test_hour_adjustment_overtime_type() -> None:
    settings = Settings()
    sessions = [
        Session("1", datetime(2026, 6, 17, 9, 0), datetime(2026, 6, 17, 11, 0)),
    ]
    adjustments = [
        HourAdjustment(
            id="a1",
            at=datetime(2026, 6, 17, 0, 0),
            hours_delta=2.0,
            reason="أوفرتايم يدوي",
            created_at=datetime(2026, 6, 17, 21, 0),
            hour_type="overtime",
        )
    ]
    summary = calculate_day_summary(
        date(2026, 6, 17), sessions, settings, adjustments=adjustments
    )
    assert round(summary.standard_hours, 2) == 2.0
    assert round(summary.overtime_hours, 2) == 2.0
    assert round(summary.total_hours, 2) == 4.0
    assert summary.earnings == 2 * 10 + 2 * 35
