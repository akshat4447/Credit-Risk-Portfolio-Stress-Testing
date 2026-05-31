import sys
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from credit_risk_portfolio import (  # noqa: E402
    BuildConfig,
    RATING_ORDER,
    build_scenario_results,
    build_segment_tables,
    generate_portfolio,
)


class CreditRiskPortfolioTests(unittest.TestCase):
    def test_portfolio_generation_has_expected_core_fields(self):
        portfolio = generate_portfolio(BuildConfig(seed=7, loan_count=500))

        required = {
            "loan_id",
            "loan_amount",
            "credit_rating",
            "PD",
            "LGD",
            "EAD",
            "Expected_Loss",
            "downgrade_risk",
        }
        self.assertTrue(required.issubset(portfolio.columns))
        self.assertEqual(len(portfolio), 500)
        self.assertTrue(portfolio["loan_id"].is_unique)
        self.assertTrue(portfolio["credit_rating"].astype(str).isin(RATING_ORDER).all())
        self.assertTrue((portfolio["Expected_Loss"] >= 0).all())

    def test_scenario_stress_is_monotonic_and_capitalized(self):
        portfolio = generate_portfolio(BuildConfig(seed=11, loan_count=1_000))
        scenario_df, loan_level = build_scenario_results(portfolio)

        baseline = scenario_df.loc[scenario_df["Scenario"] == "Baseline", "Expected_Loss"].iloc[0]
        downside = scenario_df.loc[scenario_df["Scenario"] == "Downside", "Expected_Loss"].iloc[0]
        severe = scenario_df.loc[scenario_df["Scenario"] == "Severe", "Expected_Loss"].iloc[0]

        self.assertLess(baseline, downside)
        self.assertLess(downside, severe)
        self.assertTrue((scenario_df["Capital_Required"] == scenario_df["Expected_Loss"] * 1.25).all())
        self.assertTrue({"Baseline_EL", "Downside_EL", "Severe_EL"}.issubset(loan_level.columns))

    def test_segment_tables_cover_portfolio_exposure(self):
        portfolio = generate_portfolio(BuildConfig(seed=13, loan_count=1_000))
        _, loan_level = build_scenario_results(portfolio)
        tables = build_segment_tables(portfolio, loan_level)
        rating_summary = tables["rating_summary"]
        sector_matrix = tables["sector_rating_matrix"]

        self.assertEqual(round(rating_summary["ead"].sum(), 2), round(portfolio["EAD"].sum(), 2))
        self.assertEqual(list(rating_summary["credit_rating"].astype(str)), RATING_ORDER)
        self.assertFalse(sector_matrix.empty)
        self.assertIsInstance(tables["watchlist_top100"], pd.DataFrame)


if __name__ == "__main__":
    unittest.main()
