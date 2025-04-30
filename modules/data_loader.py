
# flake8: noqa: E501
import ccxt
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import httpx
import asyncio
from ccxt.async_support import bybit as AsyncBybit


_PERIOD_DELTAS = {
    "1d": timedelta(days=1),
    "1h": timedelta(hours=1),
    "15m": timedelta(minutes=15),
    "5m": timedelta(minutes=5),
    "1m": timedelta(minutes=1),
}


def get_bybit_exchange():
    try:
        exchange = ccxt.bybit({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })

    except Exception as e:
        st.error(f"Ошибка при подключении к Bybit: {e}")
        exchange = None

    return exchange


def get_bybit_async():
    try:
        exchange = AsyncBybit({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })

    except Exception as e:
        st.error(f"Ошибка при подключении к Bybit async: {e}")
        exchange = None

    return exchange


@st.cache_data(ttl=60)
def get_ticker(symbol: str):
    """
    Возвращает всю информацию по менете.
    """
    try:
        exchange = get_bybit_exchange()
        ticker = exchange.fetch_ticker(symbol=symbol)
        return ticker

    except Exception as e:
        st.sidebar.warning(f"Не удалось получить цену {symbol}: {e}")
        return 0


@st.cache_data(ttl=180)
def fetch_ohlcv(symbol: str, timeframe: str, limit: int = 156):
    try:
        exchange = get_bybit_exchange()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        st.error(f"Не удалось получить данные fetch_ohlcv {symbol}: {e}")
        return None


async def fetch_ohlcv_async(exchange, symbol: str, timeframe: str, limit: int = 156):
    try:
        data = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return timeframe, df
    except Exception as e:
        st.error(f"Не удалось получить данные fetch_ohlcv_async {symbol}: {e}")
        return None


async def get_ohlcv(symbol: str, timeframes: list):
    exchange = get_bybit_async()
    tasks = [fetch_ohlcv_async(exchange, symbol, tf) for tf in timeframes]
    results = await asyncio.gather(*tasks)
    await exchange.close()
    return dict(results)


@st.cache_data(ttl=60)
def get_tickers():
    """
    Получает тикеры через ccxt.fetch_tickers() и преобразует в DataFrame.
    Фильтрует только фьючерсные контракты на USDT.
    https://bybit-exchange.github.io/docs/v5/market/tickers
    https://api.bybit.com/v5/market/tickers?category=linear
    """
    exchange = get_bybit_exchange()
    tickers = exchange.fetch_tickers()

    data = []
    for symbol, ticker in tickers.items():
        symbol = ticker['info']['symbol']
        last_price = float(ticker['info']['lastPrice'])
        change_pct = float(ticker['info']['price24hPcnt']) * 100
        high = float(ticker['info']['highPrice24h'])
        low = float(ticker['info']['lowPrice24h'])
        volume = float(ticker['info']['turnover24h']) / 1e6
        funding_rate = ticker['info']['fundingRate']
        next_funding_time = (
            datetime
            .fromtimestamp(int(ticker['info']['nextFundingTime']) / 1000)
            .strftime('%Y-%m-%d %H:%M')
        )

        data.append({
            'symbol': symbol,
            'last_price': last_price,
            '24h_change': round(change_pct, 2),
            '24h_high': high,
            '24h_low': low,
            'volume_24h_mln_usdt': round(volume, 2),
            'funding_rate': funding_rate,
            'next_funding_time': next_funding_time
        })

    return pd.DataFrame(data)






















