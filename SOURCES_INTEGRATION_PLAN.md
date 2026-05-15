# Source Research and Integration Plan

## Important Constraint

Do not merge external repositories blindly. Use them as references unless their license, architecture, and maintenance quality are compatible with our project.

This project should be built around a clean architecture:

- SUMO/TraCI as the primary microscopic simulator.
- Python RL service for baselines and MARL.
- Node/FastAPI gateway only if needed for web orchestration.
- React + Three.js frontend for visualization and experiment control.
- OSM/SUMO/CityFlow-compatible scenario formats.

## Tier 1 - Core References to Use

### Eclipse SUMO

Use as the primary simulation engine.

Useful parts:

- Microscopic traffic simulation.
- TraCI control API.
- Scenario creation tools.
- Traffic light control.
- Vehicle, pedestrian, emission, and multi-modal support.

Integration:

- `rl-service` owns SUMO process lifecycle.
- `rl-service` exposes normalized observations/actions to controllers.
- `backend` calls `rl-service` for run/train/evaluate operations.

Reason:

SUMO is the most mature and directly aligned dependency for real traffic-signal control.

### SUMO-RL Style Environment

Sources:

- `EEEEEclectic/traffic_signal_control`
- `zamweis/sumo-marl-traffic-control`

Useful parts:

- PettingZoo/Gym-style environment pattern.
- One agent per traffic signal.
- TraCI-backed traffic signal abstraction.
- Training/evaluation script layout.
- OSM-to-SUMO network repair/validation scripts.
- Reward variants: waiting time, queue length, emissions, weighted real-world reward.
- Baseline comparison against fixed-time and actuated controllers.

Integration:

- Implement our own `TrafficSignalEnv`.
- Use PettingZoo parallel API for MARL.
- Keep controller plugins separate:
  - `FixedTimeController`
  - `ActuatedController`
  - `MaxPressureController`
  - `FuzzyEmergencyController`
  - `DQNController`
  - `PPOController`

Do not copy:

- Thesis-specific paths.
- Hardcoded Karlsruhe scenario.
- Manual modifications to installed packages.

### UXsim

Use as an optional fast planning simulator, not as the main microscopic simulator.

Useful parts:

- Lightweight Python macroscopic/mesoscopic simulation.
- Large-scale traffic-flow approximations.
- Dynamic traffic assignment ideas.
- Fast CSV/pandas metric export.
- Educational notebooks and simple API style.

Integration:

- Add optional `uxsim-adapter` later for high-level network-flow experiments.
- Keep SUMO as the authoritative simulator for signal-control experiments.

Reason:

UXsim is useful for fast city-scale traffic-flow estimation, but MARL traffic-signal control still needs microscopic lane/signal details from SUMO.

### RL Signals Website / Traffic Signal Control Benchmark

Use as research guidance and benchmark source.

Useful parts:

- Paper list.
- Dataset list.
- CityFlow roadnet/flow benchmark structure.
- Concepts: MaxPressure, PressLight, CoLight, FRAP, MetaLight, DemoLight.
- Evaluation focus: average travel time, city-scale benchmark scenarios.

Integration:

- Create `docs/literature.md`.
- Add benchmark-compatible dataset import later.
- Use MaxPressure as a required baseline before any MARL claim.

## Tier 2 - Visualization and Map Pipeline References

### map3d

Use as frontend inspiration.

Useful parts:

- React Three Fiber city-map structure.
- OSM buildings and roads rendered as 3D objects.
- GLB export idea.
- Digital-twin/GPS-marker use cases.

Integration:

- Build our frontend with React + Three.js/R3F.
- Add OSM building extrusion for presentation mode.
- Keep simulation overlay separate from static city mesh.

### OSM2World

Use as preferred open 3D city-model generation option.

Useful parts:

- OSM to glTF/glb/OBJ generation.
- Broad OSM tag support.
- Level-of-detail concepts.
- Standalone CLI/library/server deployment.

Integration:

- Add optional `scenario-assets` command:
  - input: `.osm` or bbox
  - output: `.glb` city context
- Use generated GLB only as visual context, not as simulation logic.

### F4map Demo

Use as visual inspiration only.

Useful parts:

- Weather/time-of-day controls.
- 3D map display options.
- Traffic overlay concept.

