# 📉 Bybit Liquidation Price Calculator

Интерактивный калькулятор цены ликвидации для фьючерсных USDT-контрактов на бирже Bybit, написанный на Streamlit.

## ⚙️ Возможности

- Поддержка лонг/шорт позиций
- Учёт дополнительных инвестиций в удержание позиции
- Динамический расчёт поддерживающей маржи на основе уровней риска
- Автоматический выбор ставки маржи и учёт снижения
- Графики цены по данным с Bybit (таймфреймы: 5m, 15m, 1h, 1d)
- Обновление данных в реальном времени без кнопки "Рассчитать"
- Уведомления при потере соединения с биржей

## 🚀 Установка и запуск локально

### 1. Клонировать репозиторий

```bash
git clone https://github.com/gazlevodiva/bybit-liquidation-calculator.git
cd bybit-liquidation-calculator
```

### 2. Установить зависимости

```bash
pip install -r requirements.txt
```

### 3. Запустить приложение

```bash
streamlit run app.py
```

Приложение откроется в браузере: [http://localhost:8501](http://localhost:8501)

## 🌐 Публикация на Streamlit Cloud

1. Перейдите на [https://streamlit.io/cloud](https://streamlit.io/cloud)
2. Войдите через GitHub и выберите этот репозиторий
3. Убедитесь, что файл `app.py` выбран как основной
4. Нажмите **"Deploy"**

## 🧮 О расчёте ликвидации

Ликвидация рассчитывается с учётом уровня риска, согласно таблице ниже:

| Уровень | Лимит позиции (USDT) | Ставка поддержки | Снижение |
|--------|----------------------|------------------|----------|
| 1      | 0–100 000            | 2%               | 0        |
| 2      | 100 001–200 000      | 2.5%             | 500      |
| 3      | 200 001–300 000      | 3%               | 1500     |
| 4      | 300 001–400 000      | 3.5%             | 3000     |
| 5      | 400 001–500 000      | 4%               | 5000     |

**Формулы:**

Для Long:
```
Ликв. цена = Entry Price × (1 - (Total Margin - Maintenance Margin) / Position Value)
```

Для Short:
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
- `Maintenance Margin` = рассчитывается по таблице выше
