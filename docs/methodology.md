# Methodology

## Non-Negotiables

- No fake benchmark claims.
- Every reported result must come from stored experiment output.
- Baselines must exist before MARL is evaluated.
- Evaluation metrics must be separate from training rewards.

## Required Baselines

1. Fixed-time.
2. Actuated queue controller.
3. MaxPressure.
4. Fuzzy emergency-priority controller.

## Phase 2 Status

The current implementation only verifies SUMO availability and a synthetic one-intersection smoke run. It does not yet implement a controllable traffic-signal policy.

## Phase 3 Status

The current implementation registers baseline controllers and persists comparable SUMO run records. Actual controller actuation via TraCI is still pending, so reported Phase 3 controller runs should be treated as infrastructure validation rather than controller-performance comparisons.

## Phase 4 Status

The implementation now starts SUMO with TraCI, steps the simulation manually, reads lane queues and vehicle waiting times, and sets traffic-light phases for fixed-time, actuated, and MaxPressure baselines.

Current limitations:

- The scenario is still SUMO's packaged cross network plus project route demand.
- Adaptive controller logic is intentionally minimal.
- Results are valid infrastructure metrics, but not yet research benchmark claims.
- Multi-seed experiment orchestration is implemented in Phase 5.

## Phase 5 Status

Multi-seed orchestration is implemented for baseline controllers. The runner executes all selected controller/seed combinations, persists each run, and exports aggregate JSON/CSV files.

Still not publication-ready because:

- Only one network topology is available.
- Demand generation is still simple flow-period variation.
- No confidence intervals yet.
- No learned controller yet.

## First RL Path

1. Single-intersection DQN.
2. Independent multi-agent PPO.
3. Graph-aware MARL.

## Phase 6 Status

Single-intersection DQN training is implemented as a lightweight linear Q approximator with replay. Each training request runs exploratory episodes followed by a greedy evaluation episode.

Current limitations:

- The model is intentionally dependency-light and not a deep neural network framework implementation yet.
- Training still uses one packaged cross-intersection scenario.
- Hyperparameters are conservative defaults for local smoke testing.
- Results are useful for engineering comparison against baselines, not for research claims.

## Phase 7 Status

Scenario cataloging and saved-result comparison are implemented. The project can now group runs by scenario ID and compare controller aggregates from persisted outputs.

Current limitations:

- Scenario variants still share one cross-intersection geometry.
- OSM import and generated multi-intersection SUMO networks are not wired into execution yet.
- Comparison is descriptive and does not yet compute confidence intervals.

## Phase 8 Status

Local OSM scenario import is implemented. The importer validates OSM XML, persists source files into `scenarios/osm/`, attempts SUMO `netconvert`, and registers imported scenario metadata in the catalog.

Current limitations:

- Imported scenarios are cataloged, not yet runnable by the controller runners.
- Demand generation for imported networks is not implemented yet.
- Traffic-light validation and route files must be added before imported OSM scenarios can produce benchmark results.

## Phase 9 Status

Imported OSM route generation and open-loop smoke execution are implemented for scenarios that have a valid `network.net.xml`.

Current limitations:

- The imported OSM runner is open-loop only.
- Random trips are synthetic and not calibrated traffic demand.
- Baseline and DQN controllers still run only on the packaged cross-intersection scenario.
- If `netconvert` fails, imported scenarios remain catalog-only until a network file is provided.

## Phase 10 Status

Imported OSM network inspection and fixed-time TraCI control are implemented. This is the first controller execution path for imported networks.

Current limitations:

- Only fixed-time phase cycling is implemented for imported networks.
- The policy cycles raw SUMO program phases and does not yet reason about lane pressure.
- Imported-network DQN and MaxPressure are still future work.
- Results remain engineering validation unless demand is calibrated and more scenarios are added.

## Phase 11 Status

Imported OSM MaxPressure control is implemented. The controller uses TraCI controlled links and queue pressure to choose signal phases on imported networks.

Current limitations:

- No yellow-transition synthesis for arbitrary imported signal programs yet.
- Random trip demand remains synthetic.
- Multi-seed imported OSM aggregate exports are not implemented yet.
- DQN still runs only on the packaged cross-intersection scenario.

## Phase 12 Status

Multi-seed imported OSM experiments are implemented for open-loop, fixed-time, and MaxPressure controllers.

Current limitations:

- Imported OSM demand still uses synthetic random trips.
- Experiments are engineering comparisons, not calibrated traffic studies.
- Imported-network DQN is not implemented yet.

## Phase 13 Status

Experiment export browsing and run telemetry summaries are implemented. This improves auditability by making JSON/CSV bundle contents visible through API and dashboard views.

Current limitations:

- Telemetry charts are tabular summaries, not interactive plots yet.
- No live WebSocket telemetry stream yet.
- Export files are local filesystem artifacts, not a database-backed experiment registry.

## Phase 14 Status

Imported OSM DQN training is implemented with independent lightweight linear agents per traffic light.

Current limitations:

- This is not a full deep neural network implementation.
- Demand remains synthetic randomTrips demand.
- The learner is independent per signal and does not coordinate across a graph yet.
- Larger imported networks need longer training and validation before claims are made.

## Phase 15 Status

SUMO network geometry inspection is implemented for imported OSM scenarios and the packaged synthetic scenario. The dashboard now renders a 2D network preview with edges, junctions, and traffic-light nodes.

Current limitations:

- The viewer is read-only and does not edit scenarios.
- It renders 2D SVG geometry, not full 3D city meshes.
- Live simulation telemetry is still polled through result files and summaries, not streamed over WebSockets.
- Geometry previews support inspection only; benchmark claims still come from persisted experiment outputs.

## Metrics

- Average delay.
- Average queue length.
- Maximum queue length.
- Throughput.
- Number of stops.
- Average travel time.
- Emergency response time.
- Emissions from SUMO where available.
- Controller compute time.
