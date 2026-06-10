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
    now_dt = _as_datetime(now) if now is not None else datetime.utcnow()
    window_start = now_dt - timedelta(days=window_days)
    total_window_minutes = window_days * 24 * 60

    relevant_incidents: list[dict[str, Any]] = []
    response_times: list[float] = []
    response_breaches = 0
    downtime_minutes = 0.0

    for incident in incidents:
        started_at = _as_datetime(incident["started_at"])
        resolved_at = _as_datetime(incident["resolved_at"])
        overlap = _overlap_minutes(started_at, resolved_at, window_start, now_dt)
        if overlap <= 0:
            continue

        relevant_incidents.append(incident)
        downtime_minutes += overlap

        first_response_at = incident.get("first_response_at")
        if first_response_at is not None:
            response_minutes = _minutes_between(started_at, _as_datetime(first_response_at))
            response_times.append(response_minutes)
            if response_minutes > sla_response_minutes:
                response_breaches += 1

    avg_response = round(sum(response_times) / len(response_times), 2) if response_times else 0.0
    uptime_percent = round(max(0.0, 100.0 * (total_window_minutes - downtime_minutes) / total_window_minutes), 4)
    uptime_breach = uptime_percent < sla_uptime_percent

    credits = response_breaches * response_breach_credit_eur
    if uptime_breach:
        credits += monthly_fee_eur * uptime_credit_rate

    return {
        "customer_id": customer_id,
        "window_start": window_start.isoformat(),
        "window_end": now_dt.isoformat(),
        "incidents_considered": len(relevant_incidents),
        "sla_breaches_30d": response_breaches + (1 if uptime_breach else 0),
        "average_response_time_minutes": avg_response,
        "uptime_percent": round(uptime_percent, 2),
        "sla_credits_owed_eur": round(credits, 2),
        "auto_refund_triggered": False,
    }
# [CRUX-MK]
