# Source Link Analysis

This document summarizes the GitHub repositories and websites originally supplied for the project. The goal is not to merge them blindly. The goal is to extract patterns that directly improve this project: OSM import, SUMO simulation, 3D city/world rendering, adaptive traffic control, reinforcement learning, and presentable open-source packaging.

## Project Direction

The project should be built around five layers:

1. OSM acquisition and conversion: location search, Overpass download, SUMO `netconvert`, scenario metadata.
2. SUMO execution: route generation, high-density demand, SUMO-GUI launch, TraCI-controlled simulation.
3. Traffic control: fixed-time, actuated, MaxPressure, fuzzy logic, DQN, and later MARL.
4. 3D visualization: browser Three.js world built from SUMO/OSM geometry and simulation telemetry.
5. Research workflow: reproducible experiments, metrics, reward-function comparison, saved runs, CSV/JSON export.

## 3D City, CAD, and OSM Visualization Sources

| Source | What It Is | Useful Ideas | Project Decision |
|---|---|---|---|
| `earthtojake/text-to-cad` | Agent skills for CAD, robotics, and hardware design. It supports generated CAD outputs such as STEP, STL, 3MF, DXF, GLB, topology, and robot descriptions. | Useful for future CAD/export workflows: road network export, GLB export, and geometry review tooling. | Do not integrate now. Use as reference for future export pipeline and source-controlled generated geometry. |
| `cartesiancs/map3d` | R3F/React 3D city map generator with buildings and roads. | Directly relevant for browser-side city/world rendering and scene organization. | Study for 3D road/building component structure. Current project uses plain Three.js; R3F can be considered later. |
| `louis-e/arnis` | Generates real-world locations in Minecraft from OSM-style map data. | Useful for understanding OSM-to-3D-world generation, terrain/block simplification, and large-map performance constraints. | Use as conceptual reference for converting OSM map elements into stylized 3D scenes. |
| `demo.f4map.com` | Interactive 3D map demo. | Good UX target: rotate/zoom/pan, dense 3D map rendering, buildings, roads, landmarks. | Reference for 3D navigation quality and visual expectations. |
| `app.cityweft.com` | Web-based city/map design application. | Reference for polished urban-design UI and map interaction patterns. | Use as UX inspiration only. |
| `maps.rayon.design` | OSM-to-DXF/vector map export product. | Shows value of clean OSM export workflows for design/CAD tools. | Future: add DXF/GLB export for imported scenarios. |
| `Spatial Manager OSM to AutoCAD` | OSM import/export workflow into AutoCAD. | Reference for professional OSM-to-CAD expectations. | Future export feature only. |
| `osm2world.org` | Converts OSM data into 3D worlds. | Highly relevant for buildings, roads, terrain, and map semantics. | Use as reference for real OSM tagging to 3D visual mapping. |
| `topoexport.com` | Vector maps and 3D terrain model export for architecture/planning. | Reference for terrain/export use cases and presentation expectations. | Future optional terrain/export pipeline. |
| `vvoovv/blosm` | Blender add-on for importing Google 3D cities, OSM, and terrain. | Useful for Blender/offline visualization ideas and OSM terrain workflows. | Do not depend on it in app. Consider Blender export later. |
| `eliemichel/MapsModelsImporter` | Blender add-on/proof-of-concept for importing Google Maps/Earth captured 3D models using RenderDoc. | Shows legal/technical complexity of Google 3D assets; not suitable for direct app integration. | Avoid direct integration. Use only as proof that captured proprietary 3D data is risky. Stick to OSM/SUMO-derived geometry. |

## SUMO, Traffic Simulation, and Tutorials

