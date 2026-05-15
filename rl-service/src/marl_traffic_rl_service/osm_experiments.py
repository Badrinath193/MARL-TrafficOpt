from __future__ import annotations

from datetime import datetime, timezone

from .experiments import aggregate_runs, persist_experiment_bundle
from .osm_runner import run_imported_osm_fixed_time, run_imported_osm_max_pressure, run_imported_osm_smoke
from .scenarios import get_scenario, scenario_to_dict


DEFAULT_IMPORTED_CONTROLLERS = ["osm_open_loop", "osm_fixed_time", "osm_max_pressure"]
DEFAULT_IMPORTED_SEEDS = [1, 2, 3]


def run_imported_osm_experiment(
    scenario_id: str,
    controllers: list[str] | None = None,
    seeds: list[int] | None = None,
    end_time: int = 300,
    period: int = 8,
) -> dict:
    try:
        scenario = get_scenario(scenario_id)
    except ValueError as error:
        return {"ok": False, "error": str(error)}
    if scenario.source != "osm-import":
        return {
            "ok": False,
            "skipped": True,
            "reason": "Imported OSM experiments require an imported OSM scenario.",
            "scenario": scenario.scenario_id,
            "scenario_id": scenario.scenario_id,
            "scenario_spec": scenario_to_dict(scenario),
        }

    controllers = controllers or DEFAULT_IMPORTED_CONTROLLERS
    seeds = seeds or DEFAULT_IMPORTED_SEEDS
    runs = []

    for controller in controllers:
        for seed in seeds:
            if controller == "osm_open_loop":
                run = run_imported_osm_smoke(
                    scenario_id=scenario.scenario_id,
                    seed=int(seed),
                    end_time=end_time,
                    period=period,
                    persist=True,
                )
            elif controller == "osm_fixed_time":
                run = run_imported_osm_fixed_time(
                    scenario_id=scenario.scenario_id,
                    seed=int(seed),
                    end_time=end_time,
                    period=period,
                    persist=True,
                )
            elif controller == "osm_max_pressure":
                run = run_imported_osm_max_pressure(
                    scenario_id=scenario.scenario_id,
                    seed=int(seed),
                    end_time=end_time,
                    period=period,
                    persist=True,
                )
            else:
                run = {
                    "ok": False,
                    "skipped": False,
                    "error": f"Unknown imported OSM controller '{controller}'.",
                    "scenario": scenario.scenario_id,
                    "scenario_id": scenario.scenario_id,
                    "controller": {"name": controller},
                    "seed": seed,
                }
            runs.append(run)

    bundle = {
        "ok": all(run.get("ok") for run in runs),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario.scenario_id,
        "scenario_id": scenario.scenario_id,
        "scenario_spec": scenario_to_dict(scenario),
        "experiment_type": "imported_osm_controller_comparison",
        "controllers": controllers,
        "seeds": seeds,
        "end_time": end_time,
        "period": period,
        "runs": runs,
        "aggregate": aggregate_runs(runs),
        "limitations": [
            "Imported OSM demand is generated with randomTrips.py and is not calibrated.",
            "MaxPressure does not yet synthesize yellow transitions for arbitrary imported programs.",
            "Use as engineering comparison, not a publication benchmark.",
        ],
    }
    return persist_experiment_bundle(bundle)
