# berrytrader

Simple trading bot designed for running on Raspberry Pi. The bot uses the
Binance API and executes a dollar cost averaging strategy with optional
trailing stops. Configuration values are provided via `config.json` so that
strategy parameters can be tweaked without modifying code.

## Requirements

- Python 3.8+
- [`python-binance`](https://github.com/sammchardy/python-binance)
- `pandas` and `numpy`

Install dependencies using:

```bash
pip install python-binance pandas numpy
```

## Usage

1. Copy `config.json` and fill in your Binance API credentials and desired
   strategy parameters.
2. Run the bot:

```bash
python bot.py
```

The script will fetch price data periodically and place market orders based on
the configured RSI threshold, DCA levels and trailing stop settings.
