2 Conversion Technologies
====
2.1 	Variables
----
Energy conversion technologies are modelled using two types of variables, that represent
– the amount of energy converted per year in a period (activity  variables) and
– the capacity installed annually in a period (capacity variables).

2.1.1 	Activities  of Energy Conversion Technologies
~~~~~~~~~~~~~~~~~~~~~~

:math:`zsvd.elt`

where

:math:`z`	 is the level identifier of the main output of the technology.

:math:`z = U`  identifies the end-use level. This level is handled differently to all other levels: It has to be the demand level and technologies with the main output on this level are defined without load regions.

:math:`s`	 is the main energy input of the technology (supply). If the technology has no input :math:`s` is set to ”.” (e.g., solar technologies),

:math:`v`	 additional identifier of the conversion technology (used to distinguish technologies with the same input and output),
:math:`d`	 is the main energy output of the technology (demand),

:math:`e`	 is the level of reduction of demand due to own-price elasticities of demands (does only occur on the demand level; otherwise or if this demand has no elasticities :math:`e = ”.”`),

:math:`t`	 identifies the period, :math:`t ∈ {a, b, c, ...}`.

The activity variable of an energy conversion technology is an energy flow variable. It represents the annual consumption of this technology of the main input per period. If a technology has no input, the variable represents the annual production of the main output.
 
If the level of the main output is not U and at least one of the energy carriers consumed or supplied is defined with load regions the technology is defined with load regions. In this case the activity variables are generated separately for each load region, which is indicated by the additional identifier l in position 7. However, this can be changed by fixing the production of the technology over the load regions to a predefined pattern (see section 9.4): one variable is generated for all load regions, the distribution to the load regions is given by the definition of the user (e.g., production pattern of solar power-plants).

If the model is formulated with demand elasticities  (see section 9.10), the activity variables of technologies with a demand  as main output that is defined with elasticity are generated for each elasticity class (identifier :math:`e` in position 6).

2.1.2 	Capacities of Energy Conversion Technologies
~~~~~~~~~~~~~~~~~~~~~~
:math:`Y zsvd..t`, 

where

:math:`Y`	is the identifier for capacity variables.

:math:`z`	identifies the level on that the main energy output of the technology is defined,

:math:`s`	is the identifier of the main energy input of the technology,

:math:`v`	additional identifier of the conversion technology,

:math:`d`	is the identifier of the main energy output of the technology, and

:math:`t`	is the period in that the capacity goes into operation.

The capacity variables are power variables. Technologies can be modelled without capacity variables. In this case no capacity constraints and no dynamic constraints on construction can be included in the model. Capacity variables of energy conversion technologies can be defined  as integer variables, if the solution algorithm has a mixed integer option.

If a capacity variable is continuous it represents the annual new installations of the technology in period :math:`t`, if it is integer it represents either the annual number of installations of a certain size or the number of installations of :math:`1/∆t` times the unit size (depending  on the definition; :math:`∆t` is the length of period :math:`t` in years).

The capacity is defined in relation to the main output of the technology.

2.2 	Constraints
~~~~~~~~~~~~~~~~~~~~~~
The rows used to model energy conversion technologies limit
– the utilization of a technology in relation to the capacity actually installed (capacity constraint) and
– the activity or construction of a technology in a period in relation to the same variable in the previous period (dynamic constraints).
 
2.2.1 	Capacity Constraints
~~~~~~~~~~~~~~~~~~~~~~

:math:`C zsvd.lt`, 

where

:math:`C`	is the identifier for capacity constraints,

:math:`z`	identifies the level on that the main energy output of the technology is defined,

:math:`s`	is the identifier of the main energy input of the technology,

:math:`v`	additional identifier of the conversion technology,

:math:`d`	is the identifier of the main energy output of the technology,

:math:`l`	identifies the load region, :math:`l ∈ {1, 2, 3, ...} or l = ”.”`, if the technology is not modelled with load regions, and

:math:`t`	is the period in that the capacity goes into operation.

For all conversion technologies modelled with capacity variables the capacity constraints will be generated automatically. If the activity variables exist for each load region separately there will be one capacity constraint per load region (see also section 9.4). If the technology is an end-use technology the sum over the elasticity classes will be included in the capacity constraint.

Additionally  the activity variables of different technologies can be linked to the same capacity variable, which allows to leave the choice of the activity variable used with a given capacity to the optimization (see section 9.7).

**Technologies without Load Regions**

For technologies without load regions (i.e. technologies, where no input or output is modelled with load regions) the production is related to the total installed capacity by the plant factor. For these technologies the plant factor has to be given as the fraction they actually operate per year. All end-use technologies (technologies  with main output level ”U ”) are modelled in this way.

