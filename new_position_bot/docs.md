# new_position_bot

Path: @/new_position_bot

### Overview

- Automated trading bot that uses Grok AI to analyze Kalshi prediction markets and place trades
- Fetches newly created markets, enriches them with detailed rules, sends to AI for analysis, and executes recommended trades
- Designed to run as a serverless function on GCP with spending limit controls

### How it fits into the larger codebase

- Entry point for the entire trading system - no other components call into this folder
- Integrates with two external APIs:
  - **Kalshi API** (`kalshi_client.py`) - market data, positions, order execution
  - **xAI Grok API** (`grok_client.py`) - AI-powered trade analysis
- Configuration loaded from environment variables and GCP Secret Manager (`utils.py`)
- Can be triggered via HTTP (Cloud Function) or run directly via `main.py`

### Core Implementation

```
+------------------+     +-------------------+     +----------------+
|  main.py         | --> |  kalshi_client.py | --> |  Kalshi API    |
|  (orchestrator)  |     +-------------------+     +----------------+
|                  |
|                  |     +-------------------+     +----------------+
|                  | --> |  grok_client.py   | --> |  xAI Grok API  |
+------------------+     +-------------------+     +----------------+
```

**Data flow in `run_bot_logic()` (main.py):**

1. Load configuration from environment variables
2. Fetch recent orders to calculate current spending against limit
3. Fetch active markets created within lookback window
4. Filter to viable markets (yes_ask < 100 AND no_ask < 100) not already held
5. For each market:
   - Fetch detailed market info including rules via `get_market(ticker)`
   - Merge basic market data with detailed data (detailed overrides basic)
   - Send enriched market data to `grok.analyze_market()`
   - If Grok recommends a trade, check spending limit and execute via `create_market_order()`

**KalshiClient key methods:**

| Method | Purpose |
|--------|---------|
| `get_market(ticker)` | Fetch detailed market info including `rules_primary`, `rules_secondary`, `yes_sub_title`, `no_sub_title` |
| `get_active_markets()` | List markets created within time window |
| `get_positions()` | Current held positions |
| `get_orders()` | Order history (filtered by bot identifier) |
| `create_market_order()` | Execute a buy order |

**GrokClient prompt construction:**

The `analyze_market()` method builds a prompt containing:
- Basic market info: title, ticker, subtitle, category, yes price
- Market rules section (when present):
  - "Yes means: {yes_sub_title}"
  - "No means: {no_sub_title}"
  - Primary settlement rules
  - Secondary settlement rules
- Expected response format: JSON with `ticker`, `side` (yes/no/null), `explanation`

### Things to Know

- **Market rules enrichment is graceful** - If `get_market()` fails, the bot proceeds with basic market data only (logs a warning)
- **Spending limit tracking** counts both executed fills and committed capital from resting orders
- **Bot identifier prefix** (`NEW_POSITION_BOT` by default) is used to filter orders and tag new orders
- **Authentication uses RSA signing** - Each request is signed with timestamp + method + path using PSS padding
- **Price fields vary by endpoint** - Basic market list returns `yes_ask`/`no_ask`, detailed market returns `yes_sub_title`/`no_sub_title` for semantic meaning
- **The rules section is only added to the prompt when at least one rule field is present** - backwards compatible with markets that have no rules
