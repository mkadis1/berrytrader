import json
import os
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd


@dataclass
class IndicatorConfig:
    enabled: bool
    for_entry: bool
    for_exit: bool
    params: Dict[str, int] = field(default_factory=dict)


@dataclass
class Config:
    api_key: str
    api_secret: str
    symbols: List[str]
    base_investment: float
    max_dca_levels: int
    take_profit: float
    trailing_stop: float
    dca_drop_trigger: float
    rsi_period: int
    rsi_threshold: int
    base_currency: str
    interval: str
    alligator: IndicatorConfig
    macd: IndicatorConfig

    @staticmethod
    def load(path: str) -> "Config":
        with open(path, "r") as f:
            data = json.load(f)
        alligator = IndicatorConfig(
            enabled=data.get("alligator", {}).get("enabled", False),
            for_entry=data.get("alligator", {}).get("for_entry", False),
            for_exit=data.get("alligator", {}).get("for_exit", False),
            params={
                "jaw_period": data.get("alligator", {}).get("jaw_period", 13),
                "teeth_period": data.get("alligator", {}).get("teeth_period", 8),
                "lips_period": data.get("alligator", {}).get("lips_period", 5),
            },
        )
        macd = IndicatorConfig(
            enabled=data.get("macd", {}).get("enabled", False),
            for_entry=data.get("macd", {}).get("for_entry", False),
            for_exit=data.get("macd", {}).get("for_exit", False),
            params={
                "fast": data.get("macd", {}).get("fast", 12),
                "slow": data.get("macd", {}).get("slow", 26),
                "signal": data.get("macd", {}).get("signal", 9),
            },
        )
        return Config(
            api_key=data.get("api_key"),
            api_secret=data.get("api_secret"),
            symbols=data.get("symbols", []),
            base_investment=data.get("base_investment", 0),
            max_dca_levels=data.get("max_dca_levels", 0),
            take_profit=data.get("take_profit", 0),
            trailing_stop=data.get("trailing_stop", 0),
            dca_drop_trigger=data.get("dca_drop_trigger", 0),
            rsi_period=data.get("rsi_period", 14),
            rsi_threshold=data.get("rsi_threshold", 30),
            base_currency=data.get("base_currency"),
            interval=data.get("interval", "1h"),
            alligator=alligator,
            macd=macd,
        )


def load_trades(path: str) -> Dict[str, dict]:
    if Path(path).exists():
        with open(path, "r") as f:
            return json.load(f)
    return {}


def save_trades(path: str, trades: Dict[str, dict]) -> None:
    with open(path, "w") as f:
        json.dump(trades, f, indent=2)


def compute_rsi(series: pd.Series, period: int) -> float:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]


def main():
    config = Config.load("config.json")
    trades = load_trades("trades.json")
    client = Client(config.api_key, config.api_secret)

    while True:
        for symbol in config.symbols:
            try:
                klines = client.get_klines(symbol=symbol, interval=config.interval, limit=config.rsi_period + 1)
            except BinanceAPIException as exc:
                print(f"Error fetching klines: {exc}")
                continue
            closes = pd.Series([float(k[4]) for k in klines])
            rsi = compute_rsi(closes, config.rsi_period)
            trade = trades.get(symbol)

            if trade is None:
                if rsi < config.rsi_threshold:
                    quantity = round(config.base_investment / float(closes.iloc[-1]), 6)
                    # Place order (commented out for demo)
                    # order = client.order_market_buy(symbol=symbol, quantity=quantity)
                    order = {"price": closes.iloc[-1], "quantity": quantity}
                    print(f"BUY {symbol} at {order['price']} qty {quantity}")
                    trades[symbol] = {
                        "entry_price": order["price"],
                        "quantity": quantity,
                        "dca_level": 0,
                    }
            else:
                current_price = float(closes.iloc[-1])
                entry_price = trade["entry_price"]
                if current_price >= entry_price * (1 + config.take_profit):
                    # client.order_market_sell(symbol=symbol, quantity=trade['quantity'])
                    print(f"TAKE PROFIT {symbol} at {current_price}")
                    del trades[symbol]
                elif (
                    trade["dca_level"] < config.max_dca_levels
                    and current_price <= entry_price * (1 - config.dca_drop_trigger * (trade["dca_level"] + 1))
                ):
                    add_qty = round(config.base_investment / current_price, 6)
                    # client.order_market_buy(symbol=symbol, quantity=add_qty)
                    trade["quantity"] += add_qty
                    trade["entry_price"] = (trade["entry_price"] + current_price) / 2
                    trade["dca_level"] += 1
                    print(f"DCA BUY {symbol} at {current_price} level {trade['dca_level']}")
        save_trades("trades.json", trades)
        time.sleep(60)


if __name__ == "__main__":
    main()
