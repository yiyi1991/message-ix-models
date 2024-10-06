"""Data for light-duty vehicles (LDVs) for passenger transport."""

import logging
from collections import defaultdict
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, cast

import genno
import pandas as pd
from genno import Computer, Key, KeySeq
from message_ix import make_df
from openpyxl import load_workbook
from sdmx.model.v21 import Code

from message_ix_models.model import disutility
from message_ix_models.model.structure import get_codes
from message_ix_models.tools import exo_data
from message_ix_models.util import (
    ScenarioInfo,
    broadcast,
    cached,
    check_support,
    make_io,
    make_matched_dfs,
    merge_data,
    minimum_version,
    package_data_path,
    same_node,
)

from . import files as exo
from .data import MaybeAdaptR11Source
from .emission import ef_for_input
from .operator import extend_y
from .util import input_commodity_level

if TYPE_CHECKING:
    from genno.types import AnyQuantity

    from .config import Config

log = logging.getLogger(__name__)


@exo_data.register_source
class LDV(MaybeAdaptR11Source):
    """Provider of exogenous data on LDVs

    Parameters
    ----------
    source_kw :
       Must include exactly the keys "measure" (must be one of "fuel economy",
       "fix_cost", or "inv_cost"), "nodes", and "scenario".
    """

    id = __name__
    measures = {"inv_cost", "fuel economy", "fix_cost"}
    filename = {
        "inv_cost": "ldv-inv_cost.csv",
        "fuel economy": "ldv-fuel-economy.csv",
        "fix_cost": "ldv-fix_cost.csv",
    }

    def __init__(self, source, source_kw) -> None:
        super().__init__(source, source_kw)
        # Use "exo" tag on the target key, to align with existing code in this module
        self.key = Key(f"ldv {self.measure}:n-t-y:exo")


