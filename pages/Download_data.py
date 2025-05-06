import ccxt
import pandas as pd
import time
from datetime import datetime, timedelta
import streamlit as st


def fetch_ohlcv_to_file(
    symbol: str,
    timeframe: str,
    start_time: datetime,
    end_time: datetime,
    save_path: str = "ohlcv_data.csv",
    limit: int = 1000,
    show_progress: bool = True
) -> pd.DataFrame:
    """
    Parameters
    ----------
    symbol : str
        Market symbol, e.g., 'BTC/USDT'.
    timeframe : str
        Timeframe (e.g., '1m', '1h', '1d').
    start_time : datetime
        Start of the time range.
    end_time : datetime
        End of the time range.
    save_path : str
        Where to save the .csv file.
    limit : int
        Max records per request (default=1000).
    show_progress : bool
        If True, show progress in Streamlit.

    Returns
    -------
    pd.DataFrame
        The combined OHLCV data.
    """
    exchange = ccxt.bybit()
    since = int(start_time.timestamp() * 1000)
    end_ts = int(end_time.timestamp() * 1000)

    all_data = []
    total_requests = 0
    total_minutes = (end_ts - since) // 60000
    total_batches = (total_minutes // limit) + 1

    if show_progress:
        progress_bar = st.progress(0)
        log_area = st.empty()

    print(f"\nStart fetching {symbol} {timeframe} candles...")
    print(f"From: {start_time} To: {end_time}\n")

    while since < end_ts:
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        except Exception as e:
            msg = f"[ERROR] {e}. Retrying in 5 seconds..."
            print(msg)
            if show_progress:
                log_area.warning(msg)
            time.sleep(5)
            continue

        if not candles:
            break

        all_data.extend(candles)
        total_requests += 1

        batch_start = datetime.fromtimestamp(candles[0][0] / 1000)
        batch_end = datetime.fromtimestamp(candles[-1][0] / 1000)
        msg = f"[{total_requests:03}] {len(candles)} rows | {batch_start} → {batch_end}"
        print(msg)
        if show_progress:
            log_area.text(msg)
            progress_bar.progress(min(total_requests / total_batches, 1.0))

        since = candles[-1][0] + 1
        time.sleep(exchange.rateLimit / 1000.0)

    if not all_data:
        msg = "⚠️ No data was fetched."
        print(msg)
        if show_progress:
            st.warning(msg)
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    df.to_csv(save_path, index=False)

    summary = f"✅ Done. {len(df)} rows saved to: {save_path}"
    print(summary)
    print(f"Start: {df['timestamp'].iloc[0]}, End: {df['timestamp'].iloc[-1]}")

    if show_progress:
        progress_bar.progress(1.0)
        st.success(summary)
        st.write(f"📅 Start: {df['timestamp'].iloc[0]} — End: {df['timestamp'].iloc[-1]}")

    return df


try:
    symbol = st.text_input("Символ торговой пары", st.query_params['symbol'])
except KeyError:
    symbol = st.text_input("Символ торговой пары", "BTCUSDT")


timeframe = '1m'
days = st.number_input('За сколько дней скачать данные?', min_value=1, value=365, step=1)

start = datetime.now() - timedelta(days=days)
end = datetime.now()

if st.button("Start Download"):
    fetch_ohlcv_to_file(
        symbol=symbol,
        timeframe=timeframe,
        start_time=start,
        end_time=end,
        save_path=f"datasets/{symbol.replace('/', '')}.csv",
        show_progress=True
    )
