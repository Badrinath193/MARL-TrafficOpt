# MARL Traffic Signal Optimization

Research-ready platform for adaptive traffic signal control using SUMO, TraCI, reproducible baselines, and eventually multi-agent reinforcement learning.

Current status: **Phase 15 scenario viewer**. The project now includes health APIs, frontend shell, docs, SUMO tool detection, a scenario catalog, local OSM import, generic imported-network route generation, imported-network inspection, fixed-time and MaxPressure TraCI control for imported maps, imported-network multi-seed JSON/CSV exports, imported-network DQN training, persisted run records, synthetic multi-seed exports, run telemetry summaries, an experiment export browser, 2D SUMO network geometry viewer, and saved-result comparison views.

## Architecture

```text
frontend/        Web dashboard
backend/         API gateway and telemetry broker
rl-service/      Python SUMO/TraCI and RL service
scenario-tools/  OSM and SUMO scenario utilities
experiments/     Configs and reproducible results
docs/            Architecture, methodology, API, literature notes
```

## Quick Start

Backend:

```bash
cd backend
npm install
npm run dev
```

RL service:

```bash
cd rl-service
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python -m marl_traffic_rl_service
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Default local URLs:

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:3001/api/health`
- RL service health: `http://localhost:8000/health`

## Build Order

1. Phase 1: repository foundation and health checks. Done.
2. Phase 2: SUMO installation detection and 1x1 scenario. Done.
3. Phase 3: fixed-time, actuated, and MaxPressure baseline registry. Done.
4. Phase 4: TraCI-controlled baseline execution and metrics export. Done.
5. Phase 5: multi-seed experiment runner and aggregate exports. Done.
6. Phase 6: single-intersection DQN training and greedy evaluation. Done.
7. Phase 7: scenario catalog and saved-result comparison dashboard. Done.
8. Phase 8: local OSM scenario import and catalog persistence. Done.
9. Phase 9: route generation and generic smoke execution for imported OSM scenarios. Done.
10. Phase 10: imported OSM inspection and fixed-time TraCI control. Done.
11. Phase 11: MaxPressure control for imported OSM networks. Done.
12. Phase 12: multi-seed imported-network comparison exports. Done.
13. Phase 13: experiment export browser and run telemetry summaries. Done.
14. Phase 14: imported-network DQN training and greedy evaluation. Done.
15. Phase 15: SUMO network geometry API and 2D scenario viewer. Done.
16. Phase 16: live telemetry streaming and richer 3D city views.

## Documentation

- `PROJECT_SPEC.md`
- `SOURCES_INTEGRATION_PLAN.md`
- `docs/architecture.md`
- `docs/api.md`
- `docs/methodology.md`
- `docs/experiments.md`
- `docs/deployment.md`
- `docs/source-link-analysis.md`

## SUMO Smoke Test

The RL service exposes:

```text
GET  /sumo/detect
POST /simulations/run-smoke-test
```

The backend proxies these as:

```text
GET  /api/sumo/detect
POST /api/simulations/run-smoke-test
```

If `sumo` and `netconvert` are not available on `PATH`, the smoke test returns a structured skipped result instead of failing.

## Baselines

Registered controllers:

- `fixed_time`
- `actuated`
- `max_pressure`

Baseline runs are controlled through TraCI and persisted under `experiments/results/`. The current controllers are intentionally simple and run on a single packaged cross-intersection scenario before larger scenario work begins.

## Multi-Seed Experiments

Run all current baselines over seeds `[1, 2, 3]`:

```text
POST /api/experiments/run
```

Supported demand profiles:

- `balanced`
- `east_west_peak`
- `north_south_peak`

Exports are written to:

```text
experiments/exports/
```

## DQN Training

Train a lightweight single-intersection DQN-style controller:

```text
POST /api/training/dqn
```

Example body:

```json
{
  "episodes": 4,
  "seed": 11,
  "demand_profile": "balanced"
}
```