:math:`Esvd   × zsvd...t − min(t,κsvd ) τ =t−τsvd ∆(τ − 1) × πsvd  × fi × Y zsvd..τ ≤ hct × πsvd`
 
**Technologies with Varying Inputs and Outputs**

Many types of energy conversion technologies do not have fix relations between their inputs and outputs. MESSAGE has the option to link several activity variables of conversion technologies into one capacity constraint. For the additional activities linked to a capacity variable a coefficient defines the maximum power available in relation to one power unit of the main activity.

In the following this constraint is only described for technologies without load regions; the other types are constructed in analogy (see also section 9.7).

:math:`relsvd
 
σv/ δ
 
σv/ δ  × Eσv/ δ  × zσv δ...t −

 
min(t,κsvd )

τ =t−τsvd
 

∆(τ − 1) × πsvd  × fi × Y zsvd..τ ≤ hct
 

× πsvd` ,
 

The following notation is used in the above equations:
 
:math:`zsvd..lt`	is the activity of conversion technology :math:`v` in period :math:`t` and, if defined so, load region :math:`l` (see section 2.1.1),
:math:`Y zsvd..t`	is the capacity variable of conversion technology :math:`v` (see section 2.1.2).
:math:`Esvd`	is the efficiency of technology :math:`v` in converting the main energy input, :math:`s`, into the main energy output, :math:`d`,
:math:`κsvd` is the last period in that technology :math:`v` can be constructed,
:math:`πsvd`	is the "plant factor" of technology :math:`v`, having different meaning depending on the type of capacity equation applied,
:math:`∆τ` 	is the length of period :math:`τ` in years,
:math:`τsvd` 	is the plant life of technology :math:`v` in periods,
 
:math:`t svd`
 
represents the installations built before the time horizon under consideration,
that are still in operation in the first year of period :math:`t`,
 
:math:`fi` 	is 1. if the capacity variable is continuous, and represents the minimum installed capacity per year (unit size) if the variable is integer,
:math:`lm` 	is the load region with maximum capacity use if the production pattern over the year is fixed,
:math:`π(lm, svd)`  is the share of output in the load region with maximum production,
:math:`σv/ δ`	is the relative capacity of main output of technology (or operation mode) svd to the capacity of main output of the alternative technology (or operation
:math:`mode)σv δ`,
:math:`λl` 	is the length of load region :math:`l` as fraction of the year, and
:math:`λlm` 	is the length of load region :math:`lm`, the load region with maximum capacity requirements, as fraction of the year.



2.2.2 	Upper Dynamic Constraints on Construction Variables
~~~~~~~~~~~~~~~~~~~~~~

M Y zsvd.t


The dynamic capacity constraints relate the amount of annual new installations of a technology in a period to the annual construction during the previous period.

Y zsvd..t − γyo
 
× Y zsvd..(t − 1) ≤ gyo	,
 
where
o svd,t o svd,t
 

is the maximum growth rate per period for the construction of technology v, is the initial  size (increment) that can be given for the introduction of new technologies,
 
Y zsvd..t	is the annual new installation of technology v in period t.

2.2.3 	Lower Dynamic Constraints on Construction Variables
~~~~~~~~~~~~~~~~~~~~~~
LY zsvd.t
 
Y zsvd..t − γysvd,t   × Y zsvd..(t − 1) ≥ − gysvd,t,

where
γysvd,t 	is the minimum growth rate per period for the construction of technologyv, gysvd,t	is the ”last”  size (decrement) allowing technologies to go out of the market, and Y zsvd..t	is the annual new installation of technology v in periodt.


2.2.4 	Upper Dynamic Constraints on Activity Variables
~~~~~~~~~~~~~~~~~~~~~~
M zsvd..t

The dynamic production constraints relate the production of a technology in one period to the production in the previous period. If the technology is defined with load regions, the sum over the load regions is included in the constraint.

Esvd   × \ zsvd..lt  − γao
l
 
× zsvd..l(t − 1) l ≤ gao	,
 

where
o svd,t
 o svd,t
 
are the maximum growth rate and increment as described  in section
 
2.2.2 (the increment is to be given in units of main output), and
zsvd..lt	is the activity of technology v in load region l.


If demand elasticities are modelled, the required sums are included for end-use technologies.


2.2.5 	Lower Dynamic Constraints on Activity Variables
~~~~~~~~~~~~~~~~~~~~~~
Lzsvd..t

Esvd   × [ zsvd..lt  − γasvd,t  × zsvd..l(t − 1) ]  ≥ − gasvd,t,
l

where
γasvd,t 	and gasvd,t are the maximum growth rate and increment as described  in section 2.2.3, and zsvd..lt	is the activity of technology v in load region *l*.

