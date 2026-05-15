from fastapi import FastAPI
from pydantic import BaseModel, Field

from . import __version__
from .controllers import list_controllers
from .dqn import train_single_intersection_dqn
from .experiments import compare_results, get_export, get_result, list_exports, list_results
from .geometry import get_scenario_geometry
from .gui import launch_sumo_gui
from .imported_dqn import train_imported_osm_dqn
from .osm_experiments import run_imported_osm_experiment
from .osm_runner import inspect_imported_osm_scenario, run_imported_osm_fixed_time, run_imported_osm_max_pressure, run_imported_osm_smoke
from .runner import run_multi_seed_experiment
from .scenarios import import_osm_scenario, list_scenarios, search_and_import_osm_scenario
from .sumo import detect_sumo_tools, run_one_intersection_baseline, run_one_intersection_smoke_test

app = FastAPI(title="MARL TrafficOpt RL Service", version=__version__)


class ExperimentRequest(BaseModel):
    controllers: list[str] | None = None
    seeds: list[int] | None = Field(default=None, max_length=10)
    demand_profile: str | None = None
    scenario_id: str | None = None


class DqnTrainingRequest(BaseModel):
    episodes: int = Field(default=4, ge=1, le=20)
    seed: int = 1
    demand_profile: str | None = None
    scenario_id: str | None = None


class ImportedOsmDqnRequest(BaseModel):
    scenario_id: str
    episodes: int = Field(default=3, ge=1, le=12)
    seed: int = 1
    end_time: int = Field(default=180, ge=30, le=1800)
    period: int = Field(default=10, ge=1, le=120)
    min_green: int = Field(default=10, ge=1, le=120)


class OsmImportRequest(BaseModel):
    source_path: str
    display_name: str | None = None
    scenario_slug: str | None = None
    run_netconvert: bool = True


class OsmSearchImportRequest(BaseModel):
    query: str
    display_name: str | None = None
    scenario_slug: str | None = None
    run_netconvert: bool = True


class SumoGuiLaunchRequest(BaseModel):
    scenario_id: str
    seed: int = 1
    end_time: int = Field(default=1500, ge=30, le=3600)
    period: int = Field(default=1, ge=1, le=120)
    demand_profile: str | None = None


class OsmSmokeRequest(BaseModel):
    scenario_id: str
    seed: int = 1
    end_time: int = Field(default=1500, ge=30, le=3600)
    period: int = Field(default=1, ge=1, le=120)


class OsmFixedTimeRequest(OsmSmokeRequest):
    green_steps: int = Field(default=30, ge=5, le=300)


class OsmMaxPressureRequest(OsmSmokeRequest):
    min_green: int = Field(default=10, ge=1, le=120)


class ImportedOsmExperimentRequest(BaseModel):
    scenario_id: str
    controllers: list[str] | None = None
    seeds: list[int] | None = Field(default=None, max_length=10)
    end_time: int = Field(default=1200, ge=30, le=3600)
    period: int = Field(default=1, ge=1, le=120)


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "marl-trafficopt-rl-service",
        "version": __version__,
        "phase": "phase-16-interactive-sumo-osm",
        "capabilities": [
            "health",
            "sumo-detection",
            "one-intersection-smoke-test",
            "baseline-controller-registry",
            "baseline-result-persistence",
            "traci-controlled-baselines",
            "multi-seed-experiment-runner",
            "json-csv-exports",
            "single-intersection-dqn-training",
            "scenario-catalog",
            "result-comparison",
            "osm-scenario-import",
            "imported-osm-route-generation",
            "imported-osm-smoke-runner",
            "imported-osm-network-inspection",
            "imported-osm-fixed-time-traci",
            "imported-osm-max-pressure-traci",
            "imported-osm-multiseed-experiments",
            "experiment-export-browser",
            "run-telemetry-summary",
            "imported-osm-dqn-training",
            "scenario-geometry-viewer",
            "sumo-gui-launcher",
            "osm-location-search-import",
        ],
        "sumo": detect_sumo_tools(),
    }


@app.get("/status")
def status() -> dict:
    return {
        "ok": True,
        "currentPhase": "Phase 16",
        "nextMilestone": "Live browser telemetry streaming and 3D city views",
    }


@app.get("/sumo/detect")
def sumo_detect() -> dict:
    return {
        "ok": True,
        "tools": detect_sumo_tools(),
    }


@app.post("/simulations/run-smoke-test")
def run_smoke_test() -> dict:
    return run_one_intersection_smoke_test()


@app.get("/controllers")
def controllers() -> dict:
    return {
        "ok": True,
        "controllers": list_controllers(),
    }


