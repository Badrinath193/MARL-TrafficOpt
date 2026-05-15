# Experiments

## Directory Layout

```text
experiments/
  configs/   committed experiment configs
  results/   generated outputs, ignored by git except .gitkeep
  exports/   aggregate JSON/CSV exports, ignored by git except .gitkeep
```

## Phase 2 Smoke Scenario

Scenario path:

```text
scenarios/synthetic/one_intersection/
```

The smoke test is intentionally minimal. It verifies that:

- SUMO tools are installed.
- `netconvert` can build a network.
- `sumo` can run headlessly.
- `tripinfo.xml` can be parsed into basic metrics.

On machines where `netconvert` is blocked by policy, the smoke test uses SUMO's packaged `cross.net.xml` so the headless SUMO execution path can still be verified.

It is not a benchmark and should not be used for research claims.

## Phase 3 Baseline Records

Baseline runs write JSON files to:

```text
experiments/results/
```

Each record includes:

- Controller metadata.
- Scenario ID.
- SUMO tool detection details.
- Runtime duration.
- Parsed trip metrics.
- Current limitations.

## Phase 4 TraCI Baselines

Phase 4 records include:

- `execution: traci_controlled`
- `phase_changes`
- Queue samples from TraCI lane state.
- Parsed `tripinfo.xml` metrics.

The baseline endpoint now applies phase decisions during simulation rather than only recording declared controller metadata.

## Phase 5 Multi-Seed Experiments

The experiment runner executes each selected controller across each selected seed. It stores:

- Individual run JSON files in `experiments/results/`.
- Aggregate experiment JSON in `experiments/exports/`.
- Aggregate experiment CSV in `experiments/exports/`.

Current demand profiles:

- `balanced`
- `east_west_peak`
- `north_south_peak`

Aggregate metrics include mean, standard deviation, min, and max for arrival count, duration, waiting time, time loss, queue length, and active vehicles.

## Phase 6 DQN Training

The DQN training endpoint runs exploratory training episodes and one greedy evaluation episode on the same single-intersection SUMO scenario.

Stored outputs:

- Training episode JSON records in `experiments/results/`.
- Greedy evaluation JSON record in `experiments/results/`.
- DQN experiment bundle in `experiments/exports/`.
- CSV export containing run-level metrics.

The Phase 6 learner uses a lightweight linear Q approximator with replay and epsilon-greedy exploration. It is a real trainable controller path, but it is not yet a publication benchmark because the scenario set is still too small.

## Phase 7 Scenario Comparison

Phase 7 adds a scenario catalog and saved-result comparison endpoint.

Current scenario IDs:

- `synthetic/one_intersection_balanced`
- `synthetic/one_intersection_east_west_peak`
- `synthetic/one_intersection_north_south_peak`

These scenarios intentionally share the same packaged cross-intersection network and vary demand profile. This keeps local validation reliable while creating distinct benchmark slices for controller comparison.

Comparison summaries exclude exploratory DQN training episodes and aggregate only saved non-training records, including baseline runs and greedy DQN evaluations.

## Phase 8 OSM Import

Phase 8 adds local OSM import and catalog persistence.

Input:

- `.osm`
- `.xml`
- `.osm.xml`

Import output:

- `scenarios/osm/<slug>/source.osm.xml`
- `scenarios/osm/<slug>/scenario.json`
- `scenarios/osm/<slug>/network.net.xml` when `netconvert` succeeds

The importer validates XML shape, counts OSM nodes, ways, and highway ways, then attempts `netconvert --osm-files`. If `netconvert` is blocked or unavailable, the scenario is still cataloged as imported source data with limitations.

Imported OSM scenarios are not yet executable by the baseline or DQN runners. Phase 9 must add route generation, demand injection, traffic-light validation, and generic SUMO execution for imported networks.

## Phase 9 Imported OSM Smoke Execution

Phase 9 adds a generic open-loop smoke runner for imported OSM scenarios that have a converted SUMO network.

