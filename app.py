
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Automated DCF Valuation",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Automated DCF Valuation Platform")
st.caption(
    "Forecast financial performance, value a business using FCFF, "
    "and compare investment scenarios."
)

# ==========================================================
# SIDEBAR: INPUT ASSUMPTIONS
# All monetary values are in the selected currency unit.
# Example: enter revenue in ₹ crore if using INR crore.
# ==========================================================


st.sidebar.header("Company Information")

stock_mode = st.sidebar.radio(
    "Choose company input method",
    ["Existing Listed Stock", "Enter Company Manually"]
)

listed_stocks = {
    "Reliance Industries": {
        "ticker": "RELIANCE.NS",
        "price": 0.0
    },
    "TCS": {
        "ticker": "TCS.NS",
        "price": 0.0
    },
    "Infosys": {
        "ticker": "INFY.NS",
        "price": 0.0
    },
    "HDFC Bank": {
        "ticker": "HDFCBANK.NS",
        "price": 0.0
    },
    "ICICI Bank": {
        "ticker": "ICICIBANK.NS",
        "price": 0.0
    },
    "State Bank of India": {
        "ticker": "SBIN.NS",
        "price": 0.0
    },
    "ITC": {
        "ticker": "ITC.NS",
        "price": 0.0
    },
    "Bharti Airtel": {
        "ticker": "BHARTIARTL.NS",
        "price": 0.0
    },
    "Larsen & Toubro": {
        "ticker": "LT.NS",
        "price": 0.0
    },
    "Wipro": {
        "ticker": "WIPRO.NS",
        "price": 0.0
    }
}

if stock_mode == "Existing Listed Stock":
    selected_company = st.sidebar.selectbox(
        "Select listed company",
        list(listed_stocks.keys())
    )
    company = selected_company
    ticker = listed_stocks[selected_company]["ticker"]

    st.sidebar.caption(f"Yahoo Finance ticker: {ticker}")

else:
    company = st.sidebar.text_input(
        "Company name",
        "Sample Industries Ltd."
    )
    ticker = None


company = st.sidebar.text_input("Company name", "Sample Industries Ltd.")
currency = st.sidebar.selectbox(
    "Currency / unit",
    ["₹ crore", "$ million", "$ billion", "₹ million"]
)

market_price = st.sidebar.number_input(
    "Current market price per share",
    min_value=0.01,
    value=500.0,
    step=10.0
)

shares = st.sidebar.number_input(
    "Shares outstanding (million)",
    min_value=0.01,
    value=100.0,
    step=1.0,
    help="Enter shares in millions. Use the same unit consistently."
)

st.sidebar.header("Starting Financials")

revenue = st.sidebar.number_input(
    "Latest annual revenue",
    min_value=0.01,
    value=1000.0,
    step=50.0
)

ebitda_margin = st.sidebar.slider(
    "Starting EBITDA margin (%)",
    1.0, 50.0, 20.0, 0.5
)

da_pct = st.sidebar.slider(
    "Depreciation & amortization (% of revenue)",
    0.0, 15.0, 4.0, 0.5
)

capex_pct = st.sidebar.slider(
    "Capital expenditure (% of revenue)",
    0.0, 25.0, 6.0, 0.5
)

nwc_pct = st.sidebar.slider(
    "Net working capital (% of revenue)",
    0.0, 30.0, 10.0, 0.5
)

tax_rate = st.sidebar.slider(
    "Tax rate (%)",
    0.0, 40.0, 25.0, 1.0
) / 100

st.sidebar.header("Valuation Assumptions")

growth = st.sidebar.slider(
    "Base-case annual revenue growth (%)",
    -10.0, 40.0, 10.0, 1.0
) / 100

margin_change = st.sidebar.slider(
    "Annual EBITDA margin improvement (percentage points)",
    -2.0, 3.0, 0.5, 0.25
) / 100

wacc = st.sidebar.slider(
    "WACC (%)",
    5.0, 25.0, 11.0, 0.5
) / 100

terminal_growth = st.sidebar.slider(
    "Terminal growth rate (%)",
    0.0, 6.0, 4.0, 0.25
) / 100

