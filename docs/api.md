# API

## Backend

Base URL: `http://localhost:3001`

### `GET /api/health`

Returns backend health and RL service connectivity.

### `GET /api/status`

Returns current development phase and next milestone.

### `GET /api/sumo/detect`

Proxies SUMO tool detection from the RL service.

### `POST /api/simulations/run-smoke-test`

Runs the synthetic one-intersection smoke test through the RL service. If SUMO is not installed, returns a skipped result with installation guidance.

## RL Service

Base URL: `http://localhost:8000`

### `GET /health`

Returns RL service health and declared capabilities.

### `GET /status`

Returns current development phase and next milestone.

### `GET /sumo/detect`

Detects `sumo` and `netconvert` on `PATH`.

### `POST /simulations/run-smoke-test`

Generates the one-intersection SUMO network with `netconvert`, runs SUMO headlessly, and parses `tripinfo.xml`.

## Future Endpoints

```text
POST /api/simulations/run
GET  /api/experiments/:id/results
GET  /api/experiments/:id/export.csv
WS   /api/telemetry
```

## Phase 3 Baselines

### `GET /api/controllers`

Lists registered baseline controllers.

### `GET /api/scenarios`

Lists runnable scenario catalog entries.

### `POST /api/scenarios/import-osm`

Imports a local OSM XML extract into `scenarios/osm/`, validates basic OSM structure, and attempts SUMO `netconvert` when available.

Example body:

```json
{
  "source_path": "scenarios/osm/sample-mini-cross.osm.xml",
  "display_name": "Sample Mini Cross",
  "run_netconvert": true
}
```

Returns imported scenario metadata, OSM element counts, generated file paths, and any `netconvert` warning or error details.

### `POST /api/scenarios/run-osm-smoke`

Generates random trips for an imported OSM network and runs an open-loop SUMO smoke simulation.

Example body:

```json
{
  "scenario_id": "osm/sample-mini-cross",
  "seed": 1,
  "end_time": 300,
  "period": 8
}
```

Requires `network.net.xml` inside the imported scenario directory. If that file is missing, the endpoint returns a skipped result with the missing prerequisite.

### `GET /api/scenarios/inspect-osm`

Inspects an imported OSM SUMO network and reports junction, edge, and traffic-light counts.

Example:

```text
GET /api/scenarios/inspect-osm?scenario_id=osm/sample-mini-cross
```

### `GET /api/scenarios/geometry`

Returns compact SUMO network geometry for dashboard rendering.

Example:

```text
GET /api/scenarios/geometry?scenario_id=osm/sample-mini-cross
```

The response includes bounds, edge lane shapes, junction positions, traffic-light nodes, and a summary count. Imported OSM scenarios read `network.net.xml`; packaged synthetic scenarios are generated from the local SUMO definition when needed.

### `POST /api/scenarios/run-osm-fixed-time`

Runs a TraCI-controlled fixed-time policy across every discovered traffic light in an imported OSM network.

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

Returns route-generation details, discovered traffic-light control metadata, trip metrics, queue metrics, and a persisted result path.

### `POST /api/scenarios/run-osm-max-pressure`

Runs a MaxPressure TraCI policy across every discovered traffic light in an imported OSM network.

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

Scores each candidate green phase by incoming queue minus outgoing queue across SUMO controlled links.

### `POST /api/experiments/imported-osm/run`

Runs a multi-seed imported OSM experiment and exports aggregate JSON/CSV files.

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

Returns per-run records, aggregate metrics, and export paths.

### `POST /api/experiments/baselines/:controllerName`

Runs the one-intersection scenario for the selected baseline and persists a result JSON file.

In Phase 4 this endpoint uses TraCI-controlled signal execution.

### `GET /api/experiments/results`

Lists saved experiment result summaries.

### `GET /api/experiments/results/:runId`

Returns a saved run record and a compact telemetry summary from its time series.

### `GET /api/experiments/exports`

Lists exported experiment bundles from `experiments/exports/`.

### `GET /api/experiments/exports/:experimentId`

Returns one exported experiment bundle with aggregate metrics.

### `GET /api/experiments/comparison`

Aggregates saved non-training runs by controller.

Supported query parameters:

- `scenario_id`
- `demand_profile`

### `POST /api/experiments/run`

Runs a multi-seed experiment.

Example body:

```json
{
  "controllers": ["fixed_time", "actuated", "max_pressure"],
  "seeds": [1, 2, 3],
  "scenario_id": "synthetic/one_intersection_balanced"
}
```

Returns per-run results, aggregate metrics, and JSON/CSV export paths.

### `POST /api/training/dqn`

Trains the Phase 6 single-intersection DQN-style controller and then runs a greedy evaluation episode.

Example body:

```json
{
  "episodes": 4,
  "seed": 11,
  "scenario_id": "synthetic/one_intersection_balanced"
}
```

Returns training run records, the greedy evaluation record, the learned linear Q model weights, and JSON/CSV export paths.

### `POST /api/training/imported-osm-dqn`

Trains independent lightweight DQN agents for traffic lights in an imported OSM network, then runs a greedy evaluation episode.

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

Returns training run records, greedy evaluation metrics, learned per-signal model weights, and export paths.