@app.get("/scenarios")
def scenarios() -> dict:
    return {
        "ok": True,
        "scenarios": list_scenarios(),
    }


@app.get("/scenarios/geometry")
def scenario_geometry(scenario_id: str) -> dict:
    return get_scenario_geometry(scenario_id)


@app.post("/scenarios/import-osm")
def import_osm(request: OsmImportRequest) -> dict:
    return import_osm_scenario(
        source_path=request.source_path,
        display_name=request.display_name,
        scenario_slug=request.scenario_slug,
        run_netconvert=request.run_netconvert,
    )


@app.post("/scenarios/search-import-osm")
def search_import_osm(request: OsmSearchImportRequest) -> dict:
    return search_and_import_osm_scenario(
        query=request.query,
        display_name=request.display_name,
        scenario_slug=request.scenario_slug,
        run_netconvert=request.run_netconvert,
    )


@app.post("/sumo/launch-gui")
def launch_gui(request: SumoGuiLaunchRequest) -> dict:
    return launch_sumo_gui(
        scenario_id=request.scenario_id,
        seed=request.seed,
        end_time=request.end_time,
        period=request.period,
        demand_profile=request.demand_profile,
    )


@app.post("/scenarios/run-osm-smoke")
def run_osm_smoke(request: OsmSmokeRequest) -> dict:
    return run_imported_osm_smoke(
        scenario_id=request.scenario_id,
        seed=request.seed,
        end_time=request.end_time,
        period=request.period,
    )


@app.get("/scenarios/inspect-osm")
def inspect_osm(scenario_id: str) -> dict:
    return inspect_imported_osm_scenario(scenario_id)


@app.post("/scenarios/run-osm-fixed-time")
def run_osm_fixed_time(request: OsmFixedTimeRequest) -> dict:
    return run_imported_osm_fixed_time(
        scenario_id=request.scenario_id,
        seed=request.seed,
        end_time=request.end_time,
        period=request.period,
        green_steps=request.green_steps,
    )


@app.post("/scenarios/run-osm-max-pressure")
def run_osm_max_pressure(request: OsmMaxPressureRequest) -> dict:
    return run_imported_osm_max_pressure(
        scenario_id=request.scenario_id,
        seed=request.seed,
        end_time=request.end_time,
        period=request.period,
        min_green=request.min_green,
    )


@app.post("/experiments/imported-osm/run")
def run_imported_osm_experiment_endpoint(request: ImportedOsmExperimentRequest) -> dict:
    return run_imported_osm_experiment(
        scenario_id=request.scenario_id,
        controllers=request.controllers,
        seeds=request.seeds,
        end_time=request.end_time,
        period=request.period,
    )


@app.post("/experiments/baselines/{controller_name}")
def run_baseline(controller_name: str) -> dict:
    return run_one_intersection_baseline(controller_name)


@app.get("/experiments/results")
def experiment_results() -> dict:
    return {
        "ok": True,
        "results": list_results(),
    }


@app.get("/experiments/results/{run_id}")
def experiment_result_detail(run_id: str) -> dict:
    return get_result(run_id)


@app.get("/experiments/exports")
def experiment_exports() -> dict:
    return {
        "ok": True,
        "exports": list_exports(),
    }


@app.get("/experiments/exports/{experiment_id}")
def experiment_export_detail(experiment_id: str) -> dict:
    return get_export(experiment_id)


@app.get("/experiments/comparison")
def experiment_comparison(scenario_id: str | None = None, demand_profile: str | None = None) -> dict:
    return {
        "ok": True,
        "comparison": compare_results(scenario_id=scenario_id, demand_profile=demand_profile),
    }


@app.post("/experiments/run")
def run_experiment(request: ExperimentRequest) -> dict:
    return run_multi_seed_experiment(
        controllers=request.controllers,
        seeds=request.seeds,
        demand_profile=request.demand_profile,
        scenario_id=request.scenario_id,
    )


@app.post("/training/dqn")
def train_dqn(request: DqnTrainingRequest) -> dict:
    return train_single_intersection_dqn(
        episodes=request.episodes,
        seed=request.seed,
        demand_profile=request.demand_profile,
        scenario_id=request.scenario_id,
    )


@app.post("/training/imported-osm-dqn")
def train_imported_dqn(request: ImportedOsmDqnRequest) -> dict:
    return train_imported_osm_dqn(
        scenario_id=request.scenario_id,
        episodes=request.episodes,
        seed=request.seed,
        end_time=request.end_time,
        period=request.period,
        min_green=request.min_green,
    )
