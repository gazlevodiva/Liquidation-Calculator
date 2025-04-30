import streamlit as st
from modules.calculations import count_decimal_places, count_price_step


def stop_loss_settings(
    entry_price: float,
    initial_deposit: float,
    leverage: int,
    position_type: str,
) -> float:
    price_key = "sl_price"
    pct_key = "sl_pct"
    amt_key = "sl_amt"
    position_size = initial_deposit * leverage

    if price_key not in st.session_state:
        default_sl = entry_price * (0.99 if position_type == "Long" else 1.01)
        st.session_state[price_key] = default_sl

    if pct_key not in st.session_state:
        st.session_state[pct_key] = abs(
            entry_price - st.session_state[price_key]
        ) / entry_price * 100

    if amt_key not in st.session_state:
        qty = position_size / entry_price
        st.session_state[amt_key] = min(
            abs(entry_price - st.session_state[price_key]) * qty,
            initial_deposit,
        )

    decimal_places = count_decimal_places(entry_price)
    price_step = count_price_step(entry_price)

    def _clamp_amt(amt: float) -> float:
        # Риск в долларах не выше депозита
        return min(max(amt, 0.0), initial_deposit)

    def _clamp_pct(pct: float) -> float:
        # % риска от 0 до 100
        return min(max(pct, 0.0), 100.0)

    def _from_price():
        p = st.session_state[price_key]
        pct = _clamp_pct(abs(entry_price - p) / entry_price * 100)
        qty = position_size / entry_price
        amt = _clamp_amt(abs(entry_price - p) * qty)

        st.session_state[pct_key] = pct
        st.session_state[amt_key] = amt

    def _from_pct():
        pct = _clamp_pct(st.session_state[pct_key])
        p = (
            entry_price * (1 - pct / 100)
            if position_type == "Long"
            else entry_price * (1 + pct / 100)
        )
        qty = position_size / entry_price
        amt = _clamp_amt(abs(entry_price - p) * qty)

        st.session_state[pct_key] = pct
        st.session_state[price_key] = p
        st.session_state[amt_key] = amt

    def _from_amt():
        amt = _clamp_amt(st.session_state[amt_key])
        qty = position_size / entry_price
        dp = amt / qty
        p = (
            entry_price - dp
            if position_type == "Long"
            else entry_price + dp
        )
        pct = abs(entry_price - p) / entry_price * 100
        pct = _clamp_pct(pct)

        st.session_state[amt_key] = amt
        st.session_state[price_key] = p
        st.session_state[pct_key] = pct

    # --- Рисуем UI ---
    st.subheader("Настройки Stop-Loss")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.number_input(
            "Цена SL",
            min_value=0.0,
            value=st.session_state[price_key],
            step=price_step,
            format=f"%.{decimal_places}f",
            key=price_key,
            on_change=_from_price,
        )
    with col2:
        st.number_input(
            "Риск в %",
            min_value=0.0,
            max_value=100.0,
            value=st.session_state[pct_key],
            step=0.1,
            format="%.2f",
            key=pct_key,
            on_change=_from_pct,
        )
    with col3:
        st.number_input(
            "Риск в $",
            min_value=0.0,
            value=st.session_state[amt_key],
            step=0.01,
            format="%.2f",
            key=amt_key,
            on_change=_from_amt,
        )

    return st.session_state[price_key]
