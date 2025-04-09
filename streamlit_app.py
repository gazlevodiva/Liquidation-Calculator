import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import ccxt

RISK_LEVELS = [
    {"limit": 100_000, "mmr": 0.02, "reduction": 0},
    {"limit": 200_000, "mmr": 0.025, "reduction": 500},
    {"limit": 300_000, "mmr": 0.03, "reduction": 1500},
    {"limit": 400_000, "mmr": 0.035, "reduction": 3000},
    {"limit": 500_000, "mmr": 0.04, "reduction": 5000}
]

st.set_page_config(page_title="Калькулятор ликвидации Bybit", layout="wide")
st.title("Калькулятор цены ликвидации Bybit")

try:
    exchange = ccxt.bybit()
except Exception as e:
    st.error(f"Ошибка при подключении к Bybit: {e}")
    exchange = None


def get_current_price(symbol: str):
    try:
        if exchange:
            ticker = exchange.fetch_ticker(symbol.replace("/", "").upper())
            return ticker['last']
        else:
            return 0
    except Exception as e:
        st.sidebar.warning(f"Не удалось получить цену: {e}")
        return 0


def get_maintenance_margin(position_value: float):
    for level in RISK_LEVELS:
        if position_value <= level["limit"]:
            return level["mmr"], level["reduction"]
    return RISK_LEVELS[-1]["mmr"], RISK_LEVELS[-1]["reduction"]


def calculate_liquidation_price(
        entry_price,
        leverage,
        position_type,
        initial_deposit,
        support_investment
    ):
    position_value = initial_deposit * leverage
    total_margin = initial_deposit + support_investment

    mmr, mm_reduction = get_maintenance_margin(position_value)
    maintenance_margin = position_value * mmr - mm_reduction

    if position_type == "Long":
        return entry_price * (1 - (total_margin - maintenance_margin) / position_value)

    if position_type == "Short":
        return entry_price * (1 + (total_margin - maintenance_margin) / position_value)


def get_historical_data(symbol: str, timeframe='15m'):
    candle_limit = 120

    try:
        if exchange:
            markets = exchange.load_markets()
            if symbol not in markets:
                st.error(f"❌ Символ {symbol} не найден на бирже")
                return None, False

            market_symbol = markets[symbol]["symbol"]
            ohlcv = exchange.fetch_ohlcv(market_symbol, timeframe, limit=candle_limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df, True
        else:
            raise Exception("Биржа недоступна")

    except Exception as e:
        st.error(f"❌ Ошибка загрузки данных графика: {e}")
        return None, False


def plot_chart(df, entry_price, liquidation_price, symbol, timeframe):
    fig = go.Figure(data=[go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=symbol
    )])

    for y_val, color, label in [
        (entry_price, "green", "Точка входа"),
        (liquidation_price, "red", "Цена ликвидации")
    ]:
        fig.add_shape(type="line",
                      x0=df['timestamp'].min(),
                      x1=df['timestamp'].max(),
                      y0=y_val,
                      y1=y_val,
                      line=dict(color=color, width=2, dash="dash"))

        fig.add_annotation(x=df['timestamp'].max(),
                           y=y_val,
                           text=label,
                           showarrow=True,
                           arrowhead=1,
                           ax=50,
                           ay=0)

    min_price = min(df['low'].min(), entry_price, liquidation_price)
    max_price = max(df['high'].max(), entry_price, liquidation_price)
    padding = (max_price - min_price) * 0.1 if max_price > min_price else 1

    tf_labels = {
        "5m": "5-минутный",
        "15m": "15-минутный",
        "1h": "Часовой",
        "1d": "Дневной"
    }

    fig.update_layout(
        title=f"{symbol} - {tf_labels.get(timeframe, timeframe)} график",
        xaxis_title="Время",
        yaxis_title="Цена",
        height=600,
        xaxis_rangeslider_visible=False,
        dragmode="zoom",
        hovermode="x unified",
        yaxis=dict(range=[min_price - padding, max_price + padding])
    )

    return fig


# --- Interface ---
with st.sidebar:
    st.header("Параметры позиции")

    symbol = st.text_input("Символ торговой пары", "BTC/USDT")
    current_price = get_current_price(symbol)
    position_type = st.selectbox("Тип позиции", ["Short", "Long"])
    entry_price = st.number_input("Цена входа", min_value=0.0, value=float(current_price))
    initial_deposit = st.number_input("Начальный депозит (USDT)", min_value=1.0, value=100.0)
    leverage = st.number_input("Плечо", min_value=1, max_value=125, value=10)
    support_investment = st.number_input("Инвестиции в удержание позиции (USDT)", min_value=0.0, value=10.0)

if entry_price > 0 and leverage > 0 and initial_deposit > 0:
    with st.spinner('Расчёт...'):
        position_size = initial_deposit * leverage
        liquidation_price = calculate_liquidation_price(
            entry_price,
            leverage,
            position_type,
            initial_deposit,
            support_investment
        )

        perc_diff = abs((liquidation_price - entry_price) / entry_price * 100)

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Текущая цена", f"${current_price:.2f}")
        col2.metric("Инвестиции", f"${(initial_deposit+support_investment):.2f}")
        col3.metric("Размер позиции", f"${position_size:.2f}")
        col4.metric("Расстояние до ликвидации:", f"{perc_diff:.2f}%")
        col5.metric("Цена ликвидации", f"${liquidation_price:.2f}")

        st.subheader("График цены")
        tabs = st.tabs(["1 день", "1 час", "15 минут", "5 минут"])
        timeframes = ["1d", "1h", "15m", "5m"]

        with st.spinner("Загрузка графиков..."):
            for i, tf in enumerate(timeframes):
                with tabs[i]:
                    df, real = get_historical_data(symbol, tf)
                    if df is not None and not df.empty:
                        fig = plot_chart(df, entry_price, liquidation_price, symbol, tf)
                        st.plotly_chart(fig, use_container_width=True)
                        st.success("Данные реальные" if real else "Симуляция")
                    else:
                        st.warning("Нет данных для отображения.")


with st.expander("Информация о расчёте"):
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
    - `Support Investment` — дополнительные инвестиции в удержание позиции
    - `Total Margin` = `Initial Deposit + Support Investment`
    - `Position Value` = `Initial Deposit × Leverage`
    - `Maintenance Margin` = рассчитывается по уровням риска:

    #### Примеры уровней ставки поддержи ETH/USDT:
    | Уровень | Лимит позиции (USDT) | Ставка поддержки | Снижение |
    |--------|----------------------|------------------|----------|
    | 1      | 0–100 000            | 2%               | 0        |
    | 2      | 100 001–200 000      | 2.5%             | 500      |
    | 3      | 200 001–300 000      | 3%               | 1500     |
    | 4      | 300 001–400 000      | 3.5%             | 3000     |
    | 5      | 400 001–500 000      | 4%               | 5000     |

    🔸 Ликвидация происходит, когда общая маржа становится меньше рассчитанной `Maintenance Margin`.
    """)


if exchange:
    st.sidebar.success("✅ Подключено к Binance")
else:
    st.sidebar.error("❌ Нет подключения к Binance")
