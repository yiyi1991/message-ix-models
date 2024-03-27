from itertools import product

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression  # type: ignore
from sklearn.preprocessing import PolynomialFeatures  # type: ignore

# Global variables of model years
FIRST_MODEL_YEAR = 2020
LAST_MODEL_YEAR = 2100
PRE_LAST_YEAR_RATE = 0.01


def apply_polynominal_regression(
    df_proj_costs_learning: pd.DataFrame,
) -> pd.DataFrame:
    """Perform polynomial regression on projected costs and extract coefs/intercept

    This function applies a third degree polynominal regression on the projected
    investment costs in each region (2020-2100). The coefficients and intercept
    for each technology is saved in a dataframe.

    Parameters
    ----------
    df_proj_costs_learning : pandas.DataFrame
        Output of `project_inv_cost_using_learning_rates`

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns:

        - message_technology: the technology in MESSAGEix
        - r11_region: MESSAGEix R11 region
        - beta_1: the coefficient for x^1 for the specific technology
        - beta_2: the coefficient for x^2 for the specific technology
        - beta_3: the coefficient for x^3 for the specific technology
        - intercept: the intercept from the regression

    """

    un_ssp = df_proj_costs_learning.scenario.unique()
    un_tech = df_proj_costs_learning.message_technology.unique()
    un_reg = df_proj_costs_learning.r11_region.unique()

    data_reg = []
    for i, j, k in product(un_ssp, un_tech, un_reg):
        tech = df_proj_costs_learning.loc[
            (df_proj_costs_learning.scenario == i)
            & (df_proj_costs_learning.message_technology == j)
            & (df_proj_costs_learning.r11_region == k)
        ]

        if tech.size == 0:
            continue

        x = tech.year.values
        y = tech.inv_cost_learning_region.values

        # polynomial regression model
        poly = PolynomialFeatures(degree=3, include_bias=False)
        poly_features = poly.fit_transform(x.reshape(-1, 1))

        poly_reg_model = LinearRegression()
        poly_reg_model.fit(poly_features, y)

        data = [
            [
                i,
                j,
                k,
                poly_reg_model.coef_[0],
                poly_reg_model.coef_[1],
                poly_reg_model.coef_[2],
                poly_reg_model.intercept_,
            ]
        ]
        df = pd.DataFrame(
            data,
            columns=[
                "scenario",
                "message_technology",
                "r11_region",
                "beta_1",
                "beta_2",
                "beta_3",
                "intercept",
            ],
        )

        data_reg.append(df)

    df_regression = pd.concat(data_reg).reset_index(drop=1)

    return df_regression


def project_costs_using_splines(
    input_df_region_diff: pd.DataFrame,
    input_df_technology_first_year: pd.DataFrame,
    input_df_poly_reg: pd.DataFrame,
    input_df_learning_projections: pd.DataFrame,
    input_df_fom_inv_ratios: pd.DataFrame,
) -> pd.DataFrame:
    """Project costs using splines

    Parameters
    ----------
    input_df_region_diff : pandas.DataFrame
        Output of `get_region_differentiated_costs`
    input_df_technology_first_year : pandas.DataFrame
        Output of `get_technology_first_year_data`
    input_df_poly_reg : pandas.DataFrame
        Output of `apply_polynominal_regression`
    input_df_learning_projections : pandas.DataFrame
        Output of `project_inv_cost_using_learning_rates`
    input_df_fom_inv_ratios : pandas.DataFrame
        Output of `calculate_fom_to_inv_cost_ratios`
    input_df_gdp_ratios : pandas.DataFrame
        Output of `get_gdp_data`
    input_df_gdp_reg : pandas.DataFrame
        Output of `linearly_regress_tech_cost_vs_gdp_ratios`

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns:
        - scenario: the SSP scenario
        - message_technology: the technology in MESSAGEix
        - r11_region: MESSAGEix R11 region
        - year: the year modeled (2020-2100)
        - inv_cost: the investment cost in units of USD/kW
        - fix_cost: the fixed O&M cost in units of USD/kW

    """
    df = (
        input_df_region_diff.loc[input_df_region_diff.cost_type == "inv_cost"]
        .reindex(
            ["cost_type", "message_technology", "r11_region", "cost_region_2021"],
            axis=1,
        )
        .merge(
            input_df_technology_first_year.drop(columns=["first_year_original"]),
            on=["message_technology"],
            how="right",
        )
        .merge(input_df_poly_reg, on=["message_technology", "r11_region"])
    )

    seq_years = list(range(FIRST_MODEL_YEAR, LAST_MODEL_YEAR + 10, 10))
    for y in seq_years:
        df = df.assign(
            ycur=lambda x: np.where(
                y <= x.first_technology_year,
                x.cost_region_2021,
                (x.beta_1 * y)
                + (x.beta_2 * (y**2))
                + (x.beta_3 * (y**3))
                + x.intercept,
            )
        ).rename(columns={"ycur": y})

    df_long = (
        df.drop(
            columns=["first_technology_year", "beta_1", "beta_2", "beta_3", "intercept"]
        )
        .melt(
            id_vars=[
                "cost_type",
                "scenario",
                "message_technology",
                "r11_region",
                "cost_region_2021",
            ],
            var_name="year",
            value_name="inv_cost_splines",
        )
        .merge(
            input_df_learning_projections,
            on=[
                "scenario",
                "message_technology",
                "r11_region",
                "year",
            ],
        )
        .assign(
            inv_cost=lambda x: np.where(
                x.r11_region == "NAM",
                x.inv_cost_learning_region,
                x.inv_cost_splines,
            )
        )
        .merge(input_df_fom_inv_ratios, on=["message_technology", "r11_region"])
        .assign(fix_cost=lambda x: x.inv_cost * x.fom_to_inv_cost_ratio)
        .reindex(
            [
                "scenario",
                "message_technology",
                "r11_region",
                "year",
                "inv_cost_learning_region",
                "inv_cost_splines",
                "inv_cost",
                "fix_cost",
            ],
            axis=1,
        )
        .drop_duplicates()
        .reset_index(drop=1)
    )

    return df_long
