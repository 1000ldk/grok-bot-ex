from __future__ import annotations

from dataclasses import dataclass

from grok_bot.config import Rule, SymbolConfig
from grok_bot.fetch import Quote


@dataclass(frozen=True)
class Evaluation:
    rule: Rule
    rule_key: str
    triggered: bool
    summary: str


def evaluate_symbol(quote: Quote, symbol: SymbolConfig) -> list[Evaluation]:
    return [evaluate_rule(quote, symbol.ticker, rule) for rule in symbol.rules]


def evaluate_rule(quote: Quote, ticker: str, rule: Rule) -> Evaluation:
    key = rule.rule_key(ticker)
    if rule.type == "price":
        return _evaluate_price(quote, rule, key)
    return _evaluate_abs_change_pct(quote, rule, key)


def _evaluate_price(quote: Quote, rule: Rule, key: str) -> Evaluation:
    op_label = "上回った" if rule.op == "above" else "下回った"
    compare = quote.price > rule.value if rule.op == "above" else quote.price < rule.value
    summary = (
        f"価格 {quote.price:,.2f} が閾値 {rule.value:,.2f} を{op_label}"
        if compare
        else f"価格 {quote.price:,.2f} は {rule.op} {rule.value:,.2f} 未達"
    )
    return Evaluation(rule=rule, rule_key=key, triggered=compare, summary=summary)


def _evaluate_abs_change_pct(quote: Quote, rule: Rule, key: str) -> Evaluation:
    change = quote.change_pct
    if change is None:
        return Evaluation(
            rule=rule,
            rule_key=key,
            triggered=False,
            summary="前日終値がないため前日比％を判定できません",
        )

    triggered = abs(change) >= rule.value
    summary = (
        f"前日比 {change:+.2f}% の絶対値が閾値 {rule.value:.2f}% 以上"
        if triggered
        else f"前日比 {change:+.2f}%（閾値 ±{rule.value:.2f}% 未達）"
    )
    return Evaluation(rule=rule, rule_key=key, triggered=triggered, summary=summary)