Integration:

- Add display toggles later:
  - day/night
  - traffic density overlay
  - buildings on/off
  - terrain on/off

Do not integrate proprietary assets or services.

### TopoExport / Rayon Maps / CityWeft / Spatial Manager

Use as workflow inspiration, not dependencies.

Useful parts:

- Layer-based exports.
- Roads/buildings/water/rail/contour separation.
- DXF/SVG/OBJ/STL/IFC-style export thinking.
- Coordinate reference system awareness.

Integration:

- Our scenario export should support:
  - JSON scenario
  - SUMO XML
  - CSV metrics
  - GLB context mesh
  - optional DXF/SVG map export later

Do not depend on paid/web-only tools for the core project.

### Blosm

Borrow ideas only.

Useful parts:

- OSM building import.
- Terrain import.
- Roads/paths/railways as curves with width.
- Roof/height/floor tag handling.

Constraint:

- GPL ecosystem and Blender-specific workflow make direct integration risky for an MIT web project.

### MapsModelsImporter

Do not integrate.

Reason:

- It is a proof-of-concept for importing Google Maps/Google Earth captures.
- The README explicitly warns against commercial/redistribution use.
- GPL license and data-rights risk conflict with an open-source publishable project.

## Tier 3 - Computer Vision References

### Adaptive Traffic Signal Timer

Useful parts:

- YOLO-based vehicle density estimation from junction cameras.
- Signal timing based on detected density.
- Apache-2.0 license.

Integration:

- Later module: `cv-service`.
- Input: camera image/video.
- Output: lane density estimate.
- Feed density into simulation or controller as an observation source.

### Smart Adaptive Traffic Management System

Useful parts:

- CCTV capture.
- YOLO v8 vehicle/pedestrian detection.
- GUI monitoring concept.
- Signal time calculation from traffic density.

Constraint:

- GPL-3.0 license. Do not copy code into an MIT repo.

Integration:

- Borrow architecture idea only:
  - camera ingest
  - object detection
  - density estimator
  - signal optimizer
  - operator dashboard

### Ujwal2910 Smart Traffic Signals in India

Useful parts:

- Indian traffic motivation.
- SUMO + DQN + target network + replay.
- Queue length plus phase as state.
- Switch/not-switch action design.
- Background-subtraction queue estimation concept.
- Single and two-junction scenarios.

Integration:

- Use as conceptual reference for:
  - India-focused scenarios
  - simple DQN baseline
  - queue-length state model
  - camera-derived state option

Do not overfit to screen-recorded SUMO-frame processing; use TraCI for simulator state and CV only for real/synthetic camera inputs.

## Tier 4 - RL/Controller References

### DQL-TSC

Useful parts:

- Single-intersection DQN framing.
- Action as phase change.
- Reward based on waiting-time reduction.
- Good beginner baseline before MARL.

Integration:

- First RL milestone should be single-intersection DQN.
- Then extend to multi-agent.

### Reward Functions Paper Repository

Useful parts:

- Reward-function comparison under real-world constraints.
- Reward candidates:
  - stopped time
  - lost time
  - change in lost time
  - speed
  - queue length
  - throughput
- Strong reminder that reward choice changes results.

Integration:

- Add `rewards/` plugin system.
- Every experiment config must declare reward function.
- Evaluation metric must be separate from training reward.

### Fuzzy Traffic Controller

Useful parts:

- Fuzzy emergency-priority controller.
- Inputs: red-lane vehicles, green-lane vehicles, max waiting time, emergency vehicles on red/green.
- Output: switch or stay.
- Comparison with uncontrolled/fixed behavior.

Integration:

- Implement as non-RL baseline:
  - `FuzzyEmergencyController`
- Use for emergency preemption and explainable baseline.

### mschrader15 reinforcement-learning-sumo

Useful parts:

- SUMO wrapped into Gym-style RL environment.
- RLlib/PPO/ES comparison idea.
- XML-first workflow for real-world demand and signal operations.

Integration:

- Keep SUMO XML scenario files explicit.
- Avoid hiding scenario generation behind opaque abstractions.
- Optional RLlib support later; start with Stable-Baselines3/PyTorch first.

### Verilog FSM Traffic Signal

Useful parts:

- Simple finite-state-machine model for signal phase logic.

