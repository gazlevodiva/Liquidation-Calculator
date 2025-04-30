from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd


class Indicator:
    requires = []
    target = 'main'
    row_height = None

    def apply(self, fig: go.Figure, df, row: int = 1, col: int = 1):
        """
        Add subplot (row, col).
        """
        raise NotImplementedError("Метод apply() должен быть реализован в подклассе.")


class Chart:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.indicators = []
        self.targets = {"main"}
        self.target_order = ["main"]
        self.row_mapping = {}

    def add(self, indicator):
        self.indicators.append(indicator)

        target = getattr(indicator, "target", "main")
        if target not in self.targets:
            self.targets.add(target)
            self.target_order.append(target)

        return self

    def build(self) -> go.Figure:
        heights_px = []
        for tgt in self.target_order:
            h_list = [ind.row_height for ind in self.indicators
                      if ind.target == tgt and ind.row_height is not None]
            if not h_list:
                raise ValueError(f"Индикаторы '{tgt}' должны задать row_height")
            heights_px.append(max(h_list))

        total_height = sum(heights_px)
        row_heights = [h / total_height for h in heights_px]

        fig = make_subplots(
            rows=len(self.target_order),
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.01,
            row_heights=row_heights,
        )

        fig.update_layout(
            height=total_height,
            xaxis_rangeslider_visible=False,
            margin=dict(t=40, b=40),
            showlegend=True,
        )

        self.row_mapping = {
            target: i+1 for i, target in enumerate(self.target_order)
        }
        for ind in self.indicators:
            target = getattr(ind, "target", "main")
            row = self.row_mapping.get(target, 1)
            ind.apply(fig, self.df, row=row, col=1)

        fig.update_layout(
            height=total_height,
            xaxis_rangeslider_visible=False,
            margin=dict(t=40, b=40),
            showlegend=True,
            hovermode="x unified",
        )

        for axis_name in fig.layout:
            if axis_name.startswith("xaxis"):
                fig.layout[axis_name].update(
                    showspikes=True,
                    spikemode="across",
                    spikesnap="cursor",
                    spikethickness=1,
                    spikedash="dot",
                    spikecolor="gray",
                )
            if axis_name.startswith("yaxis"):
                fig.layout[axis_name].update(
                    showspikes=True,
                    spikemode="across",
                    spikesnap="cursor",
                    spikethickness=1,
                    spikedash="dot",
                    spikecolor="gray",
                )

        return fig


class CandlestickIndicator(Indicator):
    target = 'main'
    row_height = 800

    def apply(self, fig: go.Figure, df, row: int, col: int = 1):
        fig.add_trace(
            go.Candlestick(
                x=df['timestamp'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                increasing_line_color='green',
                decreasing_line_color='red',
                name='ohlcv',
            ),
            row=row,
            col=col
        )


class PositionIndicator(Indicator):
    target = 'main'

    def __init__(
        self,
        entry_price: float,
        liquidation_price: float,
        entry_color: str = "green",
        liq_color: str = "red",
        entry_label: str = "Точка входа",
        liq_label: str = "Цена ликвидации"
    ):
        self.entry_price = entry_price
        self.liquidation_price = liquidation_price
        self.entry_color = entry_color
        self.liq_color = liq_color
        self.entry_label = entry_label
        self.liq_label = liq_label

    def apply(self, fig: go.Figure, df, row: int, col: int = 1):
        t0 = df['timestamp'].iat[0]
        t1 = df['timestamp'].iat[-1]

        for y_val, color, label in [
            (self.entry_price, self.entry_color, self.entry_label),
            (self.liquidation_price, self.liq_color, self.liq_label),
        ]:
            fig.add_shape(
                type="line",
                x0=t0, x1=t1,
                y0=y_val, y1=y_val,
                line=dict(color=color, width=2, dash="dash"),
                row=row, col=col
            )
            fig.add_annotation(
                x=t1,
                y=y_val,
                text=label,
                showarrow=True,
                arrowhead=2,
                ax=50,
                ay=0,
                font=dict(color=color, size=14),
                align="left"
            )


class StopLossIndicator(Indicator):
    target = 'main'

    def __init__(
        self,
        price: float,
        color: str = "grey",
        label: str = "Стоп-лосс",
    ):
        self.price = price
        self.color = color
        self.label = label

    def apply(self, fig: go.Figure, df, row: int, col: int = 1):
        t0 = df["timestamp"].iat[0]
        t1 = df["timestamp"].iat[-1]
        # линия
        fig.add_shape(
            type="line",
            x0=t0, x1=t1,
            y0=self.price, y1=self.price,
            line=dict(color=self.color, width=2, dash="dot"),
            row=row, col=col,
        )
        # подпись
        fig.add_annotation(
            x=t1,
            y=self.price,
            text=self.label,
            showarrow=True,
            arrowhead=2,
            ax=50,
            ay=0,
            font=dict(color=self.color, size=14),
            align="left",
        )


class CurrentPriceIndicator(Indicator):
    target = 'main'

    def __init__(self, color: str = 'red', dash: str = 'dash', width: int = 1, text_size: int = 14):
        self.color = color
        self.dash = dash
        self.width = width
        self.text_size = text_size

    def apply(self, fig: go.Figure, df, row: int, col: int = 1):
        current_price = df['close'].iat[-1]
        t0, t1 = df['timestamp'].iat[0], df['timestamp'].iat[-1]
        fig.add_shape(
            type='line',
            x0=t0,
            x1=t1,
            y0=current_price,
            y1=current_price,
            line=dict(color=self.color, dash=self.dash, width=self.width),
            row=row,
            col=col
        )
        fig.add_trace(
            go.Scatter(
                x=[t0],
                y=[current_price],
                text=[f"{current_price}"],
                mode='text',
                textposition='top left',
                textfont=dict(color=self.color, size=self.text_size),
                showlegend=False
            ), row=row, col=col
        )


class VolumeIndicator(Indicator):
    target = 'volume'
    row_height = 200

    def apply(self, fig: go.Figure, df, row: int, col: int = 1):
        fig.add_trace(
            go.Bar(
                x=df['timestamp'],
                y=df['volume'],
                name='Volume',
                marker_color='rgba(100,100,100,0.4)'
            ),
            row=row,
            col=col
        )
        fig.update_yaxes(
            title_text="Volume",
            row=row,
            col=col,
        )


class SMAVolumeIndicator(Indicator):
    target = 'volume'
    row_height = 200

    def __init__(self, period: int = 9, color: str = 'orange'):
        self.period = period
        self.color = color

    def apply(self, fig: go.Figure, df, row: int, col: int = 1):
        df[f'volume_sma_{self.period}'] = (
            df['volume'].rolling(window=self.period).mean()
        )
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df[f'volume_sma_{self.period}'],
                mode='lines',
                name=f'Volume SMA {self.period}',
                line=dict(
                    color=self.color,
                    width=2
                )
            ),
            row=row,
            col=col
        )
        fig.update_yaxes(
            title_text="Volume SMA",
            row=row,
            col=col,
        )


