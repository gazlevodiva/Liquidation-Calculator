# flake8: noqa: E501
import asyncio
import streamlit as st
from modules.data_loader import (
    get_bybit_exchange,
    get_ticker,
    get_ohlcv,
    get_long_short_ratio,
    get_open_interest,
    get_funding_history,
)
from modules.Indicators import *

from modules.calculations import normalize_symbol

from modules.indicators.stop_loss import stop_loss_settings
from modules.indicators.posicion import posicion_settings, position_info


# --- Page configuration ---
st.set_page_config(page_title="Калькулятор ликвидации", layout="wide")
exchange = get_bybit_exchange()

# --- Sidebar ---
with st.sidebar:

    # --- Symbol ---
    st.header("Торговая пара")
    try:    
        symbol = st.text_input("Символ торговой пары", st.query_params['symbol'])
    except KeyError:
        symbol = st.text_input("Символ торговой пары", "BTCUSDT")

    # symbol = normalize_symbol(symbol)
    current_price = get_ticker(symbol)['last']

    # --- Indicators ---
    st.header("Настройка индикаторов")
    indicator_options = [
        "Объём",
        "Позиция",
        "SMA по объёму",
        "Stop-loss",
        "MACD",
        "Long-Short Ratio",
        "Funding Rate",
        "Open-interest",
        # "Аномалии объёма",
    ]
    selected_indicators = st.multiselect(
        "Выберите индикатор", indicator_options, default=[]
    )

    if "Позиция" in selected_indicators:
        stop_loss_allowed = ["Stop-loss"]
    else:
        stop_loss_allowed = []
        # если пользователь до этого как-то умудрился «захолдить» Stop-loss —
        # удалим его, чтобы не было рассинхронов
        if "Stop-loss" in selected_indicators:
            selected_indicators.remove("Stop-loss")
            st.warning("Чтобы настроить Stop-loss, сперва выберите индикатор «Позиция».")


    if "Позиция" in selected_indicators:
        position_details = posicion_settings(current_price)

    if "SMA по объёму" in selected_indicators:
        st.subheader("Настройки SMA")
        sma_period = st.sidebar.slider(
            "Период SMA",
            min_value=5,
            max_value=50,
            value=9,
            step=1
        )

    if "Аномалии объёма" in selected_indicators:
        st.subheader("Настройки аномального объема")
        volume_multiplier = st.sidebar.slider(
            "Множитель объёма",
            min_value=1.0,
            max_value=100.0,
            value=2.0,
            step=0.1
        )

    if "Stop-loss" in selected_indicators:
        params_key = "sl_params"
        current_params = (
            position_details["entry_price"],
            position_details["initial_deposit"],
            position_details["leverage"],
            position_details["position_type"],
        )

        if st.session_state.get(params_key) != current_params:
            for k in ("sl_price", "sl_pct", "sl_amt"):
                if k in st.session_state:
                    del st.session_state[k]
            st.session_state[params_key] = current_params

        stop_loss_price = stop_loss_settings(
            leverage=position_details["leverage"],
            entry_price=position_details["entry_price"],
            position_type=position_details["position_type"],  
            initial_deposit=position_details["initial_deposit"],          
        )
        

# --- Load data and charts ---
st.header(f"{symbol} – ${current_price}")
tabs = st.tabs(["1 день", "1 час", "15 минут", "5 минут", "1 минута"])
timeframes = ["1d", "1h", "15m", "5m", "1m"]
df_ohlcv_async = asyncio.run(get_ohlcv(symbol, timeframes))

if "Позиция" in selected_indicators:
    position_info(current_price=current_price, position_details=position_details)

if "Long-Short Ratio" in selected_indicators:
    df_long_short_ratio_async = asyncio.run(
        get_long_short_ratio(symbol, ["1d", "1h", "15min", "5min"])
    )    

if "Open-interest" in selected_indicators:
    df_open_int_async = asyncio.run(
        get_open_interest(symbol, ["1d", "1h", "15min", "5min"])
    )

# ✅
if "Funding Rate" in selected_indicators:
    funding_dataframe = get_funding_history(symbol, timeframes)


with st.spinner("Загрузка графиков..."):
    for i, (tab, timeframe) in enumerate(zip(tabs, timeframes)):
        with tab:

            df_ohlcv = df_ohlcv_async.get(timeframe)
            if df_ohlcv is None or df_ohlcv.empty:
                st.warning(f"Нет данных для свечтного графика {timeframe}")
                continue

            chart = Chart(df_ohlcv)
            chart.add(CandlestickIndicator())
            chart.add(CurrentPriceIndicator())

            # ✅
            if "Объём" in selected_indicators:
                chart.add(VolumeIndicator())

            # ✅
            if "SMA по объёму" in selected_indicators:
                chart.add(SMAVolumeIndicator(period=sma_period))

            # ✅
            if "Позиция" in selected_indicators:
                chart.add(PositionIndicator(position_details["entry_price"], position_details["liquidation_price"]))

            # ✅
            if "Stop-loss" in selected_indicators and stop_loss_price is not None:
                    chart.add(StopLossIndicator(stop_loss_price))

            # ✅
            if "MACD" in selected_indicators:
                chart.add(MACDIndicator())

            if "Long-Short Ratio" in selected_indicators:
                df_ratio = df_long_short_ratio_async.get(timeframe, pd.DataFrame(columns=["timestamp","ratio"]))
                if df_ratio.empty:
                    st.warning(f"Нет данных для индикатора long-short{timeframes[i]}")
                else:   
                    chart.add(LongShortRatioIndicator(df_ratio))

            if "Open-interest" in selected_indicators:
                df_op_int = df_open_int_async.get(timeframe, pd.DataFrame(columns=["timestamp","openInterest"]))
                if df_op_int.empty:
                    st.warning(f"Нет данных для индикатора open interest {timeframes[i]}")
                else:   
                    chart.add(OpenInterestIndicator(df_op_int))

            # ✅
            if "Funding Rate" in selected_indicators:
                df_fund = funding_dataframe.get(timeframe, pd.DataFrame(columns=["timestamp","fundingRate"]))
                if df_fund.empty:
                    st.warning(f"Нет данных для индикатора funding rate {timeframes[i]}")
                else:   
                    chart.add(FundingRateIndicator(df_fund))

            fig = chart.build()
            st.plotly_chart(fig, use_container_width=True, key=f"{timeframe}_plt")


if "Позиция" in selected_indicators:
    with st.expander("Информация о расчёте ликвидации"):
        st.markdown("""
            ### 📘 Формула расчёта цены ликвидации

            **Для Long-позиций:**
            ```
            Ликв. цена = Entry Price × (1 - (Total Margin - Maintenance Margin) / Position Value)
            ```

            **Для Short-позиций:**
            ```
            Ликв. цена = Entry Price × (1 + (Total Margin - Maintenance Margin) / Position Value)
            ```

            **Где:**
            - `Entry Price` — цена входа  
            - `Leverage` — плечо  
            - `Initial Deposit` — начальный депозит  
            - `Support Investment` — инвестиции в удержание позиции  
            - `Total Margin` = `Initial Deposit + Support Investment`  
            - `Position Value` = `Initial Deposit × Leverage`  
            - `Maintenance Margin` рассчитывается по уровням риска  
        """)