st.sidebar.header("Capital Structure")

debt = st.sidebar.number_input(
    "Total debt",
    min_value=0.0,
    value=200.0,
    step=10.0
)

cash = st.sidebar.number_input(
    "Cash and cash equivalents",
    min_value=0.0,
    value=100.0,
    step=10.0
)

st.sidebar.caption(
    "Keep revenue, debt and cash in the same monetary unit. "
    "Share count must be in millions when monetary values are in millions."
)

# ==========================================================
# VALIDATION
# ==========================================================

if terminal_growth >= wacc:
    st.error(
        "Terminal growth must be lower than WACC. "
        "Please adjust the assumptions in the sidebar."
    )
    st.stop()

if da_pct > ebitda_margin:
    st.warning(
        "D&A exceeds the starting EBITDA margin, producing negative EBIT. "
        "Check whether this assumption is appropriate."
    )

# ==========================================================
# DCF ENGINE
# FCFF = EBIT(1 - tax rate) + D&A - CapEx - Change in NWC
# ==========================================================

def build_forecast(
    starting_revenue,
    starting_margin,
    revenue_growth,
    annual_margin_change
):
    rows = []
    previous_revenue = starting_revenue
    previous_nwc = starting_revenue * nwc_pct / 100

    for year in range(1, 6):
        forecast_revenue = previous_revenue * (1 + revenue_growth)

        margin = (
            starting_margin / 100
            + annual_margin_change * year
        )
        margin = max(0.0, margin)

        ebitda = forecast_revenue * margin
        depreciation = forecast_revenue * da_pct / 100
        ebit = ebitda - depreciation

        # Simplified operating cash tax assumption.
        operating_taxes = max(0.0, ebit * tax_rate)
        nopat = ebit - operating_taxes

        capex = forecast_revenue * capex_pct / 100
        nwc = forecast_revenue * nwc_pct / 100
        change_nwc = nwc - previous_nwc

        fcff = nopat + depreciation - capex - change_nwc
        discount_factor = 1 / (1 + wacc) ** year
        present_value_fcff = fcff * discount_factor

        rows.append({
            "Year": f"Year {year}",
            "Revenue": forecast_revenue,
            "Revenue Growth (%)": revenue_growth * 100,
            "EBITDA Margin (%)": margin * 100,
            "EBITDA": ebitda,
            "Depreciation & Amortization": depreciation,
            "EBIT": ebit,
            "Operating Taxes": operating_taxes,
            "NOPAT": nopat,
            "Capital Expenditure": capex,
            "Change in NWC": change_nwc,
            "FCFF": fcff,
            "Discount Factor": discount_factor,
            "PV of FCFF": present_value_fcff
        })

        previous_revenue = forecast_revenue
        previous_nwc = nwc

    return pd.DataFrame(rows)


def calculate_valuation(forecast, discount_rate, perpetual_growth):
    if discount_rate <= perpetual_growth:
        return None

    final_fcff = forecast["FCFF"].iloc[-1]
    terminal_value = (
        final_fcff * (1 + perpetual_growth)
        / (discount_rate - perpetual_growth)
    )

    pv_terminal_value = (
        terminal_value / (1 + discount_rate) ** len(forecast)
    )

    pv_forecast_fcff = forecast["PV of FCFF"].sum()
    enterprise_value = pv_forecast_fcff + pv_terminal_value

    equity_value = enterprise_value - debt + cash
    fair_value_per_share = equity_value / shares

    return {
        "Enterprise Value": enterprise_value,
        "Equity Value": equity_value,
        "Fair Value Per Share": fair_value_per_share,
        "PV of Forecast FCFF": pv_forecast_fcff,
        "Terminal Value": terminal_value,
        "PV of Terminal Value": pv_terminal_value,
        "Terminal Value Share (%)": (
            pv_terminal_value / enterprise_value * 100
            if enterprise_value != 0 else np.nan
        )
    }


def format_money(value):
    return f"{value:,.2f} {currency}"


# ==========================================================
# SCENARIO ANALYSIS
# ==========================================================

