# flake8: noqa: E501
import streamlit as st
import pandas as pd

from modules.data_loader import get_bybit_exchange
from modules.data_loader import get_tickers


st.set_page_config(page_title="Рост монет", layout="wide")
st.title("Рост Bybit Derivatives")

st.sidebar.markdown("## Настройки отображения")

exchange = get_bybit_exchange()


def show_top_in_table():
    # 1. Берём данные и копируем
    df = get_tickers().copy()
    df = df.sort_values(by='24h_change', ascending=False).reset_index(drop=True)

    # 2. Приводим необходимые столбцы к числовому типу
    df['last_price'] = pd.to_numeric(df['last_price'], errors='coerce')
    df['24h_change'] = pd.to_numeric(df['24h_change'], errors='coerce')
    df['volume_24h_mln_usdt'] = pd.to_numeric(df['volume_24h_mln_usdt'], errors='coerce')
    df['funding_rate'] = pd.to_numeric(df['funding_rate'], errors='coerce')

    # 3. Переименовываем колонки
    df_view = df.rename(columns={
        'symbol': 'Монета',
        'last_price': 'Цена',
        '24h_change': 'Рост 24ч (%)',
        'volume_24h_mln_usdt': 'Объём (млн) USDT',
        'funding_rate': 'Фандинг (%)',
        'next_funding_time': 'Обновление фандинга'
    })

    # 4. Форматируем значения
    df_view['Цена'] = df_view['Цена'].apply(lambda x: f"${x:.4f}")
    df_view['Рост 24ч (%)'] = df_view['Рост 24ч (%)'].apply(lambda x: f"**{x:.2f} %**")
    df_view['Фандинг (%)'] = df_view['Фандинг (%)'].apply(lambda x: f"{x:.4f} %")
    df_view['Обновление фандинга'] = df_view['Обновление фандинга'].apply(lambda t: f"*{t}*")

    df_view['Точки роста'] = df_view['Монета'].apply(
        lambda s: f"[**Entry point**](/Entry_point?symbol={s})"
    )

    df_view[''] = df_view['Монета'].apply(
        lambda s: f"[:orange[**Bybit**]](https://www.bybit.com/trade/usdt/{s})"
    )

    df_view['Монета'] = df_view['Монета'].apply(
        lambda s: f"[**{s}**](/Liquidation_calculator?symbol={s})"
    )

    # 6. Отбираем нужные столбцы в нужном порядке
    display_cols = [
        'Монета', 'Цена', 'Рост 24ч (%)',
        'Объём (млн) USDT', 'Фандинг (%)',
        'Обновление фандинга', 'Точки роста', ''
    ]
    df_display = df_view[display_cols]

    # 7. Выводим таблицу
    st.table(df_display)


def show_top_in_cards():
    df_sorted = get_tickers().sort_values(by="24h_change", ascending=False)
    top_10 = df_sorted.head(10)

    col_sort1, col_sort2 = st.columns([2, 2])
    sort_by = col_sort1.selectbox(
        "Сортировать по:", [
            "24h_change",
            "volume_24h_mln_usdt",
            "funding_rate",
            "last_price"
        ],
        index=0,
        format_func=lambda x: {
            '24h_change': "Рост 24ч",
            'volume_24h_mln_usdt': "Объём USDT",
            'funding_rate': "Фандинг",
            'last_price': "Цена"
        }[x])

    sort_asc = col_sort2.radio("Порядок", options=["↓", "↑"], horizontal=True)
    ascending = sort_asc == "↑"

    df_sorted = get_tickers().sort_values(by=sort_by, ascending=ascending)
    top_10 = df_sorted.head(10)

    st.markdown("---")
    index = 1
    for i, row in top_10.iterrows():
        with st.container():
            col0, col1, col2, col3, col4, col5 = st.columns([1, 3, 2, 2, 2, 3])
            symbol_link = f"https://www.bybit.com/trade/usdt/{row['symbol']}"
            col0.markdown(f"### {index}.")
            col1.markdown(f"### [{row['symbol']}]({symbol_link})")
            col2.metric("Цена", f"${row['last_price']:.4f}")
            col3.metric("Рост 24ч.", f"{row['24h_change']}%")
            col4.metric("Объём (млн USDT)", f"{row['volume_24h_mln_usdt']}")
            col5.metric(f"Фандинг. Обновление: `{row['next_funding_time']}`", f"{row['funding_rate']}%")

            # with st.expander(f"Показать график {row['symbol']}"):
            #     tf_key = f"timeframe_{row['symbol']}"
            #     if tf_key not in st.session_state:
            #         st.session_state[tf_key] = '15m'

            #     timeframe = st.radio(
            #         "Timeframe",
            #         options=['1m', '15m', '1h', '1d'],
            #         key=tf_key,
            #         horizontal=True
            #     )

            #     try:
            #         df_ohlcv = get_ohlcv_data(
            #             symbol=row['symbol'],
            #             timeframe=timeframe,
            #             limit=156,
            #         )
            #         fig = build_chart(
            #             df_ohlcv.copy(),
            #             sma_period,
            #             volume_multiplier
            #         )
            #         st.plotly_chart(fig, use_container_width=True)

            #     except Exception as e:
            #         st.error(f"❌ Не удалось загрузить график: {e}")

        st.markdown("---")
        index += 1

    with st.expander("Показать все монеты"):
        st.dataframe(df_sorted.reset_index(drop=True))


display_mode = st.sidebar.selectbox(
    "Отобразить как:",
    options=["Таблица", "Карточки"],
    index=0,
    key="display_mode"
)

if display_mode == "Карточки":
    show_top_in_cards()
else:
    show_top_in_table()
