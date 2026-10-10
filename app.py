
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(
    page_title="Multi-Stock Risk Analyzer",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Multi-Stock Performance & Risk Analyzer")
st.caption(
    "Compare historical stock performance, returns and risk metrics."
)

# ---------------- SIDEBAR ----------------

st.sidebar.header("Analysis Settings")

default_stocks = ["RELIANCE.NS", "TCS.NS", "ICICIBANK.NS"]

stocks = st.sidebar.multiselect(
    "Select stocks",
    options=[
        "RELIANCE.NS",
        "TCS.NS",
        "ICICIBANK.NS",
        "HDFCBANK.NS",
        "INFY.NS",
        "SBIN.NS",
        "BHARTIARTL.NS",
        "ITC.NS",
        "LT.NS",
        "AXISBANK.NS",
        "BAJFINANCE.NS",
        "MARUTI.NS"
    ],
    default=default_stocks
)

period = st.sidebar.selectbox(
    "Historical period",
    ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
    index=3
)

benchmark = st.sidebar.selectbox(
    "Benchmark",
    ["^NSEI", "^BSESN"],
    format_func=lambda x: {
        "^NSEI": "Nifty 50",
        "^BSESN": "BSE Sensex"
    }[x]
)

risk_free_rate = st.sidebar.number_input(
    "Annual risk-free rate (%)",
    min_value=0.0,
    max_value=20.0,
    value=6.0,
    step=0.5
)

analyze = st.sidebar.button(
    "Analyze Stocks",
    type="primary",
    use_container_width=True
)

# ---------------- FUNCTIONS ----------------

@st.cache_data(ttl=900, show_spinner=False)
def download_prices(tickers, selected_period, benchmark_ticker):
    stock_data = yf.download(
        tickers=list(tickers),
        period=selected_period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="column",
        threads=True
    )

    if stock_data.empty:
        raise ValueError("No stock price data was returned.")

    # Handle yfinance column formats for one or multiple stocks.
    if isinstance(stock_data.columns, pd.MultiIndex):
        if "Close" not in stock_data.columns.get_level_values(0):
            raise ValueError("Closing prices are unavailable.")
        close = stock_data["Close"]
    else:
        if "Close" not in stock_data.columns:
            raise ValueError("Closing prices are unavailable.")
        close = stock_data[["Close"]]
        close.columns = list(tickers)

    if isinstance(close, pd.Series):
        close = close.to_frame(name=list(tickers)[0])

    close = close.dropna(how="all").sort_index()
    close = close.loc[:, ~close.columns.duplicated()]

    # Remove stocks with no usable data.
    close = close.dropna(axis=1, how="all")

    benchmark_data = yf.download(
        benchmark_ticker,
        period=selected_period,
        interval="1d",
        auto_adjust=True,
        progress=False
    )

    if benchmark_data.empty or "Close" not in benchmark_data.columns:
        raise ValueError("Benchmark data could not be downloaded.")

    benchmark_close = benchmark_data["Close"]

    if isinstance(benchmark_close, pd.DataFrame):
        benchmark_close = benchmark_close.iloc[:, 0]

    benchmark_close.name = benchmark_ticker

    return close, benchmark_close


def calculate_metrics(prices, benchmark_returns, risk_free):
    results = []

    for ticker in prices.columns:
        series = prices[ticker].dropna()

        if len(series) < 2:
            continue

        # Calculate returns using available adjusted closing prices.
        daily_returns = series.pct_change().dropna()

        if daily_returns.empty:
            continue

        total_return = (series.iloc[-1] / series.iloc[0] - 1) * 100
        volatility = daily_returns.std() * np.sqrt(252) * 100

        daily_rf = (1 + risk_free) ** (1 / 252) - 1
        daily_std = daily_returns.std()

        if pd.notna(daily_std) and daily_std > 0:
            sharpe = (
                (daily_returns.mean() - daily_rf)
                / daily_std
                * np.sqrt(252)
            )
        else:
            sharpe = np.nan

        # Align stock and benchmark returns by date.
        aligned = pd.concat(
            [daily_returns, benchmark_returns],
            axis=1,
            join="inner"
        ).dropna()

        if len(aligned) >= 2 and aligned.iloc[:, 1].var() > 0:
            beta = (
                aligned.iloc[:, 0].cov(aligned.iloc[:, 1])
                / aligned.iloc[:, 1].var()
            )
        else:
            beta = np.nan

        # Maximum peak-to-trough decline.
        drawdown = (series / series.cummax() - 1) * 100
        max_drawdown = drawdown.min()

        results.append({
            "Stock": ticker,
            "Total Return (%)": total_return,
            "Annualized Volatility (%)": volatility,
            "Sharpe Ratio": sharpe,
            "Beta": beta,
            "Max Drawdown (%)": max_drawdown
        })

    return pd.DataFrame(results)


# ---------------- MAIN APPLICATION ----------------

if not stocks:
    st.info("Select at least one stock from the sidebar.")
    st.stop()

if analyze or "analysis_done" not in st.session_state:
    st.session_state.analysis_done = True
    st.session_state.selected_stocks = stocks
    st.session_state.selected_period = period
    st.session_state.selected_benchmark = benchmark
    st.session_state.selected_rf = risk_free_rate / 100

# Use the latest sidebar settings when the user changes inputs.
selected_stocks = stocks
selected_period = period
selected_benchmark = benchmark
selected_rf = risk_free_rate / 100

try:
    with st.spinner("Downloading market data and calculating metrics..."):
        prices, benchmark_prices = download_prices(
            tuple(selected_stocks),
            selected_period,
            selected_benchmark
        )

        if prices.empty:
            st.error("No valid stock price data was found.")
            st.stop()

        # Exclude stocks with insufficient data.
        prices = prices.dropna(axis=1, how="all")
        benchmark_returns = benchmark_prices.pct_change().dropna()

        metrics = calculate_metrics(
            prices,
            benchmark_returns,
            selected_rf
        )

        if metrics.empty:
            st.error("Not enough data to calculate risk metrics.")
            st.stop()

        # Normalize each stock to 100 at its first valid observation.
        normalized = prices.apply(
            lambda col: col / col.dropna().iloc[0] * 100
            if not col.dropna().empty else col
        )

        # ---------------- SUMMARY ----------------

        st.subheader("Portfolio Comparison")

        best_stock = metrics.loc[
            metrics["Total Return (%)"].idxmax()
        ]

        riskiest_stock = metrics.loc[
            metrics["Annualized Volatility (%)"].idxmax()
        ]

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Stocks Analyzed",
            len(metrics)
        )

        c2.metric(
            "Top Performer",
            best_stock["Stock"],
            f'{best_stock["Total Return (%)"]:.2f}% return'
        )

        c3.metric(
            "Highest Volatility",
            riskiest_stock["Stock"],
            f'{riskiest_stock["Annualized Volatility (%)"]:.2f}%'
        )

        # ---------------- CHARTS ----------------

        st.subheader("1. Normalized Stock Performance")
        st.caption(
            "Every stock starts at 100. Values above 100 indicate "
            "a gain relative to its starting price."
        )

        st.line_chart(normalized, use_container_width=True)

        st.subheader("2. Daily Returns Comparison")

        daily_returns = prices.pct_change() * 100
        st.line_chart(
            daily_returns,
            use_container_width=True
        )

        # ---------------- METRICS TABLE ----------------

        st.subheader("3. Returns & Risk Metrics")

        display_metrics = metrics.copy()

        for col in [
            "Total Return (%)",
            "Annualized Volatility (%)",
            "Sharpe Ratio",
            "Beta",
            "Max Drawdown (%)"
        ]:
            display_metrics[col] = display_metrics[col].round(2)

        st.dataframe(
            display_metrics,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Risk Analysis CSV",
            data=display_metrics.to_csv(index=False).encode("utf-8"),
            file_name="stock_risk_analysis.csv",
            mime="text/csv"
        )

        # ---------------- DRAWDOWN ----------------

        st.subheader("4. Drawdown Analysis")

        drawdowns = prices.apply(
            lambda col: (col / col.cummax() - 1) * 100
        )

        st.area_chart(
            drawdowns,
            use_container_width=True
        )

        # ---------------- METHODOLOGY ----------------

        with st.expander("Understand the metrics"):
            st.markdown("""
            - **Total return:** Percentage change from the first
              available closing price to the latest price.
            - **Annualized volatility:** Standard deviation of daily
              returns multiplied by the square root of 252.
            - **Sharpe ratio:** Annualized excess return divided by
              annualized volatility, using the selected risk-free rate.
            - **Beta:** Sensitivity of a stock's daily returns to the
              benchmark's daily returns.
            - **Maximum drawdown:** Largest observed percentage decline
              from a previous price peak.
            - **Benchmark:** Nifty 50 or BSE Sensex, selected in the
              sidebar.
            
            Metrics use historical data and do not predict future returns.
            """)

        st.caption(
            f"Period: {selected_period} | "
            f"Benchmark: {selected_benchmark} | "
            "Data source: Yahoo Finance via yfinance. "
            "Prices are adjusted for corporate actions where available."
        )

except Exception as e:
    st.error(
        "Unable to complete the analysis. Check your internet connection, "
        "selected tickers, and data availability."
    )
    st.caption(f"Technical details: {e}")
