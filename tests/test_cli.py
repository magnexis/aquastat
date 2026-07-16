from aquastat_cli import main as cli_main


def _fake_request_json(_ctx, method: str, path: str, *, params=None, json_body=None):
    if method == "GET" and path == "/api/v1/status":
        return {
            "name": "AquaStat API",
            "version": "1.1.0",
            "documentation": "/docs",
            "openapi": "/openapi.json",
            "health": "/health",
        }
    if method == "GET" and path == "/api/v1/estimate":
        return {
            "datacenter": {"provider": "AWS", "region_slug": "us-east-1", "cooling_type": "DIRECT_EVAPORATIVE"},
            "weather_snapshot": {"calculated_wet_bulb_temp_c": 24.8, "relative_humidity_pct": 62.0},
            "water_metrics": {
                "estimated_it_load_mw": params["load_mw"],
                "calculated_instant_wue": 2.97,
                "water_consumption_liters_per_hour": 148500.0,
                "water_consumption_gallons_per_hour": 39229.5,
                "equivalent_household_daily_water_usage": 130.7,
            },
        }
    if method == "POST" and path == "/api/v1/route-workload":
        return {
            "optimal_region": "aws:eu-west-1",
            "explanation": "Lower wet-bulb temperature and lower carbon intensity.",
            "routing_matrix": [
                {
                    "region": "aws:eu-west-1",
                    "projected_water_liters": 15600.0,
                    "projected_carbon_g": 2250000.0,
                    "water_stress_adjusted_impact_score": 15600.0,
                }
            ],
        }
    raise AssertionError(f"Unexpected request: {method} {path}")


def test_cli_status_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_main, "request_json", _fake_request_json)
    exit_code = cli_main.main(["--json", "--base-url", "http://testserver", "status"])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert '"version"' in output
    assert '"documentation"' in output


def test_cli_estimate_human_output(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_main, "request_json", _fake_request_json)
    exit_code = cli_main.main(
        [
            "--base-url",
            "http://testserver",
            "estimate",
            "--provider",
            "aws",
            "--region",
            "us-east-1",
            "--load-mw",
            "2.5",
        ]
    )
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "AquaStat :: Estimate" in output
    assert "Water / hour" in output


def test_cli_route_workload_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_main, "request_json", _fake_request_json)
    exit_code = cli_main.main(
        [
            "--json",
            "--base-url",
            "http://testserver",
            "route-workload",
            "--job-duration-hours",
            "4",
            "--compute-demand-mwh",
            "12.5",
            "--candidate-region",
            "aws:us-east-1",
            "--candidate-region",
            "aws:eu-west-1",
        ]
    )
    assert exit_code == 0
    output = capsys.readouterr().out
    assert '"optimal_region"' in output
