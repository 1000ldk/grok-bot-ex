from grok_bot.config import Rule
from grok_bot.fetch import Quote
from grok_bot.rules import evaluate_rule


def test_price_above_triggers_when_over_threshold() -> None:
    quote = Quote(ticker="^GSPC", price=5100.0, previous_close=5000.0)
    rule = Rule(type="price", op="above", value=5050.0)
    result = evaluate_rule(quote, "^GSPC", rule)
    assert result.triggered is True
    assert result.rule_key == "^GSPC|price|above|5050.0"


def test_price_below_does_not_trigger_on_equal() -> None:
    quote = Quote(ticker="^N225", price=35000.0, previous_close=34900.0)
    rule = Rule(type="price", op="below", value=35000.0)
    result = evaluate_rule(quote, "^N225", rule)
    assert result.triggered is False


def test_price_below_triggers_when_under_threshold() -> None:
    quote = Quote(ticker="^N225", price=34999.99, previous_close=35000.0)
    rule = Rule(type="price", op="below", value=35000.0)
    result = evaluate_rule(quote, "^N225", rule)
    assert result.triggered is True


def test_abs_change_pct_uses_absolute_value() -> None:
    down = Quote(ticker="^GSPC", price=97.0, previous_close=100.0)
    rule = Rule(type="abs_change_pct", value=2.5)
    assert evaluate_rule(down, "^GSPC", rule).triggered is True

    small = Quote(ticker="^GSPC", price=98.0, previous_close=100.0)
    assert evaluate_rule(small, "^GSPC", rule).triggered is False


def test_abs_change_pct_skips_without_previous_close() -> None:
    quote = Quote(ticker="^N225", price=38000.0, previous_close=None)
    rule = Rule(type="abs_change_pct", value=1.0)
    result = evaluate_rule(quote, "^N225", rule)
    assert result.triggered is False
    assert "前日終値" in result.summary