scenarios = {
    "Worst Case": {
        "growth": growth - 0.05,
        "margin_change": margin_change - 0.005
    },
    "Base Case": {
        "growth": growth,
        "margin_change": margin_change
    },
    "Best Case": {
        "growth": growth + 0.05,
        "margin_change": margin_change + 0.005
    }
}

forecasts = {}
valuations = {}

for scenario_name, assumptions in scenarios.items():
    forecast = build_forecast(
        revenue,
        ebitda_margin,
        assumptions["growth"],
        assumptions["margin_change"]
    )

    valuation = calculate_valuation(
        forecast,
        wacc,
        terminal_growth
    )

    forecasts[scenario_name] = forecast
    valuations[scenario_name] = valuation

base_forecast = forecasts["Base Case"]
base_valuation = valuations["Base Case"]

# ==========================================================
# EXECUTIVE SUMMARY
# ==========================================================

st.subheader(f"Valuation Overview: {company}")

if base_valuation is None:
    st.error("Invalid valuation assumptions.")
    st.stop()

fair_value = base_valuation["Fair Value Per Share"]
upside = (fair_value / market_price - 1) * 100

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Estimated Fair Value / Share",
    f"{fair_value:,.2f}",
    f"{upside:+.2f}% vs. market"
)

c2.metric(
    "Enterprise Value",
    format_money(base_valuation["Enterprise Value"])
)

c3.metric(
    "Equity Value",
    format_money(base_valuation["Equity Value"])
)

c4.metric(
    "Current Market Price",
    f"{market_price:,.2f}"
)

if upside > 10:
    st.success(
        "The base-case DCF indicates potential upside relative to "
        "the current market price."
    )
elif upside < -10:
    st.warning(
        "The base-case DCF indicates potential downside relative to "
        "the current market price."
    )
else:
    st.info(
        "The base-case DCF fair value is relatively close to the "
        "current market price."
    )

st.caption(
    "Illustrative model output, not a personalized investment recommendation. "
    "The result depends on your assumptions and data quality."
)

# ==========================================================
# FORECAST TABLE
# ==========================================================

st.subheader("1. Five-Year Financial Forecast")

forecast_columns = [
    "Year",
    "Revenue",
    "Revenue Growth (%)",
    "EBITDA Margin (%)",
    "EBITDA",
    "Depreciation & Amortization",
    "EBIT",
    "Operating Taxes",
    "NOPAT",
    "Capital Expenditure",
    "Change in NWC",
    "FCFF",
    "Discount Factor",
    "PV of FCFF"
]

forecast_display = base_forecast[forecast_columns].copy()

numeric_columns = forecast_display.select_dtypes(
    include="number"
).columns

forecast_display[numeric_columns] = forecast_display[
    numeric_columns
].round(2)

st.dataframe(
    forecast_display,
    use_container_width=True,
    hide_index=True
)

st.bar_chart(
    base_forecast.set_index("Year")[["Revenue", "EBITDA", "FCFF"]]
)

# ==========================================================
# SCENARIO COMPARISON
# ==========================================================

st.subheader("2. Worst, Base & Best-Case Valuation")

scenario_rows = []

for name, valuation in valuations.items():
    scenario_rows.append({
        "Scenario": name,
        "Revenue Growth (%)": scenarios[name]["growth"] * 100,
        "Fair Value / Share": valuation["Fair Value Per Share"],
        "Enterprise Value": valuation["Enterprise Value"],
        "Equity Value": valuation["Equity Value"],
        "Upside / Downside (%)": (
            valuation["Fair Value Per Share"] / market_price - 1
        ) * 100
    })

scenario_table = pd.DataFrame(scenario_rows)

st.dataframe(
    scenario_table.round(2),
    use_container_width=True,
    hide_index=True
)

st.bar_chart(
    scenario_table.set_index("Scenario")[["Fair Value / Share"]]
)

# ==========================================================
# WACC VS TERMINAL GROWTH SENSITIVITY
# ==========================================================

st.subheader("3. Valuation Sensitivity Analysis")

st.write(
    "Fair value per share under different WACC and terminal growth "
    "assumptions. All other base-case forecast assumptions remain fixed."
)