async def fetch_long_short_ratio(
    symbol: str,
    period: str,
    limit: int = 156,
) -> tuple[str, pd.DataFrame]:
    """
    Запрашивает историю Long/Short Ratio для заданного symbol и period
    через Bybit REST API v5 и возвращает кортеж (period, DataFrame).
    """
    url = "https://api.bybit.com/v5/market/account-ratio"
    params = {
        "category": "linear",
        "symbol": symbol,
        "period": period,
        "limit": limit,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        js = resp.json()

    data = js.get("result", {}).get("list", [])
    if not data:
        # если список пуст — возвращаем пустой фрейм нужной формы
        empty = pd.DataFrame(columns=["timestamp", "ratio"])
        return period, empty

    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
    df["ratio"] = df["sellRatio"].astype(float)
    return period, df[["timestamp", "ratio"]]


async def get_long_short_ratio(
    symbol: str,
    periods: list[str],
    limit: int = 156,
) -> dict[str, pd.DataFrame]:
    """
    Запрашивает историю Long/Short Ratio для всех периодов из api_periods,
    а затем возвращает словарь с ключами ['1d','1h','15m','5m','1m']:
      - '15m' ← данные по '15min'
      - '5m'  ← данные по '5min'
      - '1m'  ← копия '5m', если нет своих данных
      - '1h','1d' как есть
    """
    tasks = [
        fetch_long_short_ratio(symbol, period, limit)
        for period in periods
    ]
    results = await asyncio.gather(*tasks)

    raw = {period: df for period, df in results}
    final = {}
    for p in periods:
        # переводим '15min'->'15m', '5min'->'5m', остальные — без изменений
        if p.endswith("min"):
            key = p.replace("min", "m")
        else:
            key = p
        final[key] = raw.get(p, pd.DataFrame(columns=["timestamp", "ratio"]))

    # если для '1m' фрейма нет данных или он пустой, копируем '5m'
    if not final.get("1m") or final["1m"].empty:
        df5 = final.get("5m", pd.DataFrame(columns=["timestamp", "ratio"])).copy()

        if not df5.empty:
            df5 = df5.set_index("timestamp").sort_index()
            df1 = df5.resample("1min").ffill().reset_index()
        else:
            df1 = pd.DataFrame(columns=["timestamp", "ratio"])
        final["1m"] = df1.tail(limit).reset_index(drop=True)

    return final















async def fetch_open_interest(
    category: str,
    symbol: str,
    period: str,
    limit: int,
) -> tuple[str, pd.DataFrame]:
    """
    Запрашивает историю Open Interest для заданного symbol и period
    через Bybit REST API v5 и возвращает кортеж (period, DataFrame).
    """
    url = "https://api.bybit.com/v5/market/open-interest"
    params = {
        "category": category,
        "symbol": symbol,
        "intervalTime": period,
        "limit": limit,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        js = resp.json()

    data = js.get("result", {}).get("list", [])
    if not data:
        empty = pd.DataFrame(columns=["timestamp", "openInterest"])
        return period, empty

    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
    df["openInterest"] = df["openInterest"].astype(float)
    return period, df[["timestamp", "openInterest"]]


async def get_open_interest(
    symbol: str,
    periods: list[str],
    limit: int = 156,
) -> dict[str, pd.DataFrame]:
    """
    Для каждого периода из periods (5min,15min,1h,1d и т.п.)
    загружает данные и возвращает их в словаре с ключами
    '5m','15m','1h','1d','1m' (последний заполняется по 5m).
    """
    tasks = [
        fetch_open_interest("linear", symbol, p, limit)
        for p in periods
    ]
    results = await asyncio.gather(*tasks)

    raw = {p: df for p, df in results}
    final = {}
    for p in periods:
        if p.endswith("min"):
            key = p.replace("min", "m")
        else:
            key = p
        final[key] = raw.get(p, pd.DataFrame(columns=["timestamp", "openInterest"]))

    if "1m" not in final or final["1m"].empty:
        df5 = final.get("5m", pd.DataFrame(columns=["timestamp", "openInterest"]))
        if not df5.empty:
            df5 = df5.set_index("timestamp").sort_index()
            df1 = df5.resample("1min").ffill().reset_index()
        else:
            df1 = pd.DataFrame(columns=["timestamp", "openInterest"])
        final["1m"] = df1.tail(limit).reset_index(drop=True)

    return final















# --- Funding Rate History ---

def fetch_funding_history(
    category: str,
    symbol: str,
    start_time: int,
    end_time: int,
    limit: int,
) -> list:
    """
    HTTP Request
    ------------
    GET /v5/market/funding/history

    Request Parameters
    ------------------
    category       Required  string   Product type. linear / inverse
    symbol         Required  string   Symbol name, e.g. "BTCUSDT", uppercase!
    startTime      Required  integer  Start timestamp in milliseconds (ms)
    endTime        Required  integer  End   timestamp in milliseconds (ms)
    limit          Optional  integer  Number of records [1..200], default=200

    Response Parameters
    -------------------
    result.list: list of objects, each containing:
      - symbol                  string  Symbol name
      - fundingRate             string  Funding rate (e.g. "-0.00005711")
      - fundingRateTimestamp    string  Funding rate timestamp in ms

    Returns
    -------
    list[dict[str, Any]]
        A list of funding rate records.
    """

    url = "https://api.bybit.com/v5/market/funding/history"
    params = {
        "category": category,
        "symbol": symbol,
        "limit": limit,
        "start_time": start_time,
        "end_time": end_time,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("result", {}).get("list", [])
    except httpx.HTTPError as exc:
        print(f"HTTP error while fetching funding history {response}: {exc}")
        return []


def get_funding_history(
    symbol: str,
    timeframes: list[str],
    limit: int = 156,
) -> dict[str, pd.DataFrame]:
    """
    Funding Rate History Processor
    ------------------------------
    Queries funding rate history from Bybit and constructs resampled time series 
    for use as indicators over candle chart timeframes.

    Data Source
    -----------
    Endpoint: GET /v5/market/funding/history

    Request Parameters (to fetch_funding_history)
    ---------------------------------------------
    category       Required  string   Product type. "linear" or "inverse"
    symbol         Required  string   Symbol name, e.g. "BTCUSDT", uppercase!
    start_time     Required  integer  Start timestamp in milliseconds (ms)
    end_time       Required  integer  End   timestamp in milliseconds (ms)
    limit          Optional  integer  Max number of records per request, default=200

    Response Format
    ---------------
    result.list: list of objects, each containing:
      - symbol                  string   Symbol name
      - fundingRate             string   Funding rate (e.g. "-0.00005711")
      - fundingRateTimestamp    string   UTC timestamp in milliseconds

    Parameters
    ----------
    symbol : str
        Trading pair symbol (e.g. "BTCUSDT")
    timeframes : list of str
        List of timeframes to generate DataFrames for (e.g. ["1m", "1h", "1d"])
    limit : int, optional
        Number of rows in the output DataFrame per timeframe. Default is 156.

    Returns
    -------
    dict[str, pd.DataFrame]
        Dictionary where keys are timeframes and values are DataFrames:
          - For "1d" timeframe: raw funding points as-is.
          - For others (e.g. "1h", "15m"): forward-filled funding values aligned to uniform grid.
        
        Each DataFrame contains:
          - timestamp     datetime64[ns]
          - fundingRate   float (unmodified)
    """
    now = pd.Timestamp.utcnow()
    start_time = now - timedelta(days=limit)
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(now.timestamp() * 1000)

    raw = fetch_funding_history(
        category="linear",
        symbol=symbol,
        start_time=start_ms,
        end_time=end_ms,
        limit=200,
    )

    df = pd.DataFrame(raw)
    if df.empty:
        return {tf: pd.DataFrame(columns=["timestamp", "fundingRate"]) for tf in timeframes}

    df["timestamp"] = pd.to_datetime(df["fundingRateTimestamp"].astype("int64"), unit="ms")
    df["fundingRate"] = pd.to_numeric(df["fundingRate"], errors="coerce")
    df = df[["timestamp", "fundingRate"]].drop_duplicates("timestamp").sort_values("timestamp")
    df.set_index("timestamp", inplace=True)

    last_timestamp = df.index.max()
    last_value = df.iloc[-1]["fundingRate"]
    now_floor = pd.Timestamp.utcnow().replace(tzinfo=None).floor("1min")

    if last_timestamp < now_floor:
        df.loc[now_floor] = last_value
        df = df.sort_index()

    FREQ_MAP = {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "1h": "1h",
        "1d": "1d",
    }

    indicators = {}
    for tf in timeframes:
        if tf == "1d":
            df_out = df.reset_index().copy()
        else:
            # if tf.endswith("min"):
            #     tf = tf.replace("min", "m")

            freq = FREQ_MAP[tf]

            period_delta = pd.to_timedelta(freq)
            end_time = df.index.max()
            start_time = end_time - limit * period_delta

            index = pd.date_range(start=start_time, periods=limit, freq=freq)
            df_out = df.reindex(index, method="ffill").reset_index()
            df_out.columns = ["timestamp", "fundingRate"]

        indicators[tf] = df_out

    return indicators
