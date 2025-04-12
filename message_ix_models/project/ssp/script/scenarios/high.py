import os
import ixmp
import message_ix
import pandas as pd
import numpy as np

from message_ix_models.util import package_data_path
from message_ix_models.model.material.report.run_reporting import run as report_materials
from message_data.tools.post_processing import iamc_report_hackathon

from message_ix_models.util import broadcast
from message_ix.util import make_df

from message_ix_models.util.compat.message_data.add_UE_share_constraints import main as add_UE_share_constraints

# specify scenario
model_ori = "SSP_SSP3_v4.0"
scen_ori = "SSP3 - High Emissions"
model_tar = "SSP_SSP3_v4.0"
scen_tar = "SSP3 - High Emissions_r3"

# specify UE
path_ue = package_data_path("ue-shares")
path_ue_file = os.path.join(path_ue, "H_april_2025.xlsx")

# clone scenario
mp = ixmp.Platform("ixmp_dev")
base = message_ix.Scenario(mp, model=model_ori, scenario=scen_ori)
scen = base.clone(model_tar, scen_tar, keep_solution=False)
scen.set_as_default()

# add clinker ratio fix
def gen_missing_clinker_ratios():
    # 2020 ratios from
    # https://www.sciencedirect.com/science/article/pii/S1750583624002238#bib0071
    # Appendix B
    reg_map = {
        "R12_AFR": 0.75,
        "R12_CHN": 0.65,
        "R12_EEU": 0.82,
        "R12_FSU": 0.85,
        "R12_LAM": 0.71,
        "R12_MEA": 0.8,
        "R12_NAM": 0.87,
        "R12_PAO": 0.83,
        "R12_PAS": 0.78,
        "R12_RCPA": 0.78,
        "R12_SAS": 0.7,
        "R12_WEU": 0.74,
    }
    df = make_df(
        "input",
        node_loc=reg_map.keys(),
        node_origin=reg_map.keys(),
        value=reg_map.values(),
        commodity="clinker_cement",
        level="tertiary_material",
        mode="M1",
        time="year",
        time_origin="year",
        unit="???",
    )
    df = (
        df.pipe(
            broadcast,
            technology=["grinding_ballmill_cement", "grinding_vertmill_cement"],
        )
        .pipe(broadcast, year_act=[2070, 2080])
        .pipe(broadcast, year_vtg=[2045, 2055])
    )
    df = df[df["year_act"] >= df["year_vtg"]]
    df = df[df["year_act"] - df["year_vtg"] <= 25]
    return {"input": df}

df = gen_missing_clinker_ratios()
with scen.transact():
    scen.add_par("input", df["input"])

# add UE share constraints
add_UE_share_constraints(
            scen,
            path_UE_share_input = path_ue_file,
            ssp="SSP3",
            start_year={
                "i_feed": 2025,
                "i_spec": 2025,
                "i_therm": 2025,
                "non-comm": 2030,
                "rc_spec": 2030,
                "rc_therm": 2030,
                "transport": 2030,
            },
            calibration_year=2020,
            clean_relations=True,
            verbose=True,
        )

# solve
solve_typ = "MESSAGE-MACRO"
message_ix.models.DEFAULT_CPLEX_OPTIONS = {
        "advind": 0,
        "lpmethod": 4,
        "threads": 4,
        "epopt": 1e-6,
        "scaind": -1,
        # "predual": 1, 
        "barcrossalg": 0,
    }
scen.solve(solve_typ)
scen.set_as_default()

# scen = message_ix.Scenario(mp, model=model_tar, scenario=scen_tar)

# report
scen.check_out(timeseries_only=True)
df = report_materials(scen, region="R12_GLB", upload_ts=True)
scen.commit("Add materials reporting")

iamc_report_hackathon.report(
            mp=mp,
            scen=scen,
            merge_hist=True,
            run_config="materials_daccs_run_config.yaml")

mp.close_db()