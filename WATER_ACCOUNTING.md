# Water Accounting

Canonical balance:

`change_in_storage = total_inflow - total_outflow`

For consumptive use:

`consumptive_use = withdrawal - return_flow - storage_change`

Cooling-tower make-up is modeled as:

`makeup = evaporation + drift + blowdown + leakage + storage_change`

When cycles of concentration are available:

`blowdown = evaporation / (cycles_of_concentration - 1) - drift`

AquaStat keeps withdrawal, consumption, discharge, potable water, reclaimed water, and indirect electricity-related water separate.
