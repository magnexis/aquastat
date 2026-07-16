use wasm_bindgen::prelude::*;

const MIN_RH: f64 = 5.0;
const MAX_RH: f64 = 99.0;
const MIN_TEMP_C: f64 = -20.0;
const MAX_TEMP_C: f64 = 50.0;

#[wasm_bindgen]
pub fn calculate_wet_bulb_temp(dry_bulb_temp: f64, relative_humidity: f64) -> f64 {
    if relative_humidity < MIN_RH {
        return round2(dry_bulb_temp);
    }

    let t = dry_bulb_temp.clamp(MIN_TEMP_C, MAX_TEMP_C);
    let rh = relative_humidity.clamp(MIN_RH, MAX_RH);

    let twb = t * (0.151977 * (rh + 8.313659).sqrt()).atan()
        + (t + rh).atan()
        - (rh - 1.676331).atan()
        + 0.00391838 * rh.powf(1.5) * (0.023101 * rh).atan()
        - 4.686035;

    round2(twb)
}

#[wasm_bindgen]
pub fn estimate_instant_wue(base_wue: f64, wet_bulb_temp: f64, cooling_profile: &str) -> f64 {
    let gamma = match cooling_profile {
        "DIRECT_EVAPORATIVE" => 1.5,
        "ADIABATIC_HYBRID" => 0.8,
        "CLOSED_LOOP" => 0.1,
        _ => 1.0,
    };

    let severity = ((wet_bulb_temp - 15.0) / 15.0).max(0.0);
    round3(base_wue * (1.0 + severity * gamma))
}

fn round2(value: f64) -> f64 {
    (value * 100.0).round() / 100.0
}

fn round3(value: f64) -> f64 {
    (value * 1000.0).round() / 1000.0
}
