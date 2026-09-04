from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime

from grok_bot.config import SymbolConfig
from grok_bot.fetch import Quote
from grok_bot.rules import Evaluation


def format_status(symbol: SymbolConfig, quote: Quote, evaluations: list[Evaluation]) -> str:
    change = "前日比 n/a" if quote.change_pct is None else f"前日比 {quote.change_pct:+.2f}%"
    lines = [
        f"{symbol.ticker}  {symbol.label}  {quote.price:,.2f}  {change}",
    ]
    for evaluation in evaluations:
        mark = "HIT" if evaluation.triggered else "---"
        lines.append(f"  [{mark}] {evaluation.summary}")
    return "\n".join(lines)


def format_alert(symbol: SymbolConfig, quote: Quote, evaluation: Evaluation, now: datetime) -> str:
    change = "n/a" if quote.change_pct is None else f"{quote.change_pct:+.2f}%"
    return (
        f"【アラート】{symbol.label} ({symbol.ticker})\n"
        f"{evaluation.summary}\n"
        f"現在値: {quote.price:,.2f} / 前日比: {change}\n"
        f"時刻: {now.isoformat(timespec='seconds')}\n"
        "※監視通知のみ。注文・投資助言ではありません。"
    )


def emit_stdout(text: str) -> None:
    print(text, flush=True)


def post_webhook(url: str, text: str, timeout: float = 10.0) -> None:
    """汎用 JSON POST。Discord は content、Slack 系は text を参照する。"""
    payload = json.dumps({"content": text, "text": text}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Webhook 送信に失敗しました: {exc}") from exc