wacc_values = sorted(set([
    max(0.01, wacc - 0.02),
    max(0.01, wacc - 0.01),
    wacc,
    wacc + 0.01,
    wacc + 0.02
]))

growth_values = sorted(set([
    max(-0.02, terminal_growth - 0.02),
    max(-0.01, terminal_growth - 0.01),
    terminal_growth,
    terminal_growth + 0.01,
    terminal_growth + 0.02
]))

sensitivity = pd.DataFrame(
    index=[f"{x:.1%}" for x in growth_values],
    columns=[f"{x:.1%}" for x in wacc_values],
    dtype=float
)

for g in growth_values:
    for r in wacc_values:
        if r > g:
            result = calculate_valuation(base_forecast, r, g)
            sensitivity.loc[f"{g:.1%}", f"{r:.1%}"] = (
                result["Fair Value Per Share"]
            )
        else:
            sensitivity.loc[f"{g:.1%}", f"{r:.1%}"] = np.nan

sensitivity.index.name = "Terminal Growth / WACC"

st.dataframe(
    sensitivity.round(2),
    use_container_width=True
)

# ==========================================================
# VALUATION BRIDGE
# ==========================================================

st.subheader("4. Enterprise Value to Equity Value Bridge")

bridge = pd.DataFrame({
    "Component": [
        "PV of forecast FCFF",
        "PV of terminal value",
        "Enterprise value",
        "Less: Debt",
        "Add: Cash",
        "Equity value"
    ],
    "Value": [
        base_valuation["PV of Forecast FCFF"],
        base_valuation["PV of Terminal Value"],
        base_valuation["Enterprise Value"],
        -debt,
        cash,
        base_valuation["Equity Value"]
    ]
})

st.dataframe(
    bridge.round(2),
    use_container_width=True,
    hide_index=True
)

st.caption(
    f"Terminal value represents "
    f"{base_valuation['Terminal Value Share (%)']:.1f}% "
    "of enterprise value in the base case."
)

# ==========================================================
# EXPORTS
# ==========================================================

st.subheader("5. Download Your Analysis")

forecast_csv = base_forecast.to_csv(index=False).encode("utf-8")
scenario_csv = scenario_table.to_csv(index=False).encode("utf-8")
sensitivity_csv = sensitivity.to_csv().encode("utf-8")

d1, d2, d3 = st.columns(3)

d1.download_button(
    "Download Forecast CSV",
    forecast_csv,
    "dcf_forecast.csv",
    "text/csv",
    use_container_width=True
)

d2.download_button(
    "Download Scenarios CSV",
    scenario_csv,
    "dcf_scenarios.csv",
    "text/csv",
    use_container_width=True
)

d3.download_button(
    "Download Sensitivity CSV",
    sensitivity_csv,
    "dcf_sensitivity.csv",
    "text/csv",
    use_container_width=True
)

with st.expander("Model methodology & limitations"):
    st.markdown("""
    **Free Cash Flow to the Firm (FCFF)**

    FCFF = EBIT × (1 − Tax Rate) + D&A − Capital Expenditure − Change in NWC

    **Enterprise Value**

    EV = PV of forecast FCFF + PV of terminal value

    **Terminal Value — Gordon Growth**

    TV = Final-year FCFF × (1 + terminal growth) / (WACC − terminal growth)

    **Equity Value**

    Equity Value = Enterprise Value − Debt + Cash

    **Fair Value Per Share**

    Fair Value = Equity Value / Shares Outstanding

    **Important limitations**

    - All company financial inputs are entered by the user; this version
      does not automatically retrieve financial statements.
    - WACC is supplied directly by the user rather than calculated from CAPM.
    - Tax losses, changing tax rates, debt schedules, dilution and minority
      interests are not modeled.
    - The scenario ranges are illustrative assumption changes, not
      statistically estimated confidence intervals.
    - Ensure the monetary units and share-count units are consistent.
    - Use normalized working capital assumptions appropriate for the company.
    """)

st.divider()
st.caption(
    "Automated DCF Valuation Platform | Educational and analytical use"
)
