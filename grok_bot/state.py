from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass
class AlertRecord:
    active: bool
    last_fired: datetime | None = None


class AlertState:
    """条件の継続中に同じアラートを連打しないためのローカル状態。"""

    def __init__(self, path: Path, cooldown: timedelta) -> None:
        self.path = path
        self.cooldown = cooldown
        self._records: dict[str, AlertRecord] = {}

    @classmethod
    def load(cls, path: Path, cooldown_seconds: int) -> AlertState:
        state = cls(path, timedelta(seconds=cooldown_seconds))
        if not path.is_file():
            return state

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return state

        alerts = raw.get("alerts", raw) if isinstance(raw, dict) else {}
        if not isinstance(alerts, dict):
            return state

        for key, value in alerts.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                continue
            last_fired = _parse_dt(value.get("last_fired"))
            state._records[key] = AlertRecord(
                active=bool(value.get("active", False)),
                last_fired=last_fired,
            )
        return state

    def should_notify(self, rule_key: str, now: datetime, triggered: bool) -> bool:
        if not triggered:
            return False

        record = self._records.get(rule_key)
        if record is None or not record.active:
            return True
        if record.last_fired is None:
            return True
        return now - record.last_fired >= self.cooldown

    def apply(self, rule_key: str, now: datetime, triggered: bool, notified: bool) -> None:
        record = self._records.get(rule_key, AlertRecord(active=False))
        if not triggered:
            record.active = False
        else:
            record.active = True
            if notified:
                record.last_fired = now
        self._records[rule_key] = record

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "alerts": {
                key: {
                    "active": record.active,
                    "last_fired": record.last_fired.isoformat() if record.last_fired else None,
                }
                for key, record in self._records.items()
            }
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_dt(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