def prepare_computer(c: Computer):
    """Set up `c` to compute techno-economic data for light-duty-vehicle technologies.

    Results in a key ``ldv::ixmp`` that triggers computation of :mod:`ixmp`-ready
    parameter data for LDV technologies. These computations respond to
    :attr:`.DataSourceConfig.LDV`:

    - :obj:`None`: :func:`get_dummy` is used.
    - “US-TIMES MA3T”: :func:`get_USTIMES_MA3T` is used.

    In both cases, :func:`get_constraints` is used to generate constraints.
    """
    from genno import Key
    from genno.core.attrseries import AttrSeries

    from . import factor

    context = c.graph["context"]
    config: "Config" = context.transport
    source = config.data_source.LDV
    info = config.base_model_info

    # Use .tools.exo_data.prepare_computer() to add task that load, adapt, and select
    # the appropriate data
    for measure in LDV.measures:
        exo_data.prepare_computer(
            context,
            c,
            source=__name__,
            source_kw=dict(
                measure=measure,
                nodes=context.model.regions,
                scenario=str(config.ssp),
            ),
            strict=False,
        )

    # Insert a scaling factor that varies according to SSP
    k_fe = Key("ldv fuel economy:n-t-y")
    c.apply(factor.insert, k_fe + "exo", name=k_fe.name, target=k_fe, dims="nty")

    # Reciprocal value, i.e. from  Gv km / GW a → GW a / Gv km
    k_eff = Key("ldv efficiency:t-y-n")
    c.add(k_eff, "div", genno.Quantity(1.0), k_fe)

    # Compute the input efficiency adjustment factor for the NAVIGATE project
    # TODO Move this to project-specific code
    k2 = Key("transport input factor:t-y")
    c.add(k2, "factor_input", "y", "t::transport", "t::transport agg", "config")

    # Product of NAVIGATE input factor and LDV efficiency
    c.add(k_eff + "adj+0", "mul", k2, k_eff)

    # Multiply by values from ldv-input-adj.csv. See file comment. Drop the 'scenario'
    # dimension; there is only one value in the file per 'n'.
    c.add("ldv input adj:n", "sum", exo.input_adj_ldv, dimensions=["scenario"])
    c.add(k_eff + "adj", "mul", k_eff + "adj+0", "ldv input adj:n")

    # Select a task for the final step that computes "ldv::ixmp"
    final = {
        "US-TIMES MA3T": (
            get_USTIMES_MA3T,
            "context",
            k_eff + "adj",
            "ldv inv_cost:n-t-y:exo",
            "ldv fix_cost:n-t-y:exo",
        ),
        None: (get_dummy, "context"),
    }.get(source)

    if final is None:
        raise ValueError(f"invalid source for non-LDV data: {source}")

    # Interpolate load factor
    lf_nsy = Key("load factor ldv:scenario-n-y")
    c.add(
        lf_nsy + "0",
        "interpolate",
        lf_nsy + "exo",
        "y::coords",
        kwargs=dict(fill_value="extrapolate"),
    )

    # Select load factor
    lf_ny = lf_nsy / "scenario"
    c.add(lf_ny + "0", "select", lf_nsy + "0", "indexers:scenario")

    # Insert a scaling factor that varies according to SSP
    c.apply(factor.insert, lf_ny + "0", name="ldv load factor", target=lf_ny)

    # Keys to be included in combined data
    keys = []

    t_ldv = "t::transport LDV"

    # Extend (forward fill) lifetime to cover all periods
    c.add(exo.lifetime_ldv + "0", "extend_y", exo.lifetime_ldv, "y", dim="yv")
    # Broadcast to all nodes
    c.add(
        "lifetime:nl-yv:ldv",
        "broadcast_n",
        exo.lifetime_ldv + "0",
        "n::ex world",
        dim="nl",
    )
    # Broadcast to all LDV technologies
    # TODO Use a named operator like genno.operator.expand_dims, instead of the method
    #      of the AttrSeries class
    c.add("lifetime:nl-t-yv:ldv", AttrSeries.expand_dims, "lifetime:nl-yv:ldv", t_ldv)
    # Convert to MESSAGE data structure
    keys.append(Key("technical_lifetime::ldv+ixmp"))
    c.add(
        keys[-1],
        "as_message_df",
        "lifetime:nl-t-yv:ldv",
        name=keys[-1].name,
        dims=dict(node_loc="nl", technology="t", year_vtg="yv"),
        common={},
    )

    # Add further keys for MESSAGE-structured data
    # Techno-economic attributes
    keys.append("ldv tech::ixmp")
    c.add(keys[-1], *final)
    # Usage
    keys.append("ldv usage::ixmp")
    c.add(keys[-1], usage_data, lf_ny, "cg", "n::ex world", t_ldv, "y::model")
    # Constraints
    keys.append("ldv constraints::ixmp")
    c.add(keys[-1], constraint_data, "context")
    # Capacity factor
    keys.append("ldv capacity_factor::ixmp")
    c.add(keys[-1], capacity_factor, exo.activity_ldv, t_ldv, "y", "broadcast:y-yv-ya")

    # Calculate base-period CAP_NEW and historical_new_capacity (‘sales’)
    if config.ldv_stock_method == "A":
        # Data from file ldv-new-capacity.csv
        try:
            k = Key(c.full_key("cap_new::ldv+exo"))
        except KeyError:
            pass  # No such file in this configuration
    elif config.ldv_stock_method == "B":
        k = c.apply(stock)

    kw: Dict[str, Any] = dict(
        dims=dict(node_loc="nl", technology="t", year_vtg="yv"), common={}
    )
    if k:
        # historical_new_capacity: select only data prior to y₀
        kw.update(name="historical_new_capacity")
        y_historical = list(filter(lambda y: y < info.y0, info.set["year"]))
        c.add(k + "1", "select", k, indexers=dict(yv=y_historical))
        keys.append(c.add("ldv hnc::ixmp", "as_message_df", k + "1", **kw))

        # CAP_NEW/bound_new_capacity_{lo,up}
        # - Select only data from y₀ and later.
        # - Discard values for ICE_conv.
        #   TODO Do not hard code this label; instead, identify the technology with the
        #   largest share and avoid setting constraints on it.
        # - Add both upper and lower constraints to ensure the solution contains exactly
        #   the given value.
        c.add(k + "2", "select", k, indexers=dict(yv=info.Y))
        c.add(k + "3", "select", k + "2", indexers=dict(t=["ICE_conv"]), inverse=True)
        for s in ("lo", "up"):
            kw.update(name=f"bound_new_capacity_{s}")
            keys.append(c.add(f"ldv bnc_{s}::ixmp", "as_message_df", k + "3", **kw))

    k_all = "transport ldv::ixmp"
    c.add(k_all, "merge_data", *keys)

    c.add("transport_data", __name__, key=k_all)


