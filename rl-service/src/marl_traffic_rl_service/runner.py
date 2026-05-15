from __future__ import annotations

from datetime import datetime, timezone

from .experiments import aggregate_runs, persist_experiment_bundle
from .scenarios import get_scenario, scenario_to_dict
from .sumo import run_one_intersection_traci_baseline


DEFAULT_CONTROLLERS = ["fixed_time", "actuated", "max_pressure"]
DEFAULT_SEEDS = [1, 2, 3]


def run_multi_seed_experiment(
    controllers: list[str] | None = None,
    seeds: list[int] | None = None,
    demand_profile: str | None = None,
    scenario_id: str | None = None,
) -> dict:
    controllers = controllers or DEFAULT_CONTROLLERS
    seeds = seeds or DEFAULT_SEEDS
    scenario = get_scenario(scenario_id)
    demand_profile = demand_profile or scenario.demand_profile
    runs = []

    for controller in controllers:
        for seed in seeds:
            run = run_one_intersection_traci_baseline(
                controller,
                persist=True,
                seed=int(seed),
                demand_profile=demand_profile,
                scenario_id=scenario.scenario_id,
            )
            runs.append(run)

    bundle = {
        "ok": all(run.get("ok") for run in runs),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario.scenario_id,
        "scenario_id": scenario.scenario_id,
        "scenario_spec": scenario_to_dict(scenario),
        "demand_profile": demand_profile,
        "controllers": controllers,
        "seeds": seeds,
        "runs": runs,
        "aggregate": aggregate_runs(runs),
        "limitations": [
            "Single packaged cross-intersection scenario.",
            "Controller logic is baseline-grade and intentionally simple.",
            "Use as engineering validation before MARL training, not as a publication benchmark yet.",
        ],
    }
    return persist_experiment_bundle(bundle)
