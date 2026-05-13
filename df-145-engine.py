"""DF-145 engine for 9dots-SLA-Compliance Customer-SLA-Breach-Detection."""

import re
import os
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, timezone

DF_DIR = Path(__file__).parent
LOCK_DIR = Path("/tmp/df-145.lock")
DF_ID = "145"
DECISION_KEYWORDS_REGEX = re.compile(
    r"\b(entscheid[a-z]*|empfehl(?:e|en|t|st)|sollt(?:e|en|est)|recommend[a-z]*|decid[a-z]*|advis[a-z]*|propos[a-z]*)\b",
    re.IGNORECASE,
)


@dataclass
class TrackerOutput:
    welle: str = "25"
    df: str = "DF-145"
    iso_timestamp: str = ""
    source: str = "mock"
    sla_breaches_30d: int = 0
    customers_at_breach_risk: list = field(default_factory=list)
    average_response_time_minutes: float = 0
    uptime_pct: float = 0
    sla_credits_owed_eur: float = 0


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_stable(path, min_age_sec=300) -> bool:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False
    try:
        stat = p.stat()
    except OSError:
        return False
    return (time.time() - stat.st_mtime) >= min_age_sec


def acquire_lock_with_identity() -> bool:
    stale_after_sec = 6 * 60 * 60
    now = time.time()

    if LOCK_DIR.exists():
        try:
            age = now - LOCK_DIR.stat().st_mtime
            if age > stale_after_sec:
                for child in LOCK_DIR.iterdir():
                    child.unlink()
                LOCK_DIR.rmdir()
        except OSError:
            pass

    try:
        LOCK_DIR.mkdir(mode=0o700)
    except FileExistsError:
        return False
    except OSError:
        return False

    identity = {
        "df_id": DF_ID,
        "pid": os.getpid(),
        "created_at": iso_now(),
        "cwd": str(Path.cwd()),
    }
    try:
        (LOCK_DIR / "identity.json").write_text(
            json.dumps(identity, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        release_lock()
        return False

    return True


def release_lock() -> None:
    if not LOCK_DIR.exists():
        return
    try:
        identity_path = LOCK_DIR / "identity.json"
        if identity_path.exists():
            data = json.loads(identity_path.read_text(encoding="utf-8"))
            if data.get("pid") != os.getpid() or data.get("df_id") != DF_ID:
                return
        for child in LOCK_DIR.iterdir():
            child.unlink()
        LOCK_DIR.rmdir()
    except OSError:
        return


def k17_pre_action_verification(anchors) -> dict:
    env_tag = "real_api_enabled=true" if _is_real_api_enabled() else "real_api_enabled=false"
    missing_anchors = []

    for anchor in anchors or []:
        if isinstance(anchor, (str, os.PathLike)):
            anchor_path = Path(anchor)
            if not anchor_path.exists():
                missing_anchors.append(str(anchor))
        elif not anchor:
            missing_anchors.append(str(anchor))

    return {
        "ok": len(missing_anchors) == 0,
        "missing_anchors": missing_anchors,
        "env_tag": env_tag,
    }


def _is_real_api_enabled() -> bool:
    value = os.getenv("DF_145_REAL_API_ENABLED", "false").strip().lower()
    return value in {"1", "true", "yes", "y", "on"}


def scan_output_for_decision_keywords(text) -> list:
    if text is None:
        return []
    return sorted({match.group(0) for match in DECISION_KEYWORDS_REGEX.finditer(str(text))})


def assert_no_decision_keywords(output) -> None:
    hits = scan_output_for_decision_keywords(output)
    if hits:
        raise ValueError("Q_0/K_0 violation: decision keywords detected: " + ", ".join(hits))


def collect_tracker_output() -> TrackerOutput:
    source = "mock"
    if _is_real_api_enabled():
        source = "mock"

    return TrackerOutput(
        iso_timestamp=iso_now(),
        source=source,
        sla_breaches_30d=0,
        customers_at_breach_risk=[],
        average_response_time_minutes=0.0,
        uptime_pct=100.0,
        sla_credits_owed_eur=0.0,
    )


def main() -> int:
    if not acquire_lock_with_identity():
        return 3

    try:
        anchors = [DF_DIR]
        pav = k17_pre_action_verification(anchors)
        if not pav.get("ok"):
            return 3

        tracker = collect_tracker_output()
        report = {
            "df-145": asdict(tracker),
            "k17_pre_action_verification": pav,
        }
        output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        assert_no_decision_keywords(output)

        reports_dir = DF_DIR / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        date_tag = datetime.now(timezone.utc).date().isoformat()
        report_path = reports_dir / f"df-145-{date_tag}.json"
        report_path.write_text(output + "\n", encoding="utf-8")

        return 0
    except Exception as exc:
        error_report = {
            "df-145": {
                "welle": "25",
                "df": "DF-145",
                "iso_timestamp": iso_now(),
                "source": "mock",
                "error": exc.__class__.__name__,
            }
        }
        try:
            assert_no_decision_keywords(json.dumps(error_report, ensure_ascii=False))
        except ValueError:
            pass
        return 3
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())