#: Input file containing structured data about LDV technologies.
#:
#: For R11, this data is from the US-TIMES and MA3T models.
FILE = "ldv-cost-efficiency.xlsx"

#: (parameter name, cell range, units) for data to be read from multiple sheets in the
#: :data:`FILE`.
TABLES = {
    "fuel economy": (slice("B3", "Q15"), "Gv km / (GW year)"),
    "inv_cost": (slice("B33", "Q45"), "USD / vehicle"),
    "fix_cost": (slice("B62", "Q74"), "USD / vehicle"),
}


@cached
def read_USTIMES_MA3T(nodes: List[str], subdir=None) -> Mapping[str, "AnyQuantity"]:
    """Read the US-TIMES MA3T data from :data:`FILE`.

    No transformation is performed.

    **NB** this function takes only simple arguments (`nodes` and `subdir`) so that
    :func:`.cached` computes the same key every time to avoid the slow step of opening/
    reading the large spreadsheet. :func:`get_USTIMES_MA3T` then conforms the data to
    particular context settings.
    """
    # Open workbook
    path = package_data_path("transport", subdir or "", FILE)
    wb = load_workbook(path, read_only=True, data_only=True)

    # Tables
    data = defaultdict(list)

    # Iterate over regions/nodes
    for node in map(str, nodes):
        # Worksheet for this region
        sheet_node = node.split("_")[-1].lower()
        sheet = wb[f"MESSAGE_LDV_{sheet_node}"]

        # Read tables for efficiency, investment, and fixed O&M cost
        # NB fix_cost varies by distance driven, thus this is the value for average
        #    driving.
        # TODO calculate the values for modest and frequent driving
        for par_name, (cells, _) in TABLES.items():
            df = pd.DataFrame(list(sheet[cells])).map(lambda c: c.value)

            # - Make the first row the headers.
            # - Drop extra columns.
            # - Use 'MESSAGE name' as the technology name.
            # - Melt to long format.
            # - Year as integer.
            # - Assign "node" and "unit" columns.
            # - Drop NA values (e.g. ICE_L_ptrp after the first year).
            data[par_name].append(
                df.iloc[1:, :]
                .set_axis(df.loc[0, :], axis=1)
                .drop(["Technology", "Description"], axis=1)
                .rename(columns={"MESSAGE name": "t"})
                .melt(id_vars=["t"], var_name="y")
                .astype({"y": int})
                .assign(n=node)
                .dropna(subset=["value"])
            )

    # Combine data frames, convert to Quantity
    qty = {}
    for par_name, dfs in data.items():
        qty[par_name] = genno.Quantity(
            pd.concat(dfs, ignore_index=True).set_index(["n", "t", "y"]),
            units=TABLES[par_name][1],
            name=par_name,
        )

    return qty


