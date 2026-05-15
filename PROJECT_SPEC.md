# MARL Traffic Signal Optimization - Project Specification

## 1. Project Motto

Build an open-source, research-ready traffic signal optimization platform that uses simulation, real map data, and multi-agent reinforcement learning to reduce congestion in urban road networks.

The final project should be honest, reproducible, and presentable: it must clearly separate demo features from validated research results.

## 2. Problem Statement

Urban intersections often operate with fixed or manually tuned signal plans. Under oversaturated traffic, this causes long queues, spillback, unnecessary delay, higher emissions, and slow emergency response.

The project will build a system where each signalized intersection acts as an agent. Agents observe traffic state, coordinate with neighboring intersections, and learn signal policies that improve network-level throughput and delay compared with fixed-time and actuated baselines.

## 3. Target Users

- Final-year engineering students presenting an intelligent transportation project.
- Researchers testing MARL traffic-control methods.
- Developers who need a clean open-source traffic optimization demo.
- Reviewers who need reproducible experiments and clear documentation.

## 4. Final Deliverables

- Web dashboard for running and visualizing traffic simulations.
- Backend API for scenarios, metrics, training jobs, and exports.
- SUMO integration through TraCI.
- OSM import pipeline for real road networks.
- Baseline controllers: fixed-time, actuated, max-pressure.
- MARL controllers: initial DQN/MAPPO-style multi-agent implementation.
- Experiment runner with reproducible seeds.
- Metrics export as CSV/JSON.
- Documentation, architecture diagrams, setup guide, and research methodology.
- Docker-based deployment.
- MIT license and clean open-source repository structure.

## 5. Core Features

### 5.1 Simulation

- Load synthetic grid networks.
- Load OpenStreetMap road networks.
- Convert map geometry into simulation-ready graph data.
- Support vehicle classes:
  - Car
  - Bus
  - Truck
  - Motorcycle
  - Emergency vehicle
- Track queues, delays, stops, throughput, emissions proxy, and safety proxy.

### 5.2 Signal Control

- Fixed-time controller.
- Actuated controller based on local queue thresholds.
- Max-pressure controller based on incoming/outgoing queue pressure.
- MARL controller with one agent per intersection.
- Emergency preemption mode.

### 5.3 Reinforcement Learning

Recommended first implementation:

- Environment wrapper around SUMO TraCI.
- State per agent:
  - Queue length by approach
  - Waiting time by lane
  - Current signal phase
  - Neighbor signal phase
  - Emergency vehicle distance
- Actions:
  - Select next phase
  - Extend current phase
  - Shorten current phase within safety constraints
- Reward:
  - Positive throughput
  - Negative delay
  - Negative queue spillback
  - Negative emergency delay
  - Safety penalty for invalid phase transitions

Training should start simple:

1. Single intersection DQN.
2. Multi-intersection independent DQN.
3. Shared-policy MARL.
4. Neighbor-aware MARL.
5. Optional MAPPO/QMIX upgrade.

### 5.4 Visualization

- 2D network view for debugging.
- 3D city/street-level view for presentation.
- Live traffic-light phase display.
- Live vehicle rendering.
- Metrics dashboard.
- Training progress charts.
- Scenario selector.

### 5.5 Backend

Backend responsibilities:

- Serve scenarios.
- Proxy OSM requests.
- Start/stop SUMO runs.
- Manage training jobs.
- Stream live simulation state through WebSocket.
- Export metrics.
- Store experiment metadata.

Recommended stack:

- Node.js + Express for web/API.
- Python service for RL training and SUMO TraCI.
- WebSocket for live telemetry.
- SQLite/PostgreSQL for experiment metadata.

### 5.6 Frontend

Recommended stack:

- Vite
- React or vanilla modular JavaScript
- Three.js for 3D visualization
- Tailwind CSS or plain CSS design system
- Chart.js/Recharts/ECharts for metrics

The frontend should be a real tool, not a landing page.

## 6. Architecture