The implementation intentionally uses a small linear Q approximator with replay instead of a heavyweight ML framework. Training episodes and the greedy evaluation are persisted to `experiments/results/`, while the model bundle and export summary are written to `experiments/exports/`.

## Scenario Catalog And Comparison

List runnable benchmark scenarios:

```text
GET /api/scenarios
```

Compare saved non-training runs for a scenario:

```text
GET /api/experiments/comparison?scenario_id=synthetic/one_intersection_balanced
```

Current scenarios share the packaged cross-intersection network and vary demand profile. OSM-derived geometry remains a future phase.

## OSM Scenario Import

Import a local OSM XML extract:

```text
POST /api/scenarios/import-osm
```

Example body:

```json
{
  "source_path": "scenarios/osm/sample-mini-cross.osm.xml",
  "display_name": "Sample Mini Cross",
  "run_netconvert": true
}
```

Imported scenarios are cataloged under `scenarios/osm/<scenario-slug>/`. If `netconvert` is unavailable or blocked by the OS, the importer still validates and catalogs the OSM source with a structured warning. Imported OSM scenarios are not executable by the baseline/DQN runners until route generation and traffic-light validation are added.

## Imported OSM Smoke Runs

Run route generation and an open-loop SUMO smoke test for an imported OSM scenario:

```text
POST /api/scenarios/run-osm-smoke
```

Example body:

```json
{
  "scenario_id": "osm/sample-mini-cross",
  "seed": 1,
  "end_time": 300,
  "period": 8
}
```

This requires `scenarios/osm/<slug>/network.net.xml`, which is produced by a successful `netconvert` import. If the network file is missing, the endpoint returns a structured skipped result instead of using the synthetic scenario by mistake.

## Imported OSM Fixed-Time Control

Inspect an imported network:

```text
GET /api/scenarios/inspect-osm?scenario_id=osm/sample-mini-cross
```

Run fixed-time TraCI control across discovered traffic lights:

```text
POST /api/scenarios/run-osm-fixed-time
```

Example body:

```json
{
  "scenario_id": "osm/sample-mini-cross",
  "seed": 2,
  "end_time": 300,
  "period": 8,
  "green_steps": 30
}
```

If the imported network has no traffic lights, the endpoint returns a structured skipped result with network inspection counts.

Run MaxPressure TraCI control on an imported network:

```text
POST /api/scenarios/run-osm-max-pressure
```

Example body:

```json
{
  "scenario_id": "osm/sample-mini-cross",
  "seed": 4,
  "end_time": 300,
  "period": 8,
  "min_green": 10
}
```

Run a multi-seed imported OSM controller comparison:

```text
POST /api/experiments/imported-osm/run
```

Example body:

```json
{
  "scenario_id": "osm/sample-mini-cross",
  "controllers": ["osm_open_loop", "osm_fixed_time", "osm_max_pressure"],
  "seeds": [1, 2, 3],
  "end_time": 300,
  "period": 8
}
```

Exports are written to `experiments/exports/`.

## Telemetry Browser

List experiment exports:

```text
GET /api/experiments/exports
```

Read one export bundle:

```text
GET /api/experiments/exports/{experiment_id}
```

Read one run with telemetry summary:

```text
GET /api/experiments/results/{run_id}
```

## Imported OSM DQN

Train independent lightweight DQN agents for an imported OSM network:

```text
POST /api/training/imported-osm-dqn
```

Example body:

```json
{
  "scenario_id": "osm/sample-mini-cross",
  "episodes": 2,
  "seed": 21,
  "end_time": 120,
  "period": 10,
  "min_green": 10
}
```

## Scenario Geometry

Read SUMO network geometry for a scenario:

```text
GET /api/scenarios/geometry?scenario_id=osm/sample-mini-cross
```

The dashboard renders this geometry as a compact 2D SVG preview with edges, junctions, and traffic-light nodes.
