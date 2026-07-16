"""Business logic for work session tracking and salary calculation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable


@dataclass(frozen=True)
class Settings:
    month_start_day: int = 17
    standard_daily_hours: float = 4.0
    standard_hourly_rate: float = 10.0
    overtime_hourly_rate: float = 35.0

    def validate(self) -> None:
        if not 1 <= self.month_start_day <= 28:
            raise ValueError("month_start_day must be between 1 and 28")
        if self.standard_daily_hours <= 0:
            raise ValueError("standard_daily_hours must be positive")
        if self.standard_hourly_rate < 0 or self.overtime_hourly_rate < 0:
            raise ValueError("hourly rates cannot be negative")


@dataclass(frozen=True)
class Session:
    id: str
    start: datetime
    end: datetime | None = None

    def duration_seconds(self, *, now: datetime | None = None) -> float:
        end_time = self.end if self.end is not None else (now or datetime.now())
        return max(0.0, (end_time - self.start).total_seconds())


@dataclass(frozen=True)
class HourAdjustment:
    """Manual add (+) or deduct (-) hours for a specific date with a reason and hour type."""

    id: str
    at: datetime
    hours_delta: float
    reason: str
    created_at: datetime
    hour_type: str = "standard"  # "standard" | "overtime"

    def validate(self) -> None:
        if self.hours_delta == 0:
            raise ValueError("hours_delta must not be zero")
        if not self.reason.strip():
            raise ValueError("reason is required")
        if self.hour_type not in {"standard", "overtime"}:
            raise ValueError("hour_type must be 'standard' or 'overtime'")

    @property
    def hour_type_label(self) -> str:
        return "عادية" if self.hour_type == "standard" else "إضافية"


@dataclass(frozen=True)
class SessionBreakdown:
    session: Session
    total_hours: float
    standard_hours: float
    overtime_hours: float


@dataclass(frozen=True)
class DaySummary:
    day: date
    total_hours: float
    standard_hours: float
    overtime_hours: float
    earnings: float
    session_count: int
    adjustment_hours: float = 0.0


@dataclass(frozen=True)
class PeriodSummary:
    label: str
    start: date
    end: date
    total_hours: float
    standard_hours: float
    overtime_hours: float
    earnings: float
    days: tuple[DaySummary, ...]


def period_bounds_for_date(d: date, month_start_day: int) -> tuple[date, date, str]:
    """Return (start, end, label) for the payroll period containing `d`."""
    if d.day >= month_start_day:
        period_start = date(d.year, d.month, month_start_day)
        if d.month == 12:
            next_period_start = date(d.year + 1, 1, month_start_day)
        else:
            next_period_start = date(d.year, d.month + 1, month_start_day)
    else:
        if d.month == 1:
            period_start = date(d.year - 1, 12, month_start_day)
        else:
            period_start = date(d.year, d.month - 1, month_start_day)
        next_period_start = date(d.year, d.month, month_start_day)

    period_end = next_period_start - timedelta(days=1)
    label = f"{period_start.year}-{period_start.month:02d}"
    return period_start, period_end, label


def session_day(session: Session, *, now: datetime | None = None) -> date:
    return session.start.date()


def sessions_for_day(sessions: Iterable[Session], day: date, *, now: datetime | None = None) -> list[Session]:
    return [s for s in sessions if session_day(s, now=now) == day]


def adjustments_for_day(adjustments: Iterable[HourAdjustment], day: date) -> list[HourAdjustment]:
    return [a for a in adjustments if a.at.date() == day]


def day_hours(sessions: Iterable[Session], day: date, *, now: datetime | None = None) -> float:
    total_seconds = sum(s.duration_seconds(now=now) for s in sessions_for_day(sessions, day, now=now))
    return total_seconds / 3600.0


def day_adjustment_hours(adjustments: Iterable[HourAdjustment], day: date) -> float:
    return sum(a.hours_delta for a in adjustments_for_day(adjustments, day))


def split_standard_overtime(total_hours: float, settings: Settings) -> tuple[float, float]:
    capped = max(0.0, total_hours)
    standard_hours = min(capped, settings.standard_daily_hours)
    overtime_hours = max(0.0, capped - settings.standard_daily_hours)
    return standard_hours, overtime_hours


def allocate_session_breakdown(
    sessions: Iterable[Session],
    settings: Settings,
    *,
    now: datetime | None = None,
) -> list[SessionBreakdown]:
    """Assign standard/OT hours to sessions in chronological order within a day."""
    ordered = sorted(sessions, key=lambda s: s.start)
    remaining_standard = settings.standard_daily_hours
    rows: list[SessionBreakdown] = []
    for session in ordered:
        total_hours = session.duration_seconds(now=now) / 3600.0
        standard_hours = min(total_hours, remaining_standard)
        overtime_hours = max(0.0, total_hours - standard_hours)
        remaining_standard = max(0.0, remaining_standard - standard_hours)
        rows.append(
            SessionBreakdown(
                session=session,
                total_hours=total_hours,
                standard_hours=standard_hours,
                overtime_hours=overtime_hours,
            )
        )
    return rows


def calculate_day_summary(
    day: date,
    sessions: Iterable[Session],
    settings: Settings,
    *,
    now: datetime | None = None,
    adjustments: Iterable[HourAdjustment] | None = None,
) -> DaySummary:
    day_sessions = sessions_for_day(sessions, day, now=now)
    session_hours = day_hours(sessions, day, now=now)
    day_adjs = adjustments_for_day(adjustments or (), day)
    adj_hours = sum(a.hours_delta for a in day_adjs)

    # Split tracked session hours first, then apply typed manual adjustments.
    standard_hours, overtime_hours = split_standard_overtime(session_hours, settings)
    for adj in day_adjs:
        if adj.hour_type == "overtime":
            overtime_hours += adj.hours_delta
        else:
            standard_hours += adj.hours_delta

    standard_hours = max(0.0, standard_hours)
    overtime_hours = max(0.0, overtime_hours)
    total_hours = standard_hours + overtime_hours
    earnings = (
        standard_hours * settings.standard_hourly_rate
        + overtime_hours * settings.overtime_hourly_rate
    )
    return DaySummary(
        day=day,
        total_hours=total_hours,
        standard_hours=standard_hours,
        overtime_hours=overtime_hours,
        earnings=earnings,
        session_count=len(day_sessions),
        adjustment_hours=adj_hours,
    )


def calculate_period_summary(
    sessions: Iterable[Session],
    settings: Settings,
    reference: date | None = None,
    *,
    now: datetime | None = None,
    adjustments: Iterable[HourAdjustment] | None = None,
) -> PeriodSummary:
    ref = reference or date.today()
    period_start, period_end, label = period_bounds_for_date(ref, settings.month_start_day)
    adj_list = list(adjustments or ())

    days: list[DaySummary] = []
    current = period_start
    while current <= period_end:
        summary = calculate_day_summary(
            current, sessions, settings, now=now, adjustments=adj_list
        )
        if summary.total_hours > 0 or summary.adjustment_hours != 0 or summary.session_count > 0:
            days.append(summary)
        current += timedelta(days=1)

    total_hours = sum(d.total_hours for d in days)
    standard_hours = sum(d.standard_hours for d in days)
    overtime_hours = sum(d.overtime_hours for d in days)
    earnings = sum(d.earnings for d in days)

    return PeriodSummary(
        label=label,
        start=period_start,
        end=period_end,
        total_hours=total_hours,
        standard_hours=standard_hours,
        overtime_hours=overtime_hours,
        earnings=earnings,
        days=tuple(days),
    )


def format_hours(hours: float) -> str:
    sign = "-" if hours < 0 else ""
    total_minutes = int(round(abs(hours) * 60))
    h, m = divmod(total_minutes, 60)
    return f"{sign}{h}:{m:02d}"
