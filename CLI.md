# CLI

AquaStat now ships with a first-party CLI entry point:

```bash
aquastat --help
```

The CLI is designed for fast operational use rather than full-screen TUI behavior. It supports:

- service status checks
- public API metadata inspection
- supported region listing
- estimate lookups
- facility listing
- facility inspection
- workload routing comparisons
- human-readable output
- JSON output for scripting

## Installation

From the repository:

```bash
pip install -e .[dev]
```

The installed command is:

```bash
aquastat
```

## Configuration

The CLI reads:

- `AQUASTAT_BASE_URL`
- `AQUASTAT_API_KEY`

You can also pass:

```bash
aquastat --base-url https://aquastat-api.onrender.com --api-key aq_live_example status
```

## Commands

### Status

```bash
aquastat status
aquastat info
```

### Regions

```bash
aquastat regions
```

### Estimate

```bash
aquastat estimate --provider aws --region us-east-1 --load-mw 2.5
```

### Facilities

```bash
aquastat facilities --query ashburn --limit 5
aquastat facility fac_syn_ashburn
```

### Route workload

```bash
aquastat route-workload \
  --job-duration-hours 4 \
  --compute-demand-mwh 12.5 \
  --candidate-region aws:us-east-1 \
  --candidate-region aws:eu-west-1 \
  --candidate-region gcp:asia-southeast1
```

### JSON output

```bash
aquastat --json estimate --provider aws --region us-east-1
```

## Existing utility scripts

The older script utilities still exist where they remain useful:

- `python scripts/generate_api_key.py`
- `python scripts/generate_openapi.py`
- `python scripts/ingest_worker.py`
