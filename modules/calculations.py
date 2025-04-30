from typing import Literal, Union
from decimal import Decimal
import re


RISK_LEVELS = [
    {"limit": 100_000, "mmr": 0.02, "reduction": 0},
    {"limit": 200_000, "mmr": 0.025, "reduction": 500},
    {"limit": 300_000, "mmr": 0.03, "reduction": 1500},
    {"limit": 400_000, "mmr": 0.035, "reduction": 3000},
    {"limit": 500_000, "mmr": 0.04, "reduction": 5000}
]


def get_maintenance_margin(position_value: float) -> tuple[float, float]:
    for level in RISK_LEVELS:
        if position_value <= level["limit"]:
            return level["mmr"], level["reduction"]
    return RISK_LEVELS[-1]["mmr"], RISK_LEVELS[-1]["reduction"]


def calculate_liquidation(
    entry_price: float,
    leverage: int,
    position_type: Literal["Long", "Short"],
    initial_deposit: float,
    support_investment: float
) -> float:

    pos_value = initial_deposit * leverage
    total_margin = initial_deposit + support_investment

    mmr, mm_reduction = get_maintenance_margin(pos_value)
    main_margin = pos_value * mmr - mm_reduction

    if position_type == "Long":
        liquidation_price = entry_price * (1 - (total_margin - main_margin) / pos_value)

    if position_type == "Short":
        liquidation_price = entry_price * (1 + (total_margin - main_margin) / pos_value)
    
    liquidation_dist = abs((liquidation_price - entry_price) / entry_price * 100)
    return liquidation_price, liquidation_dist

def count_decimal_places(x: Union[str, float, int]) -> int:
    """
    Возвращает количество значащих цифр после десятичной точки у X,
    но не менее 2.
    """
    s = x if isinstance(x, str) else format(x, 'f')
    decimals = s.partition('.')[2].rstrip('0')
    return max(len(decimals), 2)


def count_price_step(x) -> float:
    """
    Возвращает минимальный шаг цены для числа x,
    то есть 10^(-количество знаков после точки).
    """
    decimals = count_decimal_places(x)
    step = Decimal('1').scaleb(-decimals)
    return float(step)


def normalize_symbol(symbol: str, quote: str = "USDT") -> str:
    cleaned = re.sub(r'[^A-Za-z0-9]', '', symbol)
    cleaned = cleaned.upper()
    if cleaned.endswith(quote):
        return cleaned
    return f"{cleaned}{quote}"
