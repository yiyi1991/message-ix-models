from itertools import product

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression  # type: ignore
from sklearn.preprocessing import PolynomialFeatures  # type: ignore

from message_ix_models.tools.costs.config import (
    FIRST_MODEL_YEAR,
    LAST_MODEL_YEAR,
    TIME_STEPS,
)


# Function to apply polynomial regression to convergence costs
def apply_splines_to_convergence(
    df_reg,
    column_name,
    convergence_year,
):
    """Apply polynomial regression and splines to convergence"""

    # un_vers = df.scenario_version.unique()
    un_ssp = df_reg.scenario.unique()
    un_tech = df_reg.message_technology.unique()
    un_reg = df_reg.region.unique()

    data_reg = []
    for i, j, k in product(un_ssp, un_tech, un_reg):
        tech = df_reg.query(
            "scenario == @i and message_technology == @j \
                and region == @k"
        ).query("year == @FIRST_MODEL_YEAR or year >= @convergence_year")

        if tech.size == 0:
            continue

        x = tech.year.values
        y = tech[[column_name]].values

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
                poly_reg_model.coef_[0][0],
                poly_reg_model.coef_[0][1],
                poly_reg_model.coef_[0][2],
                poly_reg_model.intercept_[0],
            ]
        ]

        df = pd.DataFrame(
            data,
            columns=[
                "scenario",
                "message_technology",
                "region",
                "beta_1",
                "beta_2",
                "beta_3",
                "intercept",
            ],
        )

        data_reg.append(df)

    df_reg = pd.concat(data_reg).reset_index(drop=1)
    df_wide = (
        df.reindex(
            [
                "scenario",
                "message_technology",
                "region",
                "first_technology_year",
                "reg_cost_base_year",
            ],
            axis=1,
        )
        .drop_duplicates()
        .merge(df_reg, on=["scenario", "message_technology", "region"])
    )

    seq_years = list(range(FIRST_MODEL_YEAR, LAST_MODEL_YEAR + TIME_STEPS, TIME_STEPS))

    for y in seq_years:
        df_wide = df_wide.assign(
            ycur=lambda x: np.where(
                y <= x.first_technology_year,
                x.reg_cost_base_year,
                (x.beta_1 * y)
                + (x.beta_2 * (y**2))
                + (x.beta_3 * (y**3))
                + x.intercept,
            )
        ).rename(columns={"ycur": y})

    df_long = df_wide.drop(
        columns=[
            "first_technology_year",
            "beta_1",
            "beta_2",
            "beta_3",
            "intercept",
            "reg_cost_base_year",
        ]
    ).melt(
        id_vars=[
            "scenario",
            "message_technology",
            "region",
        ],
        var_name="year",
        value_name="inv_cost_splines",
    )

    return df_long
