from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Iterable


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError(f"Unsupported datetime value: {value!r}")


def _minutes_between(start: datetime, end: datetime) -> float:
    return max(0.0, (end - start).total_seconds() / 60.0)


def _overlap_minutes(
    start: datetime,
    end: datetime,
    window_start: datetime,
    window_end: datetime,
) -> float:
    overlap_start = max(start, window_start)
    overlap_end = min(end, window_end)
    if overlap_end <= overlap_start:
        return 0.0
    return _minutes_between(overlap_start, overlap_end)


def calculate_sla_report(
    customer_id: str,
    incidents: Iterable[dict[str, Any]],
    *,
    now: datetime | str | None = None,
    window_days: int = 30,
    sla_response_minutes: float = 60.0,
    sla_uptime_percent: float = 99.9,
    response_breach_credit_eur: float = 25.0,
    monthly_fee_eur: float = 0.0,
    uptime_credit_rate: float = 0.10,
) -> dict[str, Any]:
    if window_days <= 0:
        raise ValueError("window_days must be positive")
    if sla_response_minutes < 0:
        raise ValueError("sla_response_minutes must be non-negative")
    if not 0 <= sla_uptime_percent <= 100:
        raise ValueError("sla_uptime_percent must be between 0 and 100")
    if response_breach_credit_eur < 0 or monthly_fee_eur < 0 or uptime_credit_rate < 0:
        raise ValueError("credit values must be non-negative")

    now_dt = _as_datetime(now) if now is not None else datetime.utcnow()
    window_start = now_dt - timedelta(days=window_days)
    total_window_minutes = window_days * 24 * 60

    incidents_considered = 0
    response_times: list[float] = []
    response_breaches = 0
    downtime_minutes = 0.0

    for incident in incidents:
        if incident.get("customer_id", customer_id) != customer_id:
            continue

        started_at = _as_datetime(incident["started_at"])
        resolved_at = _as_datetime(incident["resolved_at"])
        overlap = _overlap_minutes(started_at, resolved_at, window_start, now_dt)
        if overlap <= 0:
            continue

        incidents_considered += 1
        downtime_minutes += overlap

        first_response_at = incident.get("first_response_at")
        if first_response_at is None:
            response_breaches += 1
            continue

        response_minutes = _minutes_between(started_at, _as_datetime(first_response_at))
        response_times.append(response_minutes)
        if response_minutes > sla_response_minutes:
            response_breaches += 1

    avg_response = round(sum(response_times) / len(response_times), 2) if response_times else 0.0
    uptime_percent_raw = max(
        0.0,
        100.0 * (total_window_minutes - downtime_minutes) / total_window_minutes,
    )
    uptime_breach = uptime_percent_raw < sla_uptime_percent

    credits = response_breaches * response_breach_credit_eur
    if uptime_breach:
        credits += monthly_fee_eur * uptime_credit_rate

    credits = round(credits, 2)

    return {
        "customer_id": customer_id,
        "window_start": window_start.isoformat(),
        "window_end": now_dt.isoformat(),
        "incidents_considered": incidents_considered,
        "sla_breaches_30d": response_breaches + (1 if uptime_breach else 0),
        "average_response_time_minutes": avg_response,
        "uptime_percent": round(uptime_percent_raw, 2),
        "sla_credits_owed_eur": credits,
        "auto_refund_triggered": credits > 0,
    }