| Source | What It Is | Useful Ideas | Project Decision |
|---|---|---|---|
| `eclipse-sumo/sumo` | Official open-source microscopic traffic simulator, designed for large networks and scenario creation tools. | Core simulator. Supports SUMO-GUI, TraCI, `netconvert`, `randomTrips.py`, metrics, pedestrians, intermodal simulation. | Primary backend simulation engine. Already integrated. |
| `RoadwayVR/SUMO-Traffic-Simulator-Tutorial` | SUMO tutorials covering Quick Start, NetEdit, TraCI, CAVs, energy/emissions, and SUMO2Unity. | Use for tutorial documentation, SUMO-GUI workflows, and possible Unity/VR export direction. | Reference for docs and onboarding. |
| `toruseo/UXsim` | Python vehicular traffic flow simulator for road networks. | Useful lightweight alternative model for fast flow-level simulations when SUMO is too heavy. | Do not replace SUMO. Consider later for fast preview/batch estimation. |
| `cityflow-project/CityFlowER` | Efficient realistic traffic simulator with embedded ML models. | Useful reference for ML-oriented simulation architecture and batch experiments. | Study for future scalable RL benchmark design. |
| GitHub topic `traffic-simulation` | GitHub topic index showing hundreds of public traffic simulation projects. | Discovery surface for additional references and benchmarking. | Use as ongoing research index, not an integration target. |

## RL and Adaptive Traffic Signal Control Sources

| Source | What It Is | Useful Ideas | Project Decision |
|---|---|---|---|
| `zamweis/sumo-marl-traffic-control` | Framework for training/evaluating MARL traffic-light control models in SUMO. | Directly relevant for true MARL environment design, multi-agent observations/actions/rewards, and evaluation loops. | High-priority reference for Phase MARL. |
| `ACabrejas/IEEE_SMC2020_Reward_Functions_RL_UTC` | Paper/preprint repo assessing reward functions for RL traffic signal control under real-world constraints. | Reward design: waiting time, lost time, speed, queue length, throughput. Important warning: reward choice materially changes results. | Use for reward-function module and experiment comparison. |
| `mschrader15/reinforcement-learning-sumo` | SUMO + reinforcement learning via Ray RLlib/OpenAI Gym wrapping. | Gym-style environment wrapping and RLlib integration ideas. | Reference for future Gymnasium/RLlib-compatible API. |
| `RituPande/DQL-TSC` and site | Adaptive traffic signal control using deep Q-learning and SUMO. | DQL baseline, state/action/reward framing, result presentation. | Reference for DQN baseline and documentation structure. |
| `traffic-signal-control/RL_signals` | Curated “all you need to know” RL traffic signal control resource. | Literature map and baseline taxonomy. | Use for reading list and method selection. |
| `Ujwal2910/Smart-Traffic-Signals-in-India...` | SUMO environment, DQN + target network + replay, computer vision queue estimation, Indian road scenarios. | Useful for Indian-road framing, queue-length state, switch/not-switch action, CV-to-RL concept. | Reference for India-specific scenario assumptions and DQN design. |
| `RituPande/DQL-TSC` page | Project presentation for DQL traffic signal control. | Presentation/documentation inspiration. | Use for report/demo formatting. |

## Non-RL Signal Control Sources

| Source | What It Is | Useful Ideas | Project Decision |
|---|---|---|---|
| `devolamide/fuzzy_traffic_controller` | Fuzzy logic traffic controller using scikit-fuzzy and SUMO. | Add fuzzy controller baseline between fixed-time/MaxPressure and RL. | Good next baseline. |
| `mihir-m-gandhi/Adaptive-Traffic-Signal-Timer` | YOLO-based adaptive signal timer from live images. | Computer-vision traffic density estimation and timer adjustment. | Future CV module only; not needed for core SUMO simulation. |
| `shubham001official/Smart-Adaptive-Traffic-Management-System` | YOLOv8/CCTV-based traffic analysis for adaptive timings. | Similar CV density estimation and real-time signal adjustment. | Future CV integration reference. |
| `Ammar-Bin-Amir/Traffic_Control_System` | Simple one-way traffic-flow controller. | Too simple for our main simulator. | Ignore except for beginner FSM logic. |
| `Ramaiah-Skills/Designing-a-Traffic-Signal-Control-System-with-Verilog-HDL` | Verilog FSM traffic light controller. | Useful for deterministic FSM signal logic and hardware-style state machines. | Not directly integrated; can inspire simple FSM baseline. |
| `EEEEEclectic/traffic_signal_control` | Traffic-signal-control repo. | Needs deeper file review before integration. | Keep as low-priority reference. |

## Game / Road Generation / Visual Simulation Sources

