from __future__ import annotations

import argparse
import os
import sys
import time
import warnings
from datetime import datetime, timezone

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

from dotenv import load_dotenv

from grok_bot.config import AppConfig, ConfigError, load_config
from grok_bot.fetch import FetchError, fetch_quote
from grok_bot.notify import emit_stdout, format_alert, format_status, post_webhook
from grok_bot.rules import evaluate_symbol
from grok_bot.state import AlertState


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"設定エラー: {exc}", file=sys.stderr)
        return 2

    if args.command == "check":
        return run_once(config)

    interval = args.interval or config.interval_seconds
    return run_watch(config, interval)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grok-bot",
        description="株・指数の監視＋アラート（教育用）。注文・自動売買は行いません。",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="いまの価格を1回だけ確認する")
    check.add_argument("-c", "--config", default="config.yaml", help="設定ファイル（既定: config.yaml）")

    watch = sub.add_parser("watch", help="間隔をおいて繰り返し確認する")
    watch.add_argument("-c", "--config", default="config.yaml", help="設定ファイル（既定: config.yaml）")
    watch.add_argument(
        "-i",
        "--interval",
        type=int,
        default=None,
        help="確認間隔（秒）。未指定なら設定ファイルの interval_seconds",
    )
    return parser


def run_once(config: AppConfig) -> int:
    state = AlertState.load(config.state_file, config.cooldown_seconds)
    webhook_url = os.environ.get("ALERT_WEBHOOK_URL", "").strip() or None
    now = datetime.now(timezone.utc)
    had_error = False

    emit_stdout(f"=== {now.isoformat(timespec='seconds')} ===")

    for symbol in config.symbols:
        try:
            quote = fetch_quote(symbol.ticker)
        except FetchError as exc:
            emit_stdout(f"{symbol.ticker}  取得失敗: {exc}")
            had_error = True
            continue

        evaluations = evaluate_symbol(quote, symbol)
        emit_stdout(format_status(symbol, quote, evaluations))

        for evaluation in evaluations:
            notify = state.should_notify(evaluation.rule_key, now, evaluation.triggered)
            if notify:
                message = format_alert(symbol, quote, evaluation, now)
                emit_stdout(message)
                if webhook_url:
                    try:
                        post_webhook(webhook_url, message)
                    except RuntimeError as exc:
                        emit_stdout(str(exc))
                        had_error = True
            state.apply(evaluation.rule_key, now, evaluation.triggered, notify)

    try:
        state.save()
    except OSError as exc:
        print(f"状態ファイルの保存に失敗しました: {exc}", file=sys.stderr)
        had_error = True

    return 1 if had_error else 0


def run_watch(config: AppConfig, interval: int) -> int:
    if interval <= 0:
        print("interval は正の整数にしてください。", file=sys.stderr)
        return 2

    emit_stdout(f"watch 開始（{interval}秒間隔）。Ctrl+C で停止。注文は行いません。")
    try:
        while True:
            run_once(config)
            time.sleep(interval)
    except KeyboardInterrupt:
        emit_stdout("watch を停止しました。")
        return 0