def get_USTIMES_MA3T(
    context, efficiency: "AnyQuantity", inv_cost: "AnyQuantity", fix_cost: "AnyQuantity"
) -> Dict[str, pd.DataFrame]:
    """Prepare LDV data from US-TIMES and MA3T.

    .. todo:: Some calculations are performed in the spreadsheet; transfer to code.
    .. todo:: Values for intermediate time periods e.g. 2025 are forward-filled from
       the next earlier period, e.g. 2020; interpolate instead.

    Returns
    -------
    dict of (str → pd.DataFrame)
        Data for the ``input``, ``output``, ``capacity_factor, ``technical_lifetime``,
        ``inv_cost``, and ``fix_cost`` parameters.
    """
    from message_ix_models.util import convert_units

    # Compatibility checks
    check_support(
        context,
        settings=dict(regions=frozenset(["R11", "R12", "R14"])),
        desc="US-TIMES and MA3T data available",
    )

    # Retrieve configuration and ScenarioInfo
    config: "Config" = context.transport
    info = config.base_model_info
    spec = config.spec

    # Merge with base model commodity information for io_units() below
    # TODO this duplicates code in .ikarus; move to a common location
    all_info = ScenarioInfo()
    all_info.set["commodity"].extend(get_codes("commodity"))
    all_info.update(spec.add)

    # Retrieve the input data
    data = dict(efficiency=efficiency, inv_cost=inv_cost, fix_cost=fix_cost)

    # Years to include
    # FIXME Avoid hard-coding this period
    target_years = list(filter(lambda y: 1995 <= y, info.set["year"]))
    # Extend over missing periods in the model horizon
    data = {name: extend_y(qty, target_years) for name, qty in data.items()}

    # Prepare "input" and "output" parameter data from `efficiency`
    name = "efficiency"
    base = data.pop(name).to_series().rename("value").reset_index()

    common = dict(mode="all", time="year", time_dest="year", time_origin="year")

    i_o = make_io(
        src=(None, None, f"{efficiency.units:~}"),
        dest=(None, "useful", "Gv km"),
        efficiency=base["value"],
        on="input",
        node_loc=base["n"],  # Other dimensions
        technology=base["t"].astype(str),
        year_vtg=base["y"],
        **common,
    )

    # Assign input commodity and level according to the technology
    result = {}
    result["input"] = (
        input_commodity_level(context, i_o["input"], default_level="final")
        .pipe(broadcast, year_act=info.Y)
        .query("year_act >= year_vtg")
        .pipe(same_node)
    )

    # Convert units to the model's preferred input units for each commodity
    @lru_cache
    def _io_units(t, c, l):  # noqa: E741
        return all_info.io_units(t, c, l)

    target_units = (
        result["input"]
        .apply(
            lambda row: _io_units(row["technology"], row["commodity"], row["level"]),
            axis=1,
        )
        .unique()
    )
    assert 1 == len(target_units)

    result["input"]["value"] = convert_units(
        result["input"]["value"],
        {"value": (1.0, f"{efficiency.units:~}", target_units[0])},
    )

    # Assign output commodity based on the technology name
    result["output"] = (
        i_o["output"]
        .assign(commodity=lambda df: "transport vehicle " + df["technology"])
        .pipe(broadcast, year_act=info.Y)
        .query("year_act >= year_vtg")
        .pipe(same_node)
    )

    # Transform costs
    for name in "fix_cost", "inv_cost":
        base = data[name].to_series().reset_index()
        result[name] = make_df(
            name,
            node_loc=base["n"],
            technology=base["t"],
            year_vtg=base["y"],
            value=base[name],
            unit=f"{data[name].units:~}",
        )
    result["fix_cost"] = (
        result["fix_cost"]
        .pipe(broadcast, year_act=info.Y)
        .query("year_act >= year_vtg")
    )

    # Compute CO₂ emissions factors
    result.update(ef_for_input(context, result["input"], species="CO2"))

    return result


def get_dummy(context) -> Dict[str, pd.DataFrame]:
    """Generate dummy, equal-cost output for each LDV technology."""
    # Information about the target structure
    config: "Config" = context.transport
    info = config.base_model_info

    # List of years to include
    years = list(filter(lambda y: y >= 2010, info.set["year"]))

    # List of LDV technologies
    all_techs = config.spec.add.set["technology"]
    ldv_techs = list(map(str, all_techs[all_techs.index("LDV")].child))

    # 'output' parameter values: all 1.0 (ACT units == output units)
    # - Broadcast across nodes.
    # - Broadcast across LDV technologies.
    # - Add commodity ID based on technology ID.
    output = (
        make_df(
            "output",
            value=1.0,
            year_act=years,
            year_vtg=years,
            unit="Gv km",
            level="useful",
            mode="all",
            time="year",
            time_dest="year",
        )
        .pipe(broadcast, node_loc=info.N[1:], technology=ldv_techs)
        .assign(commodity=lambda df: "transport vehicle " + df["technology"])
        .pipe(same_node)
    )

    # Discard rows for the historical LDV technology beyond 2010
    output = output[~output.eval("technology == 'ICE_L_ptrp' and year_vtg > 2010")]

    # Add matching data for 'capacity_factor' and 'var_cost'
    data = make_matched_dfs(output, capacity_factor=1.0, var_cost=1.0)
    data["output"] = output

    return data