| Source | What It Is | Useful Ideas | Project Decision |
|---|---|---|---|
| `TheDuckCow/godot-road-generator` | Godot plugin for 3D highways/streets and lane-following traffic. | Useful for lane-following traffic visuals and road mesh generation. | Reference for 3D vehicle pathing; do not switch to Godot. |
| `CalNightingale/TrafficSim` | Godot traffic simulator game. | Reference for interactive visual simulation, not research metrics. | Inspiration only. |
| `whipped-cream/Traffic` | Link could not be reliably loaded in browser session. | Unknown. | Re-check later before using. |

## CAD / Map Export / Import Boundary

The CAD/map import links are useful, but not all should become dependencies. The project should avoid proprietary Google 3D capture workflows in the core product. For open-source publishability, use:

- OSM/Overpass for map source.
- SUMO `netconvert` for simulation network.
- Browser Three.js for 3D visualization.
- Optional future exporters: GLB, DXF, GeoJSON, CSV, SUMO config bundle.

## Integration Priority

### Immediate

- Keep SUMO as the simulator.
- Keep OSM location search and `netconvert` import.
- Improve Three.js world using OSM building footprints and tags.
- Add stable high-density route-generation controls.
- Add real TraCI telemetry streaming.

### Next

- Add fuzzy controller baseline from the fuzzy traffic controller idea.
- Add reward-function comparison inspired by the IEEE reward-functions paper.
- Add Gymnasium-compatible environment wrapper inspired by RLlib/SUMO projects.
- Replace current lightweight DQN with a real PyTorch DQN baseline: replay buffer, target network, epsilon schedule, checkpointing, evaluation seeds.

### Later

- Add MARL environment: one agent per traffic light, shared graph observations, independent/centralized training modes.
- Add 3D buildings/terrain from OSM tags, inspired by OSM2World/F4map/Arnis.
- Add exports: GLB/DXF/GeoJSON/SUMO scenario bundle.
- Add CV module only after core simulation and RL are reliable.

## What Not To Do

- Do not blindly merge any repo.
- Do not depend on Google Maps capture/import tools for an open-source core.
- Do not claim MARL until multi-agent training/evaluation is implemented.
- Do not treat randomTrips demand as calibrated real traffic.
- Do not use visual simulation as proof of control performance; use persisted SUMO metrics.

## Source Links

- https://github.com/earthtojake/text-to-cad
- https://github.com/cartesiancs/map3d
- https://github.com/louis-e/arnis
- https://demo.f4map.com
- https://app.cityweft.com
- https://maps.rayon.design
- https://github.com/EEEEEclectic/traffic_signal_control
- https://github.com/zamweis/sumo-marl-traffic-control
- https://github.com/ACabrejas/IEEE_SMC2020_Reward_Functions_RL_UTC
- https://github.com/CalNightingale/TrafficSim
- https://github.com/TheDuckCow/godot-road-generator
- https://github.com/whipped-cream/Traffic
- https://github.com/cityflow-project/CityFlowER
- https://github.com/shubham001official/Smart-Adaptive-Traffic-Management-System
- https://github.com/mschrader15/reinforcement-learning-sumo
- https://github.com/Ujwal2910/Smart-Traffic-Signals-in-India-using-Deep-Reinforcement-Learning-and-Advanced-Computer-Vision
- https://github.com/Ammar-Bin-Amir/Traffic_Control_System
- https://github.com/RoadwayVR/SUMO-Traffic-Simulator-Tutorial
- https://github.com/devolamide/fuzzy_traffic_controller
- https://github.com/toruseo/UXsim
- https://github.com/RituPande/DQL-TSC
- https://ritupande.github.io/DQL-TSC/
- https://github.com/traffic-signal-control/RL_signals
- https://github.com/mihir-m-gandhi/Adaptive-Traffic-Signal-Timer
- https://github.com/Ramaiah-Skills/Designing-a-Traffic-Signal-Control-System-with-Verilog-HDL
- https://github.com/topics/traffic-simulation
- https://github.com/eclipse-sumo/sumo
- https://github.com/openstreetmap
- https://www.spatialmanager.com/osm-to-autocad/
- https://osm2world.org/
- https://topoexport.com
- https://github.com/vvoovv/blosm
- https://github.com/eliemichel/MapsModelsImporter
