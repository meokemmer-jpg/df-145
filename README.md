# DF-145 9dots-SLA-Compliance [CRUX-MK]

**Status:** SKELETON-CONDITIONAL (Welle-51 W51-B Skeleton-Wave-1)
**Domain:** K_0 (9dots Revenue/Customer-Retention)
**Welle:** 25

## Mission

Customer-SLA-Breach-Detection fuer 9dots-Kunden. Tracking:
- SLA-Breaches in 30 Tagen
- Average-Response-Time (Minuten)
- Uptime-Prozent
- SLA-Credits-Owed (EUR)

**NIEMALS Auto-Refund-Ausloesung.**

## Activation-Trigger

- Manuell: `python df-145-engine.py`
- Real-API: `DF_145_REAL_API_ENABLED=true` + Phronesis-Ticket

## Usage

```bash
cd ~/Projects/dark-factories/df-145
python df-145-engine.py        # Mock-Mode default
pytest tests/                   # Existing tests
```

## Output

- Reports: `reports/df-145-{date}.json`
- STOP-Flag: `/tmp/df-145.stop`

[CRUX-MK]
