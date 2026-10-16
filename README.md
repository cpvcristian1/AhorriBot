# AhorriBot

A Telegram bot that watches Amazon Spain price drops and sends instant alerts to your phone.

## Description

AhorriBot runs a background loop that polls the CamelCamelCamel top-drops feed for Amazon Spain,
extracts the current price, previous price, drop percentage and ASIN, and notifies you through
Telegram when a matching deal appears. Every alert includes the product's Keepa price-history
graph so you can check whether the price is actually near its historical low before buying.
Already notified products are stored in a local SQLite database so alerts are never repeated.

## Features

- Background scanner that runs on a configurable interval while the bot is online.
- Automatic detection of price drops with per-user thresholds for drop percentage and minimum price.
- Tech-only filter mode: keeps laptops, e-readers, phones, tablets, cameras, audio, monitors,
  components and consoles, and discards cheap accessories such as cases and screen protectors.
- Keepa price-history graph attached to each alert, with a direct link to the product page.
- Inline buttons that open the product on Amazon and the product on Keepa.
- Fallback to a plain text message if the Keepa graph cannot be fetched.
- Anti-spam database: each ASIN is only re-alerted after a cooldown window.
- Per-chat settings stored in SQLite and editable at runtime from Telegram.
- Additional scraper for the Chollometro RSS feed included in the scrapers module.

## Requirements

- Python 3.13
- Dependencies listed in `requirements.txt`:
  - `python-telegram-bot` (Telegram Bot API client, used by `bot.py`)
  - `python-dotenv` (loads `.env` into the environment, used by `config.py`)
- A Telegram bot token, created for free with @BotFather (`/newbot`).
- An internet connection to reach CamelCamelCamel, Keepa and the Telegram API.

## Installation

1. Clone or download this repository and enter the folder.

2. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux / macOS
   source .venv/bin/activate
   ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create the bot with @BotFather: open Telegram, search for @BotFather, send `/newbot`, follow
   the prompts and copy the HTTP API token it returns.

5. Copy the example environment file and fill in your own values:

   ```bash
   # Windows
   copy .env.example .env
   # Linux / macOS
   cp .env.example .env
   ```

   Then edit `.env` and paste your token into `TELEGRAM_BOT_TOKEN`.

6. Start the bot:

   ```bash
   python bot.py
   ```

7. Open Telegram, start a chat with your bot and send `/start`. The first `/start` binds the alert
   destination to that chat, so `TELEGRAM_CHAT_ID` can stay empty in the `.env` file.

## Configuration

All variables are read from `.env` (or the process environment) by `config.py`.

| Variable | Required | Description | Example (fake value) |
| :--- | :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Yes | HTTP API token issued by @BotFather. The bot exits on startup without it. | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `TELEGRAM_CHAT_ID` | No | Numeric chat ID that receives alerts as soon as the bot starts. Auto-detected on `/start` if empty. | `123456789` |
| `MIN_DROP_PERCENT` | No | Minimum price drop percentage to trigger an alert. Default `30.0`. | `40.0` |
| `MIN_PRICE_EUR` | No | Minimum price in EUR. Cheaper items are ignored to skip small accessories. Default `20.0`. | `25.0` |
| `CHECK_INTERVAL_SECONDS` | No | Seconds between background scans. Default `120`. | `300` |

## Usage

```bash
python bot.py
```

The process starts the Telegram polling loop and the background scanner. Press `Ctrl+C` to stop it.
Logs are written to the standard output.

## Commands

| Command | Description |
| :--- | :--- |
| `/start`, `/help` | Welcome message with the active chat ID, current thresholds and the command list. |
| `/test` | Sends a demo alert with a Keepa graph to verify photo delivery and buttons. |
| `/scan` | Forces a scan immediately and reports how many new alerts were sent. |
| `/drop <pct>` | Sets the minimum drop percentage for this chat, e.g. `/drop 40`. |
| `/minprice <eur>` | Sets the minimum price for this chat, e.g. `/minprice 25`. |
| `/mode tech` | Only alert on electronics and gadgets (default). |
| `/mode all` | Disable the tech filter and alert on any large drop. |
| `/status` | Shows the active settings and the number of recorded deals. |

## Database schema

The database file is created next to `bot.py` on first run and is excluded from the repository.
Tables are created by `init_db()` in `database.py`.

- `notified_deals`: products already alerted, to avoid duplicates.
  - `asin` TEXT PRIMARY KEY, `title` TEXT, `new_price` REAL, `old_price` REAL, `drop_pct` REAL,
    `notified_at` INTEGER (Unix timestamp).
- `user_settings`: per-chat thresholds.
  - `chat_id` TEXT PRIMARY KEY, `min_drop_pct` REAL DEFAULT 30.0, `min_price` REAL DEFAULT 20.0.
- `watchlist`: manually followed products.
  - `id` INTEGER PRIMARY KEY AUTOINCREMENT, `chat_id` TEXT, `asin` TEXT, `product_name` TEXT,
    `target_price` REAL, `created_at` INTEGER, with `UNIQUE(chat_id, asin)`.

## Tests

```bash
pip install pytest
pytest
```

The tests in `test_scrapers.py` call the live feeds and the `is_tech_product` classifier, so an
internet connection is required and results depend on the current content of CamelCamelCamel and
Chollometro.

## License

Released under the MIT License. See [LICENSE](LICENSE).
