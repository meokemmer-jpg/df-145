from datetime import datetime, timedelta
from pathlib import Path
import importlib
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

engine = importlib.import_module("145")


def _incident(started_at, resolved_at, first_response_at, customer_id="cust-145"):
    return {
        "customer_id": customer_id,
        "started_at": started_at.isoformat(),
        "resolved_at": resolved_at.isoformat(),
        "first_response_at": first_response_at.isoformat() if first_response_at else None,
    }


def test_df_145_sla_report_discriminates_adversarial_incidents():
    now = datetime(2026, 7, 9, 12, 0, 0)
    window_days = 30
    monthly_fee = 1000.0
    response_credit = 25.0
    uptime_credit_rate = 0.10
    sla_response_minutes = 60.0
    sla_uptime_percent = 99.9

    healthy_incidents = [
        _incident(
            now - timedelta(days=1, minutes=20),
            now - timedelta(days=1, minutes=10),
            now - timedelta(days=1, minutes=5),
        )
    ]
    adversarial_incidents = [
        _incident(
            now - timedelta(days=1, minutes=120),
            now - timedelta(days=1),
            now - timedelta(days=1, minutes=20),
        )
    ]

    healthy = engine.calculate_sla_report(
        "cust-145",
        healthy_incidents,
        now=now,
        window_days=window_days,
        sla_response_minutes=sla_response_minutes,
        sla_uptime_percent=sla_uptime_percent,
        response_breach_credit_eur=response_credit,
        monthly_fee_eur=monthly_fee,
        uptime_credit_rate=uptime_credit_rate,
    )
    adversarial = engine.calculate_sla_report(
        "cust-145",
        adversarial_incidents,
        now=now,
        window_days=window_days,
        sla_response_minutes=sla_response_minutes,
        sla_uptime_percent=sla_uptime_percent,
        response_breach_credit_eur=response_credit,
        monthly_fee_eur=monthly_fee,
        uptime_credit_rate=uptime_credit_rate,
    )

    healthy_response_minutes = (
        datetime.fromisoformat(healthy_incidents[0]["first_response_at"])
        - datetime.fromisoformat(healthy_incidents[0]["started_at"])
    ).total_seconds() / 60
    adversarial_response_minutes = (
        datetime.fromisoformat(adversarial_incidents[0]["first_response_at"])
        - datetime.fromisoformat(adversarial_incidents[0]["started_at"])
    ).total_seconds() / 60
    adversarial_downtime_minutes = (
        datetime.fromisoformat(adversarial_incidents[0]["resolved_at"])
        - datetime.fromisoformat(adversarial_incidents[0]["started_at"])
    ).total_seconds() / 60
    total_window_minutes = window_days * 24 * 60
    adversarial_uptime = round(
        100.0 * (total_window_minutes - adversarial_downtime_minutes) / total_window_minutes,
        2,
    )
    expected_adversarial_credits = response_credit + (monthly_fee * uptime_credit_rate)

    assert healthy_response_minutes < sla_response_minutes
    assert adversarial_response_minutes > sla_response_minutes
    assert adversarial_uptime < sla_uptime_percent

    assert healthy["sla_breaches_30d"] == 0
    assert healthy["sla_credits_owed_eur"] == 0.0
    assert healthy["auto_refund_triggered"] is False

    assert adversarial["sla_breaches_30d"] == 2
    assert adversarial["average_response_time_minutes"] == adversarial_response_minutes
    assert adversarial["uptime_percent"] == adversarial_uptime
    assert adversarial["sla_credits_owed_eur"] == expected_adversarial_credits
    assert adversarial["auto_refund_triggered"] is True

    discriminating_fields = {
        key
        for key in healthy
        if healthy[key] != adversarial[key]
    }
    assert {
        "sla_breaches_30d",
        "average_response_time_minutes",
        "uptime_percent",
        "sla_credits_owed_eur",
        "auto_refund_triggered",
    }.issubset(discriminating_fields)