@minimum_version("message_ix 3.6")
def capacity_factor(
    qty: "AnyQuantity", t_ldv: dict, y, y_broadcast: "AnyQuantity"
) -> Dict[str, pd.DataFrame]:
    """Return capacity factor data for LDVs.

    The data are:

    - Broadcast across all |yV|, |yA| (`broadcast_y`), and LDV technologies (`t_ldv`).
    - Converted to :mod:`message_ix` parameter format using :func:`.as_message_df`.

    Parameters
    ----------
    qty
        Input data, for instance from file :`ldv-activity.csv`, with dimension |n|.
    broadcast_y
        The structure :py:`"broadcast:y-yv-va"`.
    t_ldv
        The structure :py:`"t::transport LDV"`, mapping the key "t" to the list of LDV
        technologies.
    y
        All periods, including pre-model periods.
    """
    from genno.operator import convert_units

    try:
        from message_ix.report.operator import as_message_df
    except ImportError:
        from message_ix.reporting.computations import as_message_df

    # TODO determine units from technology annotations
    data = convert_units(qty.expand_dims(y=y) * y_broadcast, "Mm / year")

    name = "capacity_factor"
    dims = dict(node_loc="n", year_vtg="yv", year_act="ya")
    # TODO Remove typing exclusion once message_ix is updated for genno 1.25
    result = as_message_df(data, name, dims, dict(time="year"))  # type: ignore [arg-type]

    result[name] = result[name].pipe(broadcast, technology=t_ldv["t"])

    return result


def constraint_data(context) -> Dict[str, pd.DataFrame]:
    """Return constraints on light-duty vehicle technology activity and usage.

    Responds to the :attr:`.Config.constraint` key :py:`"LDV growth_activity"`; see
    description there.
    """
    config: "Config" = context.transport

    # Information about the target structure
    info = config.base_model_info
    years = info.Y[1:]

    # Technologies as a hierarchical code list
    techs = config.spec.add.set["technology"]
    ldv_techs = techs[techs.index("LDV")].child

    # All technologies in the spec, as strings
    all_techs = list(map(str, techs))

    # List of technologies to constrain, including the LDV technologies, plus the
    # corresponding "X usage by CG" pseudo-technologies
    constrained: List[Code] = []
    for t in map(str, ldv_techs):
        constrained.extend(filter(lambda _t: t in _t, all_techs))  # type: ignore

    data: Dict[str, pd.DataFrame] = dict()
    for bound in "lo", "up":
        name = f"growth_activity_{bound}"

        # Retrieve the constraint value from configuration
        value = config.constraint[f"LDV {name}"]

        # Assemble the data
        data[name] = make_df(
            name, value=value, year_act=years, time="year", unit="-"
        ).pipe(broadcast, node_loc=info.N[1:], technology=constrained)

        if bound == "lo":
            continue

        # Add initial_activity_up values allowing usage to begin in any period
        name = f"initial_activity_{bound}"
        data[name] = make_df(
            name, value=1e6, year_act=years, time="year", unit="-"
        ).pipe(broadcast, node_loc=info.N[1:], technology=constrained)

    # Prevent new capacity from being constructed for techs annotated
    # "historical-only: True"
    historical_only_techs = list(
        filter(lambda t: t.eval_annotation("historical-only") is True, techs)
    )
    name = "bound_new_capacity_up"
    data[name] = make_df(name, year_vtg=info.Y, value=0.0, unit="-").pipe(
        broadcast, node_loc=info.N[1:], technology=historical_only_techs
    )

    return data


