# File: modules/indicators/posicion.py

import streamlit as st

from modules.calculations import (
    calculate_liquidation,
    count_decimal_places,
    count_price_step,
)


def posicion_settings(current_price: float) -> dict:
    """
    Рисует в сайдбаре блок «Параметры позиции»:
      - выбор Long/Short
      - ввод entry_price, initial_deposit, leverage, support_investment
    Считает:
      - position_size
      - liquidation_price и liquidation_perc
      - decimal_places и price_step для форматирования
    Возвращает словарь с этими значениями.
    """
    st.subheader("Параметры позиции")

    # Тип позиции
    position_type = st.selectbox(
        "Тип позиции",
        ["Short", "Long"],
        key="pos_type",
    )

    # Для вывода метрик на графике
    decimal_places = count_decimal_places(current_price)
    price_step = count_price_step(current_price)

    # Точка входа
    entry_price = st.number_input(
        "Цена входа",
        min_value=0.0,
        value=current_price,
        format=f"%.{decimal_places}f",
        step=price_step,
        key="pos_entry_price",
    )

    # Депозит
    initial_deposit = st.number_input(
        "Начальный депозит (USDT)",
        min_value=0.0,
        value=100.0,
        step=1.0,
        key="pos_initial_deposit",
    )

    # Плечо
    leverage = st.number_input(
        "Плечо",
        min_value=1,
        max_value=125,
        value=10,
        step=1,
        key="pos_leverage",
    )

    # Инвестиции для поддержки позиции
    support_investment = st.number_input(
        "Инвестиции в удержание позиции (USDT)",
        min_value=0.0,
        value=10.0,
        step=1.0,
        key="pos_support_investment",
    )

    # Размер позиции и ликвидация
    position_size = initial_deposit * leverage
    liquidation_price, liquidation_perc = calculate_liquidation(
        entry_price,
        leverage,
        position_type,
        initial_deposit,
        support_investment,
    )

    return {
        "position_type": position_type,
        "decimal_places": decimal_places,
        "price_step": price_step,
        "entry_price": entry_price,
        "initial_deposit": initial_deposit,
        "leverage": leverage,
        "support_investment": support_investment,
        "position_size": position_size,
        "liquidation_price": liquidation_price,
        "liquidation_perc": liquidation_perc,
    }


def position_info(current_price: float, position_details):
    with st.spinner("Просчет позиции..."):
        decimal_places = position_details["decimal_places"]

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric(
            "Текущая цена",
            f"${current_price:.{decimal_places}f}"
        )
        col2.metric(
            "Инвестиции",
            f"${(position_details['initial_deposit'] + position_details['support_investment']):.2f}"
        )
        col3.metric(
            "Размер позиции",
            f"${position_details['position_size']:.2f}"
        )
        col4.metric(
            "Расстояние до ликвидации",
            f"{position_details['liquidation_perc']:.2f}%"
        )
        col5.metric(
            "Цена ликвидации",
            f"${position_details['liquidation_price']:.{decimal_places}f}"
        )   