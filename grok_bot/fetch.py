from __future__ import annotations

from dataclasses import dataclass

import yfinance as yf


class FetchError(RuntimeError):
    """公開データソースからの価格取得に失敗。"""


@dataclass(frozen=True)
class Quote:
    ticker: str
    price: float
    previous_close: float | None

    @property
    def change_pct(self) -> float | None:
        if self.previous_close is None or self.previous_close == 0:
            return None
        return ((self.price - self.previous_close) / self.previous_close) * 100


def fetch_quote(ticker: str) -> Quote:
    """yfinance の無料公開データから直近価格と前日終値を取得する。"""
    try:
        ticker_obj = yf.Ticker(ticker)
        price, previous_close = _from_fast_info(ticker_obj)
        if price is None:
            price, previous_close = _from_history(ticker_obj)
    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(f"{ticker}: 価格取得に失敗しました: {exc}") from exc

    if price is None:
        raise FetchError(f"{ticker}: 価格を取得できませんでした（休場・ティッカー誤りの可能性）。")

    return Quote(ticker=ticker, price=price, previous_close=previous_close)


def _from_fast_info(ticker_obj: yf.Ticker) -> tuple[float | None, float | None]:
    try:
        info = ticker_obj.fast_info
        price = _pick(info, "last_price", "lastPrice", "regular_market_price", "regularMarketPrice")
        previous = _pick(info, "previous_close", "previousClose", "regular_market_previous_close")
    except Exception:
        return None, None
    return _as_float(price), _as_float(previous)


def _from_history(ticker_obj: yf.Ticker) -> tuple[float | None, float | None]:
    try:
        history = ticker_obj.history(period="5d", auto_adjust=False)
    except Exception as exc:
        raise FetchError(f"履歴の取得に失敗しました: {exc}") from exc

    if history is None or history.empty or "Close" not in history.columns:
        return None, None

    closes = [float(value) for value in history["Close"].dropna().tolist()]
    if not closes:
        return None, None

    price = closes[-1]
    previous = closes[-2] if len(closes) >= 2 else None
    return price, previous


def _pick(obj: object, *names: str) -> object:
    for name in names:
        if isinstance(obj, dict):
            value = obj.get(name)
        else:
            value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return number
