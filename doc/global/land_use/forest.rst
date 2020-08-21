.. _forestry:

Forestry
--------

The forestry sector is represented in GLOBIOM with five categories of primary products (pulp logs, saw logs, biomass for energy, traditional fuel wood, and other industrial logs) which are consumed by industrial energy, 
cooking fuel demand, or processed and sold on the market as final products (wood pulp and sawnwood). These products are supplied from managed forests and short rotation plantations. Harvesting cost and mean annual 
increments are informed by the G4M global forestry model (Kindermann et al., 2006 :cite:`kindermann_predicting_2006`) which in turn calculates them based on thinning strategies and length of the rotation period.

Primary forest production from traditional managed forests is characterized also at the level of SimUs. The most important parameters for the model are mean annual increment, maximum share of saw logs in the mean annual 
increment, and harvesting cost. These parameters are shared with the G4M model – a successor of the model described by Kindermann et al. (2006) :cite:`kindermann_predicting_2006`. More specifically, mean annual increment 
for the current management, is obtained by downscaling biomass stock data from the Global Forest Resources Assessment (FAO, 2006 :cite:`FAO_global_2006`) from the country level to a 0.5 x 0.5 degree grid using the method 
described in Kindermann et al. (2008) :cite:`kindermann_global_forest_2008`. The downscaled biomass stock data is subsequently used to parameterize increment curves. Finally, the saw logs share is estimated by the tree size, 
which in turn depends on yield and rotation time. Harvesting costs are adjusted for slope and tree size as well. 
Among the five primary forest products, saw logs, pulp logs and biomass for energy are further processed. Sawn wood and wood pulp production and demand parameters rely on the 4DSM model described in 
Rametsteiner et al. (2007) :cite:`rametsteiner_study_2007`. FAO data and other secondary sources have been used for quantities and prices of sawn wood and wood pulp. For processing cost estimates of these products an internal 
IIASA database and proprietary data (e.g. RISI database for locations of individual pulp and paper mills, with additional economic and technical information, http://www.risiinfo.com) were used. Biomass for energy can be converted 
in several processes: combined heat and power production, fermentation for ethanol, heat, power and gas production, and gasification for methanol and heat production. Processing cost and conversion coefficients are obtained from 
various sources (Biomass Technology Group, 2005 :cite:`biomass_handbook_2005`; Hamelinck and Faaij, 2001 :cite:`hamelinck_future_2001`; Leduc et al., 2008 :cite:`leduc_optimal_2008`; Sorensen, 2005 :cite:`sorensen_economies_2005`). 
Demand for woody bioenergy production is implemented through minimum quantity constraints, similar to demand for other industrial logs and for firewood.
Woody biomass for bioenergy can also be produced on short rotation tree plantations. To parameterize this land use type in terms of yields, an evaluation of the land availability and suitability was carried out. 
Calculated plantation costs involve the establishment cost and the harvesting cost. The establishment related capital cost includes only sapling cost for manual planting 
(Carpentieri et al., 1993 :cite:`carpentieri_future_1993`; Herzogbaum GmbH, 2008 :cite:`herzogbaum_forstpflanzen_2008`). Labour requirements for plantation establishment are based on Jurvelius (1997) :cite:`jurvelius_labor_1997`, 
and consider land preparation, saplings transport, planting and fertilization. These labour requirements are adjusted for temperate and boreal regions to take into account the different site conditions. 
The average wages for planting are obtained from ILO (2007) :cite:`ILO_occupational_2007`. 
Harvesting cost includes logging and timber extraction. The unit cost of harvesting equipment and labour is derived from various datasets for Europe and North America 
(e.g. FPP, 1999 :cite:`FPP_holzernte_1999`; Jiroušek et al., 2007 :cite:`jiroušek_productivity_2007` ; Stokes et al., 1986 :cite:`stokes_field_1986` ; Wang et al., 2004 :cite:`wang_productivity_2004`). 
Because the productivity of harvesting equipment depends on terrain conditions, a slope factor (Hartsough et al., 2001 :cite:`hartsough_harvesting_2001`) was integrated to estimate total harvesting cost. 
The labour cost, as well as the cost of saplings, is regionally adjusted by the ratio of mean PPP (purchasing power parity over GDP), (Heston et al., 2006 :cite:`heston_penn_2006`).