Integration:

- Use only as educational documentation for phase safety and state transitions.
- Do not include Verilog in the main platform unless hardware demonstration becomes a separate module.

## Tier 5 - Game/Engine/High-Scale Visual Simulation References

### OSMTrafficSim

Useful parts:

- OSM road graph generation.
- Unity ECS high-scale visual traffic.
- BVH/spatial indexing for vehicle communication.
- Pedestrian animation ideas.

Constraint:

- GPL-3.0 and Unity-specific.

Integration:

- Borrow design ideas:
  - spatial index for nearby vehicles
  - OSM-to-road-graph conversion
  - performance target thinking
- Do not port Unity ECS code.

### Godot Road Generator

Useful parts:

- Procedural road/intersection mesh generation.
- Lane-following traffic paths.
- GLB export.
- Custom mesh/collider separation.

Constraint:

- Godot-specific GDScript.

Integration:

- Borrow mesh-generation concepts for frontend visual context.
- Do not add Godot dependency to the main project.

### TrafficSim / whipped-cream Traffic

Potential use:

- Game/simulation inspiration only.

Integration:

- No direct integration planned unless later review finds a uniquely useful algorithm.

## Tier 6 - CAD / 3D Export References

### text-to-cad

Useful parts:

- CAD artifact generation workflow.
- STEP/STL/GLB/DXF export mindset.
- Agent workflow discipline: edit source first, regenerate artifacts explicitly, review generated geometry.

Integration:

- Use workflow ideas for generated city/road assets:
  - source scenario first
  - generated assets second
  - reproducible export command
  - do not hand-edit generated artifacts

Do not integrate CAD skills into the core traffic platform.

## Recommended Final Architecture

```text
frontend/
  React + R3F dashboard
  Scenario editor
  2D/3D map viewer
  Metrics charts
  Training/evaluation monitor

backend/
  API gateway
  Auth-free local mode
  Scenario metadata
  WebSocket telemetry broker

rl-service/
  SUMO process manager
  TraCI adapter
  PettingZoo/Gym environments
  Controllers and reward plugins
  Experiment runner
  Metrics exporter

scenario-tools/
  OSM downloader
  OSM validator
  OSM-to-SUMO pipeline
  SUMO network repair checks
  Optional OSM2World visual asset export

experiments/
  configs/
  results/
  notebooks/

docs/
  architecture
  setup
  methodology
  literature
  benchmark protocol
```

## Controller Roadmap

1. Fixed-time controller.
2. Actuated queue controller.
3. MaxPressure controller.
4. Fuzzy emergency controller.
5. Single-intersection DQN.
6. Independent multi-agent PPO.
7. Graph-aware MARL with DCRNN/Transformer/attention.

## Scenario Roadmap

1. Synthetic 1x1 intersection.
2. Synthetic 2x2 grid.
3. Synthetic 4x4 grid.
4. OSM small Indian junction.
5. OSM corridor with 3-5 signals.
6. OSM district-scale network.
7. Optional CityFlow benchmark datasets.

## What Not to Do

- Do not combine Unity, Godot, Blender, SUMO, CityFlow, and web rendering into one runtime.
- Do not copy GPL code into an MIT codebase.
- Do not use Google Maps extracted geometry.
- Do not claim 37% or any benchmark result without stored experiment outputs.
- Do not implement MARL before fixed-time, actuated, and MaxPressure baselines.

## Best Integration Path

Phase 1:

- Scaffold clean monorepo.
- Implement backend health API.
- Implement frontend shell.
- Implement SUMO install detector.

Phase 2:

- Implement scenario-tools with OSM download, validation, and SUMO conversion.
- Add 1x1 and 2x2 synthetic SUMO scenarios.

Phase 3:

- Implement TraCI environment and fixed-time/actuated/MaxPressure controllers.
- Add metrics export.

Phase 4:

- Implement single-intersection DQN.
- Add experiment runner.

Phase 5:

- Implement multi-agent PPO using PettingZoo parallel env.
- Add graph-aware model hooks later.

Phase 6:

- Add 3D visualization with OSM2World/map3d-inspired rendering.
- Keep rendering separate from simulation correctness.

Phase 7:

- Add optional CV service for YOLO/density estimation.
- Treat CV as an observation provider, not the core simulator.