Execution prerequisites:

- `scenarios/osm/<slug>/network.net.xml`
- SUMO `sumo`
- SUMO `randomTrips.py`
- `duarouter` for validated random-trip route generation

The runner creates:

- `generated.rou.xml`
- `osm_smoke.sumocfg`
- `tripinfo.xml`
- A persisted result record under `experiments/results/`

If the imported scenario has no converted network, the runner returns a structured skipped result. This prevents accidental reuse of the synthetic cross-intersection network.

## Phase 10 Imported OSM Fixed-Time Control

Phase 10 adds network inspection and a TraCI fixed-time controller for imported OSM scenarios.

The inspection endpoint reports:

- SUMO network path.
- Junction count.
- Edge count.
- Traffic light IDs.

The fixed-time runner:

- Regenerates random routes.
- Starts SUMO through TraCI.
- Discovers all traffic-light IDs.
- Cycles every traffic light through its program phases using a fixed interval.
- Persists trip and queue metrics.

If no traffic lights are discovered, the runner returns a skipped result instead of pretending a controller was evaluated.

## Phase 11 Imported OSM MaxPressure

Phase 11 adds a MaxPressure controller for imported OSM networks. For every discovered traffic light, the runner:

- Finds candidate non-yellow green phases.
- Reads controlled links from TraCI.
- Scores each phase by incoming queue minus outgoing queue.
- Enforces a minimum green interval before switching.
- Persists trip, queue, and phase-change metrics.

This is the first adaptive imported-network baseline. It is still not a research benchmark until demand calibration and multi-seed imported-network runs are added.

## Phase 12 Imported OSM Experiment Exports

Phase 12 adds multi-seed imported OSM controller comparison.

Supported imported OSM controllers:

- `osm_open_loop`
- `osm_fixed_time`
- `osm_max_pressure`

Each experiment persists individual run records to `experiments/results/` and aggregate JSON/CSV files to `experiments/exports/`.

The exported aggregate includes the same metric family used by synthetic experiments: arrivals, duration, waiting time, time loss, queue length, active vehicles, and phase changes.

## Phase 13 Telemetry Browser

Phase 13 adds read-only APIs and dashboard views for exported experiment bundles and run telemetry summaries.

The export browser reads files from `experiments/exports/` and shows:

- Experiment ID.
- Scenario.
- Experiment type.
- Controllers.
- Seeds.
- Aggregate metrics.

Run detail reads files from `experiments/results/` and summarizes available time-series telemetry, including queue and active vehicle ranges.

## Phase 14 Imported OSM DQN

Phase 14 adds imported-network DQN training. The implementation uses one lightweight linear DQN agent per discovered traffic light.

Each training request:

- Generates random trips for every episode.
- Runs exploratory training episodes with epsilon decay.
- Runs one greedy evaluation episode.
- Persists all episode records.
- Exports a bundle containing per-signal model weights.

This is an engineering baseline for imported-network learning, not a final MARL implementation.

## Phase 15 Scenario Geometry Viewer

Phase 15 adds a read-only SUMO network geometry API and dashboard preview for scenario inspection.

The geometry endpoint:

- Reads imported OSM `network.net.xml` files.
- Generates the packaged synthetic network on demand if needed.
- Returns bounded edge polylines, junction positions, and traffic-light node IDs.
- Keeps visualization data separate from experiment metrics.

The dashboard renders the response as a compact 2D SVG preview so users can verify the selected scenario before running controllers or training.

## Experiment Config Requirements

Each config must declare:

- Scenario ID.
- SUMO config path.
- Controller type.
- Reward function if training.
- Random seed.
- Simulation duration.
- Demand profile.
- Output directory.

## Reporting Requirements

Reports must include:

- Mean.
- Standard deviation.
- Confidence interval.
- Number of seeds.
- Scenario commit/version.
- SUMO version.
- Hardware/software environment.
