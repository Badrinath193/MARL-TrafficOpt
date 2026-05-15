# Architecture

## System Shape

```text
Frontend Dashboard
  |
  | REST and WebSocket
  v
Backend API Gateway
  |
  | service calls
  v
RL Service
  |
  | TraCI
  v
SUMO
```

## Responsibilities

### Frontend

- Show project status.
- Display scenarios, simulations, and experiment results.
- Render scenario network geometry previews from the API.
- Later: live telemetry charts, 3D visualization, training monitor, scenario editor.

### Backend

- Stable HTTP API for the web client.
- Proxy/status layer for the RL service.
- Later: telemetry broker, scenario metadata, user-facing export endpoints.

### RL Service

- Owns SUMO lifecycle.
- Owns TraCI integration.
- Implements controllers, environments, training, and evaluation.
- Owns scenario catalog metadata and result comparison summaries.
- Extracts SUMO network geometry for frontend inspection.
- Later: Gym/PettingZoo-compatible environment.

### Scenario Tools

- OSM download and validation.
- SUMO network generation.
- Scenario repair and reproducibility checks.

## Design Rule

Rendering and research must stay separate. The frontend can be beautiful, but benchmark claims must come only from experiment outputs.
