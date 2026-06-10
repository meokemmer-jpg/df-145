import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# [CRUX-MK]
# `from 145 import ...` is not valid Python syntax, so the test uses importlib to load 145.py.
from importlib import import_module
from datetime import datetime

calculate_sla_report = import_module("145").calculate_sla_report


def test_calculate_sla_report_detects_breaches_and_never_triggers_refund():
    now = datetime(2026, 6, 9, 12, 0, 0)
    incidents = [
        {
            "started_at": "2026-06-08T10:00:00",
            "resolved_at": "2026-06-08T11:00:00",
            "first_response_at": "2026-06-08T10:45:00",
        },
        {
            "started_at": "2026-06-05T09:00:00",
            "resolved_at": "2026-06-05T11:30:00",
            "first_response_at": "2026-06-05T10:30:00",
        },
        {
            "started_at": "2026-05-10T11:00:00",
            "resolved_at": "2026-05-10T13:00:00",
            "first_response_at": "2026-05-10T11:20:00",
        },
        {
            "started_at": "2026-04-01T09:00:00",
            "resolved_at": "2026-04-01T10:00:00",
            "first_response_at": "2026-04-01T09:10:00",
        },
    ]

    report = calculate_sla_report(
        "cust-9dots-001",
        incidents,
        now=now,
        monthly_fee_eur=1000.0,
    )

    assert report["customer_id"] == "cust-9dots-001"
    assert report["incidents_considered"] == 3
    assert report["sla_breaches_30d"] == 2
    assert report["average_response_time_minutes"] == 51.67
    assert report["uptime_percent"] == 99.38
    assert report["sla_credits_owed_eur"] == 125.0
    assert report["auto_refund_triggered"] is False
