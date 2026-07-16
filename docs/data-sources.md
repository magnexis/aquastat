# Data Sources

## Open-Meteo

- Provider: Open-Meteo
- Data type: current weather signals including temperature and relative humidity
- Integration: HTTP API
- Update frequency: live/current endpoint
- Cache duration: 15 minutes by default
- Failure behavior: falls back to seasonal baselines or cached telemetry paths depending on endpoint
- Limitations: modeled weather source, not guaranteed ground-truth sensor data

## Electricity Maps / Grid Signals

- Provider: Electricity Maps or compatible regional grid feeds
- Data type: carbon intensity and grid load factors
- Integration: planned/optional API key-backed integration
- Cache duration: cached telemetry state
- Failure behavior: fallback baselines

## WRI / Hydrological Risk Data

- Provider: World Resources Institute Aqueduct data
- Data type: water stress scoring
- Integration: seeded score/model path today, GIS-ready schema for deeper spatial joins
- Limitations: not currently a live upstream call in the request path