class LongShortRatioIndicator(Indicator):
    target = 'ratio'
    row_height = 200

    def __init__(self, df_ratio, name: str = 'L/S Ratio'):
        self.df_ratio = df_ratio.copy()
        self.name = name
        self.threshold = 0.5
        self.above_color = "rgba(255, 0, 0, 0.4)"
        self.below_color = "rgba(0, 255, 0, 0.4)"
        self.opacity = 0.2

    def apply(self, fig: go.Figure, df, row: int, col: int = 1):
        x = self.df_ratio['timestamp']
        y = self.df_ratio['ratio']
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                fill='tozeroy',
                fillcolor=self.below_color,
                line=dict(color='rgba(0,0,0,0)'),
                showlegend=False,
            ),
            row=row,
            col=col,
        )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=[1.0] * len(x),
                fill='tonexty',
                fillcolor=self.above_color,
                line=dict(color='rgba(0,0,0,0)'),
                showlegend=False,
            ),
            row=row,
            col=col,
        )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode='lines',
                name=self.name,
                line=dict(color='rgba(0, 255, 0, 0.4)', width=1),
            ),
            row=row,
            col=col,
        )
        y_min, y_max = float(y.min()), float(y.max())
        pad = (y_max - y_min) * 0.1 or 0.01  # 10% запаса, но не менее 0.01
        fig.update_yaxes(
            range=[y_min - pad, y_max + pad],
            row=row, col=col,
        )
        fig.update_yaxes(
            title_text="Long/Short Ratio",
            row=row,
            col=col,
        )


class MACDIndicator(Indicator):
    target = 'aux'
    row_height = 400

    def __init__(self, fast=12, slow=26, signal=9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def apply(self, fig: go.Figure, df, row: int, col: int = 1):
        df['ema_fast'] = df['close'].ewm(span=self.fast).mean()
        df['ema_slow'] = df['close'].ewm(span=self.slow).mean()
        df['macd'] = df['ema_fast'] - df['ema_slow']
        df['signal'] = df['macd'].ewm(span=self.signal).mean()
        df['hist'] = df['macd'] - df['signal']

        fig.add_trace(
            go.Bar(
                x=df['timestamp'],
                y=df['hist'],
                name='Hist',
                opacity=0.3
            ),
            row=row,
            col=col
        )
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['macd'],
                name='MACD',
                line=dict(color='blue')
            ),
            row=row,
            col=col
        )
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['signal'],
                name='Signal',
                line=dict(color='orange')
            ),
            row=row,
            col=col
        )
        fig.update_yaxes(
            tickformat=".5f",  # ← это решает проблему μ
            title_text="MACD",
            row=row,
            col=col,
        )


class OpenInterestIndicator(Indicator):
    target = "open-interest"
    row_height = 200

    def __init__(self, df_oi, name: str = "Open Interest"):
        self.df_oi = df_oi.copy()
        self.name = name

    def apply(self, fig, df, row: int, col: int = 1):
        fig.add_trace(
            go.Bar(
                x=self.df_oi["timestamp"],
                y=self.df_oi["openInterest"],
                name=self.name,
                marker_color="gray",
                opacity=0.6,
            ),
            row=row,
            col=col,
        )
        fig.update_yaxes(
            title_text="Open Interest",
            row=row,
            col=col,
        )
        y = self.df_oi["openInterest"]
        y_min, y_max = float(y.min()), float(y.max())
        pad = (y_max - y_min) * 0.1 or 1  # ← 10% запаса, минимум 1
        fig.update_yaxes(
            title_text="Open Interest",
            range=[y_min - pad, y_max + pad],
            row=row,
            col=col,
        )


class FundingRateIndicator(Indicator):
    target = "funding"
    row_height = 200

    def __init__(self, df_fund, name: str = "Funding Rate"):
        self.df_fund = df_fund.copy()
        self.name = name

    def apply(self, fig: go.Figure, df, row: int, col: int = 1):
        fig.add_trace(
            go.Scatter(
                x=self.df_fund["timestamp"],
                y=self.df_fund["fundingRate"],
                mode="lines",
                name=self.name,
                line=dict(width=2),
            ),
            row=row,
            col=col,
        )

        fig.update_yaxes(
            tickformat=".5f",  # ← это решает проблему μ
            title_text="Funding Rate (%)",
            row=row,
            col=col,
        )
