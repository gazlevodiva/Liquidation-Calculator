import os
import pandas as pd
import streamlit as st
from modules.Indicators import Chart, CandlestickIndicator

st.set_page_config(page_title="Точка входа", layout="wide")


def get_available_symbols(dataset_dir="datasets"):
    files = os.listdir(dataset_dir)
    symbols = [
        f.replace(".csv", "") for f in files
        if f.endswith(".csv")
    ]
    return sorted(symbols)


@st.cache_data
def load_data(symbol: str):
    filename = f"{symbol}.csv"
    filepath = os.path.join("datasets", filename)

    if not os.path.exists(filepath):
        st.error(f"Файл {filename} не найден.")
        download_url = f"/Download_data?symbol={symbol}"
        st.markdown(f"👉 [Скачать данные для {symbol}]({download_url})")
        st.stop()

    df = pd.read_csv(filepath, parse_dates=["timestamp"])
    df.sort_values("timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


# available_symbols = get_available_symbols()
# try:
#     symbol = st.sidebar.selectbox("Выберите скачанную монету", [st.query_params['symbol']]+available_symbols)
# except KeyError:
#     symbol = st.sidebar.selectbox("Выберите скачанную монету", available_symbols)


try:
    symbol = st.text_input("Символ торговой пары", st.query_params['symbol'])
except KeyError:
    symbol = st.text_input("Символ торговой пары", "BTCUSDT")

df = load_data(symbol)


st.sidebar.header("Параметры роста цены")
window_size = st.sidebar.number_input(
    "Кол-во свечей SMA | (За сколько минут)", min_value=1, value=1440, step=1,
     help="1 день = 1440 минут, 1 неделя = 10080 минутам, 1 месяц = ~43200 минут"
)
sma_threshold_pct = st.sidebar.number_input(
    "Превышение SMA (%) | (На сколько выросло)", min_value=1, value=30, step=1
)


def find_anomalies(df: pd.DataFrame, window: int = 20, threshold_pct: float = 30) -> list:
    df = df.copy()

    # Вычисляем скользящее среднее по цене закрытия
    df["sma"] = df["close"].rolling(window=window).mean()

    anomalies = []

    # Начинаем с индекса = window (до этого SMA будет NaN)
    for i in range(window, len(df)):
        sma = df.loc[i, "sma"]
        close = df.loc[i, "close"]

        if pd.notna(sma) and close > sma * (1 + threshold_pct / 100):
            anomalies.append(i)

    return anomalies

raw_anomalies = find_anomalies(df, window_size, sma_threshold_pct)
n_candles_context = 100

filtered_anomalies = []
last_used_index = -1

for idx in raw_anomalies:
    if idx > last_used_index + n_candles_context:
        filtered_anomalies.append(idx)
        last_used_index = idx

anomaly_options = [df.loc[i, "timestamp"] for i in filtered_anomalies]

if anomaly_options:
    st.write(f"Найдено точек роста: {len(anomaly_options)}")
    selected_timestamp = st.selectbox("Выберите дату: ", anomaly_options)

    selected_index = df[df["timestamp"] == selected_timestamp].index[0]

    start_idx = max(0, selected_index - n_candles_context)
    end_idx = min(len(df), selected_index + n_candles_context)
    df_window = df.iloc[start_idx:end_idx]

    chart = Chart(df_window)
    chart.add(CandlestickIndicator())
    fig = chart.build()
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Роста по параметрам не найдено. Попробуйте уменьшить порог изменения цены.")
