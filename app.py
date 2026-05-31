from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from credit_risk_portfolio import BuildConfig, build_scenario_results, build_segment_tables, generate_portfolio, inr_cr


st.set_page_config(
    page_title="Credit Risk Stress Testing",
    page_icon="",
    layout="wide",
)


@st.cache_data
def load_model_outputs(seed: int = 42, loan_count: int = 10_000):
    portfolio = generate_portfolio(BuildConfig(seed=seed, loan_count=loan_count))
    scenario_df, scenario_loan_level = build_scenario_results(portfolio)
    segments = build_segment_tables(portfolio, scenario_loan_level)
    return portfolio, scenario_df, segments


portfolio, scenario_df, segments = load_model_outputs()
baseline_el = float(scenario_df.loc[scenario_df["Scenario"] == "Baseline", "Expected_Loss"].iloc[0])
severe_el = float(scenario_df.loc[scenario_df["Scenario"] == "Severe", "Expected_Loss"].iloc[0])
portfolio_ead = float(portfolio["EAD"].sum())
capital_shortfall = severe_el - baseline_el

st.title("Credit Risk Portfolio Stress Testing")
st.caption("PD, LGD, EAD, expected loss and stress testing for a simulated loan portfolio.")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Portfolio Exposure", f"Rs {inr_cr(portfolio_ead):,.1f} Cr")
kpi2.metric("Baseline Expected Loss", f"Rs {inr_cr(baseline_el):,.1f} Cr", f"{baseline_el / portfolio_ead:.2%}")
kpi3.metric("Severe Expected Loss", f"Rs {inr_cr(severe_el):,.1f} Cr", f"{severe_el / baseline_el:,.1f}x")
kpi4.metric("Capital Shortfall", f"Rs {inr_cr(capital_shortfall):,.1f} Cr")

st.divider()

left, right = st.columns([1, 1])

with left:
    st.subheader("Scenario Stress Test")
    scenario_chart = scenario_df.assign(Expected_Loss_Cr=scenario_df["Expected_Loss"].map(inr_cr)).set_index("Scenario")
    st.bar_chart(scenario_chart["Expected_Loss_Cr"], y_label="Expected Loss Rs Cr")
    st.dataframe(
        scenario_df.assign(
            Total_Portfolio_Cr=scenario_df["Total_Portfolio"].map(inr_cr),
            Expected_Loss_Cr=scenario_df["Expected_Loss"].map(inr_cr),
            Capital_Required_Cr=scenario_df["Capital_Required"].map(inr_cr),
        )[["Scenario", "Total_Portfolio_Cr", "Expected_Loss_Cr", "EL_Pct", "Capital_Required_Cr"]],
        width="stretch",
        hide_index=True,
    )

with right:
    st.subheader("Expected Loss by Rating")
    rating_summary = segments["rating_summary"].copy()
    rating_summary["baseline_el_cr"] = rating_summary["baseline_el"].map(inr_cr)
    rating_summary["severe_el_cr"] = rating_summary["severe_el"].map(inr_cr)
    st.bar_chart(
        rating_summary.set_index("credit_rating")[["baseline_el_cr", "severe_el_cr"]],
        y_label="Expected Loss Rs Cr",
    )
    st.dataframe(
        rating_summary[
            ["credit_rating", "loans", "ead", "avg_pd", "avg_lgd", "baseline_el", "severe_el", "watchlist_loans"]
        ],
        width="stretch",
        hide_index=True,
    )

st.subheader("Sector Concentration")
sector_summary = segments["sector_summary"].copy()
sector_summary["EAD Rs Cr"] = sector_summary["ead"].map(inr_cr)
sector_summary["Baseline EL Rs Cr"] = sector_summary["baseline_el"].map(inr_cr)
sector_summary["Severe EL Rs Cr"] = sector_summary["severe_el"].map(inr_cr)
st.dataframe(
    sector_summary[["sector", "loans", "EAD Rs Cr", "Baseline EL Rs Cr", "Severe EL Rs Cr", "watchlist_loans"]],
    width="stretch",
    hide_index=True,
)

st.subheader("Watchlist Loans")
st.caption("Lower-rated loans with high LTV and repayment pressure are flagged for closer monitoring.")
watchlist = segments["watchlist_top100"].copy()
watchlist["Severe EL Rs"] = watchlist["Severe_EL"]
st.dataframe(
    watchlist[
        [
            "loan_id",
            "sector",
            "credit_rating",
            "loan_amount",
            "interest_rate",
            "ltv_ratio",
            "dti_ratio",
            "PD",
            "LGD",
            "Severe EL Rs",
            "watchlist_reason",
        ]
    ],
    width="stretch",
    hide_index=True,
)

with st.expander("Model logic"):
    st.write(
        "Expected Loss is calculated as PD x LGD x EAD. "
        "The stress test increases PDs across rating grades under downside and severe scenarios, "
        "then compares expected loss and capital required against the baseline case."
    )
