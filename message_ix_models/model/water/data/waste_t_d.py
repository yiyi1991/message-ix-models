
"""Prepare data for adding techs related to water distribution, treatment in urban & rural"""

import pandas as pd
from message_data.model.water import read_config
import os
import xarray as xr
from message_data.tools import broadcast,make_df, same_node, make_matched_dfs, get_context, make_io
from message_data.model.water.build import get_water_reference_scenario



def add_techs(info):
    """
        Parameters
        ----------
        info : .ScenarioInfo
            Information about target Scenario.

        Returns
        -------
        data : dict of (str -> pandas.DataFrame)
            Keys are MESSAGE parameter names such as 'input', 'fix_cost'. Values
            are data frames ready for :meth:`~.Scenario.add_par`.
        """

    # define an empty dictionary
    results = {}

    context = read_config()

    tec = 'urban_recycle'
    wwt_techs = ('urban_treatment', 'urban_untreated', 'urban_recycle',
                 'rural_treatment', 'rural_untreated')


    i_o = make_io(
        src=(None, None, "GWa"),
        dest=("transport pax vehicle", "useful", "Gv km"),
        efficiency=1. / base["value"],
        on="input",
        # Other data
        node_loc=base["node"],
        node_origin=base["node"],
        node_dest=base["node"],
        technology=base["technology"],
        year_vtg=base["year"],
        year_act=base["year"],
        mode="all",
        # No subannual detail
        time="year",
        time_origin="year",
        time_dest="year",
    )

    tec = ['saline_ppl_t_d'\
          'desal_t_d']

    tec_saline = ['membrane',\
                  'distillation']


    tec_urban = ['urban_recycle',\
          'urban_treatment']

    tec_t_d = ['urban_t_d',\
          'urban_unconnected',\
          'rural_t_d',\
          'rural_unconnected']

    
    return results 



