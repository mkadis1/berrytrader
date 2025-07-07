import json
import time
from datetime import datetime

import numpy as np
import pandas as pd
from binance.client import Client


def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return json.load(f)


def rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    gain_series = pd.Series(gain, index=series.index)
    loss_series = pd.Series(loss, index=series.index)
    avg_gain = gain_series.rolling(window=period).mean()
    avg_loss = loss_series.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def fetch_prices(client: Client, symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(
        klines,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "num_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
            "ignore",
        ],
    )
    df["close"] = df["close"].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df.set_index("open_time", inplace=True)
    return df


def main() -> None:
    config = load_config('config.json')
    client = Client(config['api_key'], config['api_secret'])
    symbol = config['symbol']
    interval = config['interval']

    profit_target = config['profit_target']
    trailing_stop = config['trailing_stop']
    max_dca_levels = config['max_dca_levels']
    base_investment = config['base_investment']
    dca_drop_trigger = config['dca_drop_trigger']
    rsi_period = config['rsi_period']
    rsi_threshold = config['rsi_threshold']
    fee_rate = config['fee_rate']

    balance = config['initial_balance']
    invested = 0.0
    amount = 0.0
    buy_price = None
    peak_price = 0.0
    dca_level = 0
    buy_amount = base_investment
    trailing = False

    df = fetch_prices(client, symbol, interval, limit=rsi_period + 1)
    df['rsi'] = rsi(df['close'], rsi_period)

    while True:
        new_df = fetch_prices(client, symbol, interval, limit=1)
        df = pd.concat([df, new_df])
        df = df.last('1000T')
        df['rsi'] = rsi(df['close'], rsi_period)

        current_rsi = df['rsi'].iloc[-1]
        price = df['close'].iloc[-1]

        if amount == 0 and current_rsi < rsi_threshold:
            qty = buy_amount / price
            cost = qty * price
            fee = cost * fee_rate
            if balance >= cost + fee:
                try:
                    client.create_order(symbol=symbol, side='BUY', type='MARKET', quantity=qty)
                except Exception:
                    pass
                amount += qty
                invested += cost + fee
                balance -= cost + fee
                buy_price = price
                peak_price = price
                dca_level = 1
                buy_amount *= 2
                trailing = False

        elif amount > 0:
            value = amount * price
            profit = (value - invested) / invested if invested else 0

            if profit >= profit_target:
                if not trailing:
                    trailing = True
                    peak_price = price
                elif price > peak_price:
                    peak_price = price
                elif (peak_price - price) / peak_price >= trailing_stop:
                    revenue = amount * price
                    fee = revenue * fee_rate
                    try:
                        client.create_order(symbol=symbol, side='SELL', type='MARKET', quantity=amount)
                    except Exception:
                        pass
                    balance += revenue - fee
                    invested = 0
                    amount = 0
                    buy_amount = base_investment
                    trailing = False
                    dca_level = 0

            elif price <= buy_price * (1 - dca_drop_trigger) and dca_level < max_dca_levels:
                qty = buy_amount / price
                cost = qty * price
                fee = cost * fee_rate
                if balance >= cost + fee:
                    try:
                        client.create_order(symbol=symbol, side='BUY', type='MARKET', quantity=qty)
                    except Exception:
                        pass
                    amount += qty
                    invested += cost + fee
                    balance -= cost + fee
                    buy_price = price
                    dca_level += 1
                    buy_amount *= 2
            elif dca_level >= max_dca_levels:
                revenue = amount * price
                fee = revenue * fee_rate
                try:
                    client.create_order(symbol=symbol, side='SELL', type='MARKET', quantity=amount)
                except Exception:
                    pass
                balance += revenue - fee
                invested = 0
                amount = 0
                buy_amount = base_investment
                trailing = False
                dca_level = 0

        print(f"{datetime.utcnow()} Price: {price} Balance: {balance} Holding: {amount} RSI: {current_rsi}")
        time.sleep(60)


if __name__ == '__main__':
    main()
