# grok-bot-ex

株・指数の**監視＋アラート**だけの教育用 MVP です。設定した銘柄の公開価格を見て、閾値を超えたら標準出力（と任意で Webhook）に知らせます。

## 重要（必ず読んでください）

- **教育・検証用の監視ツール**です。投資助言ではありません。
- **証券口座連携・注文・自動売買は行いません。** ブローカー API は含まれません。
- 表示する価格は遅延・欠落することがあります。売買判断には使わないでください。

## できること / やらないこと

| する | しない |
| --- | --- |
| YAML の銘柄を監視する | 証券口座に接続する |
| 価格の above / below、前日比の絶対％ | 注文・建玉・自動売買 |
| 1回チェック / 間隔付きループ | Web UI |
| 標準出力と任意 Webhook | 暗号資産特化、本格バックテスト |

## 価格データの制限（yfinance）

価格は [yfinance](https://github.com/ranaroussi/yfinance) 経由の**無料の公開データ**です。

- Yahoo Finance の非公式利用であり、可用性・レート制限・利用規約は Yahoo 側に依存します。
- 指数（`^N225`, `^GSPC` など）は休場中やメンテ中に値が取れない／古いことがあります。
- 高頻度のポーリングは避けてください。`watch` の間隔は数分以上を推奨します。
- 本番の取引システムや SLA 付きフィードの代替にはなりません。

## 必要環境

- Python 3.9 以上
- インターネット（価格取得時のみ。テストはネット不要）

## セットアップ

```bash
git clone https://github.com/1000ldk/grok-bot-ex.git
cd grok-bot-ex

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip

pip install -e .
# 開発時（pytest）:
# pip install -e ".[dev]"

cp config.example.yaml config.yaml
# Webhook を使う場合だけ:
# cp .env.example .env
# そして .env の ALERT_WEBHOOK_URL を編集
```

`config.yaml` と `.env` は git 管理しません。秘密情報をリポジトリに入れないでください。

## 使い方

### 1回チェック

```bash
grok-bot check -c config.yaml
# または
python -m grok_bot check -c config.yaml
```

### 間隔付きループ

```bash
grok-bot watch -c config.yaml
grok-bot watch -c config.yaml --interval 300
```

`Ctrl+C` で停止します。

### アラート経路の確認

`config.yaml` の `above` / `below` を現在値のすぐ近く（わざと低い／高い閾値）にすると、`check` 一発でアラート文面を確認できます。同じ条件は連打しません。

## 設定

`config.example.yaml` をコピーして編集します。

```yaml
interval_seconds: 300      # watch の間隔
cooldown_seconds: 3600     # 条件が真のまま続くときの再通知間隔
state_file: .alert_state.json

symbols:
  - ticker: "^N225"
    name: 日経平均
    rules:
      - type: price
        op: below          # above または below
        value: 60000
      - type: abs_change_pct
        value: 2.0         # 前日比の絶対％
```

ティッカーは yfinance が解釈できる記号です。必要なら追加してください（例: `7203.T`）。

## 通知

- 毎回、標準出力に銘柄ごとの現状を出します。
- 条件を満たし、かつ抑制対象でないとき、アラート文を追加で出します。
- 環境変数 `ALERT_WEBHOOK_URL` があれば JSON を POST します。
  - Discord Incoming Webhook 向けに `content` 文字列を含めます。
  - Slack 互換のため `text` も同じ内容で送ります。

### 連打防止

- 条件が**偽 → 真**になったときに通知します。
- 真のまま続く場合は `cooldown_seconds` が経過するまで再通知しません。
- 状態はローカル JSON（既定: `.alert_state.json`）に保存します。

## テスト

ネット不要です。

```bash
pip install -e ".[dev]"
pytest
```

`rules`（閾値判定）と `dedupe`（連打防止）の最小テストを同梱しています。

## モジュール構成

| モジュール | 役割 |
| --- | --- |
| `grok_bot/config.py` | YAML の読み込みと検証 |
| `grok_bot/fetch.py` | 公開価格の取得 |
| `grok_bot/rules.py` | above / below / 前日比％の判定 |
| `grok_bot/notify.py` | 標準出力と Webhook |
| `grok_bot/state.py` | クールダウン／状態の永続化 |
| `grok_bot/cli.py` | `check` / `watch` |

## ライセンス

教育用のサンプルです。利用は自己責任でお願いします。
