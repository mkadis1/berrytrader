# berrytrader

A simple trading bot designed for Raspberry Pi 4 using the Binance API.

## Requirements

- Python 3.9+
- `python-binance` library
- `pandas`

Install dependencies:

```bash
pip install python-binance pandas
```

## Configuration

Edit `config.json` to provide your API credentials and strategy settings. The
file contains options for enabling or disabling the Alligator and MACD
indicators and customising their parameters.

## Running

Run the bot detached so it continues running after logout:

```bash
nohup python3 bot.py &
```

To keep the bot running after a reboot, create a systemd service:

```bash
sudo tee /etc/systemd/system/berrytrader.service > /dev/null <<SERVICE
[Unit]
Description=BerryTrader bot
After=network.target

[Service]
WorkingDirectory=/path/to/berrytrader
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl enable berrytrader.service
sudo systemctl start berrytrader.service
```

On start the bot synchronises with your Binance account and rebuilds any
open positions based on balances. It stores its state in `trades.json`
so trades persist across reboots. Trailing stops and optional Alligator or
MACD filters can be enabled in `config.json`.
