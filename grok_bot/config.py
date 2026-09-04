from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

RuleType = Literal["price", "abs_change_pct"]
PriceOp = Literal["above", "below"]


class ConfigError(ValueError):
    """設定ファイルの内容が不正。"""


@dataclass(frozen=True)
class Rule:
    type: RuleType
    op: PriceOp | None = None
    value: float = 0.0

    def rule_key(self, ticker: str) -> str:
        if self.type == "price":
            return f"{ticker}|price|{self.op}|{self.value}"
        return f"{ticker}|abs_change_pct|{self.value}"


@dataclass(frozen=True)
class SymbolConfig:
    ticker: str
    name: str | None
    rules: tuple[Rule, ...]

    @property
    def label(self) -> str:
        return self.name or self.ticker


@dataclass(frozen=True)
class AppConfig:
    symbols: tuple[SymbolConfig, ...]
    interval_seconds: int
    cooldown_seconds: int
    state_file: Path


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigError(
            f"設定ファイルが見つかりません: {config_path}\n"
            "  cp config.example.yaml config.yaml  を実行してください。"
        )

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigError("YAML のルートはマッピングである必要があります。")

    symbols_raw = raw.get("symbols")
    if not isinstance(symbols_raw, list) or not symbols_raw:
        raise ConfigError("symbols に1件以上の銘柄を指定してください。")

    symbols = tuple(_parse_symbol(item, index) for index, item in enumerate(symbols_raw))

    interval = _as_positive_int(raw.get("interval_seconds", 300), "interval_seconds")
    cooldown = _as_positive_int(raw.get("cooldown_seconds", 3600), "cooldown_seconds")
    state_file = Path(str(raw.get("state_file", ".alert_state.json")))
    if not state_file.is_absolute():
        state_file = (config_path.parent / state_file).resolve()

    return AppConfig(
        symbols=symbols,
        interval_seconds=interval,
        cooldown_seconds=cooldown,
        state_file=state_file,
    )


def _parse_symbol(item: object, index: int) -> SymbolConfig:
    if not isinstance(item, dict):
        raise ConfigError(f"symbols[{index}] はマッピングである必要があります。")

    ticker = item.get("ticker")
    if not isinstance(ticker, str) or not ticker.strip():
        raise ConfigError(f"symbols[{index}].ticker が必要です。")

    name = item.get("name")
    if name is not None and not isinstance(name, str):
        raise ConfigError(f"symbols[{index}].name は文字列にしてください。")

    rules_raw = item.get("rules")
    if not isinstance(rules_raw, list) or not rules_raw:
        raise ConfigError(f"symbols[{index}].rules に1件以上のルールを指定してください。")

    rules = tuple(_parse_rule(rule, index, rule_i) for rule_i, rule in enumerate(rules_raw))
    return SymbolConfig(ticker=ticker.strip(), name=name, rules=rules)


def _parse_rule(item: object, symbol_index: int, rule_index: int) -> Rule:
    loc = f"symbols[{symbol_index}].rules[{rule_index}]"
    if not isinstance(item, dict):
        raise ConfigError(f"{loc} はマッピングである必要があります。")

    rule_type = item.get("type")
    if rule_type not in ("price", "abs_change_pct"):
        raise ConfigError(f"{loc}.type は price または abs_change_pct にしてください。")

    value = item.get("value")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ConfigError(f"{loc}.value は数値である必要があります。")

    op: PriceOp | None = None
    if rule_type == "price":
        raw_op = item.get("op")
        if raw_op not in ("above", "below"):
            raise ConfigError(f"{loc}.op は above または below にしてください。")
        op = raw_op

    return Rule(type=rule_type, op=op, value=float(value))


def _as_positive_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{field_name} は正の整数にしてください。")
    number = int(value)
    if number <= 0:
        raise ConfigError(f"{field_name} は正の整数にしてください。")
    return number