def stock(c: Computer) -> Key:
    """Prepare `c` to compute base-period stock and historical sales."""
    from .key import ldv_ny

    k = KeySeq("stock:n-y:ldv")

    # - Divide total LDV activity by (1) annual driving distance per vehicle and (2)
    #   load factor (occupancy) to obtain implied stock.
    # - Correct units: "load factor ldv:n-y" is dimensionless, should be
    #   passenger/vehicle
    # - Select only the base-period value.
    c.add(k[0], "div", ldv_ny + "total", exo.activity_ldv)
    c.add(k[1], "div", k[0], "load factor ldv:n-y")
    c.add(k[2], "div", k[1], genno.Quantity(1.0, units="passenger / vehicle"))
    c.add(k[3] / "y", "select", k[2], "y0::coord")

    # Multiply by exogenous technology shares to obtain stock with (n, t) dimensions
    c.add("stock:n-t:ldv", "mul", k[3] / "y", exo.t_share_ldv)

    # TODO Move the following 4 calls to .build.add_structure() or similar
    # Identify the subset of periods up to and including y0
    c.add(
        "y::to y0",
        lambda periods, y0: dict(y=list(filter(lambda y: y <= y0, periods))),
        "y",
        "y0",
    )
    # Convert duration_period to Quantity
    c.add("duration_period:y", "duration_period", "info")
    # Duration_period up to and including y0
    c.add("duration_period:y:to y0", "select", "duration_period:y", "y::to y0")
    # Groups for aggregating annual to period data
    c.add("y::annual agg", "groups_y_annual", "duration_period:y")

    # Fraction of sales in preceding years (annual, not MESSAGE 'year' referring to
    # multi-year periods)
    c.add("sales fraction:n-t-y:ldv", "sales_fraction_annual", exo.age_ldv)
    # Absolute sales in preceding years
    c.add("sales:n-t-y:ldv+annual", "mul", "stock:n-t:ldv", "sales fraction:n-t-y:ldv")
    # Aggregate to model periods; total sales across the period
    c.add(
        "sales:n-t-y:ldv+total",
        "aggregate",
        "sales:n-t-y:ldv+annual",
        "y::annual agg",
        keep=False,
    )
    # Divide by duration_period for the equivalent of CAP_NEW/historical_new_capacity
    c.add("sales:n-t-y:ldv", "div", "sales:n-t-y:ldv+total", "duration_period:y")

    # Rename dimensions to match those expected in prepare_computer(), above
    k = Key("sales:nl-t-yv:ldv")
    c.add(k, "rename_dims", "sales:n-t-y:ldv", name_dict={"n": "nl", "y": "yv"})

    return k


def usage_data(
    load_factor: "AnyQuantity",
    cg: List["Code"],
    nodes: List[str],
    t_ldv: Mapping[str, List],
    years: List,
) -> Mapping[str, pd.DataFrame]:
    """Generate data for LDV usage technologies.

    These technologies convert commodities like "transport ELC_100 vehicle" (i.e.
    vehicle-distance traveled) into "transport pax RUEAM" (i.e. passenger-distance
    traveled). These data incorporate:

    1. Load factor, in the ``output`` efficiency.
    2. Required consumption of a "disutility" commodity, in ``input``.
    """
    from .structure import TEMPLATE

    info = ScenarioInfo(set={"node": nodes, "year": years})

    # Regenerate the Spec for the disutility formulation
    spec = disutility.get_spec(
        groups=cg,
        technologies=t_ldv["t"],
        template=TEMPLATE,
    )

    data = disutility.data_conversion(info, spec)

    # Apply load factor
    cols = list(data["output"].columns[:-2])
    unit = data["output"]["unit"].unique()[0]
    rename = cast(Mapping, {"n": "node_loc", "y": "year_act"})
    data["output"] = (
        (
            genno.Quantity(data["output"].set_index(cols)["value"])
            * load_factor.rename(rename)
        )
        .to_dataframe()
        .reset_index()
        .assign(unit=unit)
    )

    # Add a source that produces the "disutility" commodity
    merge_data(data, disutility.data_source(info, spec))

    return data
