# Formulas

## Wet-Bulb Temperature

AquaStat uses a bounded Stull-based wet-bulb calculation with a psychrometric refinement loop.

## Dynamic WUE

`dynamic_wue = base_wue * (1 + severity * cooling_multiplier)`

Where:

- `severity = max(0, (wet_bulb - 15C) / 15C)`
- cooling multiplier depends on the cooling profile

## Cooling-Tower Water

- `latent_heat_kj_per_kg = 2501 - 2.361 * water_temp_c`
- `evaporation_lph = heat_load_kw / latent_heat_kj_per_kg * 3600`
- `blowdown = evaporation / (cycles_of_concentration - 1) - drift`
- `makeup = evaporation + drift + blowdown + leakage + storage_change`