```text
Frontend Dashboard
  |
  | REST APIs
  | WebSocket telemetry
  v
Node Backend
  |
  | scenario/config management
  v
Python RL + SUMO Service
  |
  | TraCI
  v
SUMO Simulator
```

## 7. Repository Structure

Recommended clean repository:

```text
.
├── README.md
├── LICENSE
├── docker-compose.yml
├── docs/
│   ├── architecture.md
│   ├── methodology.md
│   ├── api.md
│   └── experiments.md
├── frontend/
│   ├── package.json
│   ├── src/
│   └── public/
├── backend/
│   ├── package.json
│   └── src/
├── rl-service/
│   ├── pyproject.toml
│   ├── src/
│   └── tests/
├── scenarios/
│   ├── synthetic/
│   └── osm/
├── experiments/
│   ├── configs/
│   └── results/
└── tests/
```

## 8. Development Phases

### Phase 1 - Clean Foundation

- Create repository structure.
- Add README, license, contribution notes.
- Add frontend shell.
- Add backend health API.
- Add Docker Compose.
- Add lint/build/test scripts.

### Phase 2 - Simulation MVP

- Implement synthetic grid generator.
- Implement vehicle movement model.
- Implement traffic-light phase model.
- Add fixed-time controller.
- Add metrics collection.
- Add dashboard visualization.

### Phase 3 - OSM Pipeline

- Add Overpass API import.
- Normalize OSM roads and traffic signals.
- Convert roads to graph.
- Validate missing/invalid geometry.
- Cache city scenarios locally.

### Phase 4 - SUMO Integration

- Generate SUMO network/config files.
- Launch SUMO from backend or Python service.
- Connect TraCI.
- Read live queues, speeds, and waiting times.
- Control traffic lights through TraCI.

### Phase 5 - Baselines

- Fixed-time baseline.
- Actuated baseline.
- Max-pressure baseline.
- Scenario runner.
- Export comparable metrics.

### Phase 6 - MARL Training

- Define RL environment API.
- Implement replay buffer and agent model.
- Train single-intersection DQN.
- Extend to multi-agent training.
- Save/load trained policies.
- Add training dashboard.

### Phase 7 - Research Validation

- Run repeated experiments with seeds.
- Compare against baselines.
- Generate tables and charts.
- Document methodology and limitations.
- Prepare presentation and paper-style report.

### Phase 8 - Production Polish

- Improve UI/UX.
- Add error boundaries.
- Add logs and health checks.
- Add CI pipeline.
- Add release workflow.
- Add deployment instructions.

## 9. Metrics

Minimum metrics:

- Average vehicle delay.
- Average queue length.
- Maximum queue length.
- Throughput.
- Number of stops.
- Travel time.
- Emergency response time.
- Emissions proxy or SUMO emissions output.
- Controller compute time.

Experiment reports should include:

- Mean.
- Standard deviation.
- Confidence interval.
- Number of seeds.
- Scenario configuration.
- Hardware/software environment.

## 10. Quality Requirements

- No fake benchmark claims.
- No hardcoded research results.
- Every reported metric must come from an experiment output file.
- App must run from a fresh clone.
- Build must pass.
- Backend health endpoint must pass.
- Tests must cover graph conversion, metrics, and controller decisions.
- Docs must explain limitations clearly.

## 11. Required External Tools

- Node.js LTS.
- Python 3.11+.
- SUMO.
- Git.
- Docker Desktop.
- Optional GPU support for training.

## 12. Open-Source Readiness Checklist

- MIT license.
- Clean README.
- `.gitignore`.
- No committed `node_modules`.
- No committed virtual environments.
- No committed build output unless intentional.
- No secrets or API keys.
- Reproducible setup commands.
- Clear roadmap.
- Clear current status.

## 13. Immediate Next Step

Start from a clean repository and implement Phase 1 only:

1. Create the folder structure.
2. Add minimal frontend.
3. Add backend health API.
4. Add Docker Compose.
5. Add documentation.
6. Verify fresh install and build.

Do not implement MARL until the simulation, metrics, baselines, and SUMO integration are stable.
