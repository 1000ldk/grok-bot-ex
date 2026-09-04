from datetime import datetime, timedelta, timezone
from pathlib import Path

from grok_bot.state import AlertState


def _now() -> datetime:
    return datetime(2026, 9, 4, 4, 0, tzinfo=timezone.utc)


def test_notifies_on_first_trigger(tmp_path: Path) -> None:
    state = AlertState.load(tmp_path / "state.json", cooldown_seconds=3600)
    now = _now()
    assert state.should_notify("n225|price|below|35000", now, triggered=True) is True


def test_does_not_repeat_while_still_active_within_cooldown(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state = AlertState.load(path, cooldown_seconds=3600)
    now = _now()
    key = "n225|price|below|35000"

    assert state.should_notify(key, now, triggered=True)
    state.apply(key, now, triggered=True, notified=True)
    state.save()

    again = AlertState.load(path, cooldown_seconds=3600)
    assert again.should_notify(key, now + timedelta(minutes=10), triggered=True) is False


def test_renotifies_after_cooldown_while_still_true(tmp_path: Path) -> None:
    state = AlertState.load(tmp_path / "state.json", cooldown_seconds=60)
    now = _now()
    key = "^GSPC|abs_change_pct|1.5"
    state.apply(key, now, triggered=True, notified=True)

    assert state.should_notify(key, now + timedelta(seconds=59), triggered=True) is False
    assert state.should_notify(key, now + timedelta(seconds=60), triggered=True) is True


def test_renotifies_when_condition_clears_then_hits_again(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state = AlertState.load(path, cooldown_seconds=3600)
    now = _now()
    key = "^N225|price|above|50000"

    state.apply(key, now, triggered=True, notified=True)
    state.apply(key, now + timedelta(minutes=1), triggered=False, notified=False)
    state.save()

    restored = AlertState.load(path, cooldown_seconds=3600)
    assert restored.should_notify(key, now + timedelta(minutes=2), triggered=True) is True


def test_false_condition_never_notifies(tmp_path: Path) -> None:
    state = AlertState.load(tmp_path / "state.json", cooldown_seconds=1)
    assert state.should_notify("x|price|above|1", _now(), triggered=False) is False
