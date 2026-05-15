# RL Service

Python service that will own SUMO, TraCI, controllers, and RL training.

Current endpoints:

- `GET /health`
- `GET /status`
- `GET /sumo/detect`
- `POST /simulations/run-smoke-test`
- `GET /controllers`
- `GET /scenarios`
- `POST /scenarios/import-osm`
- `POST /scenarios/run-osm-smoke`
- `GET /scenarios/inspect-osm`
- `GET /scenarios/geometry`
- `POST /scenarios/run-osm-fixed-time`
- `POST /scenarios/run-osm-max-pressure`
- `POST /experiments/imported-osm/run`
- `POST /experiments/baselines/{controller_name}`
- `GET /experiments/results/{run_id}`
- `GET /experiments/exports`
- `GET /experiments/exports/{experiment_id}`
- `GET /experiments/comparison`
- `POST /experiments/run`
- `POST /training/dqn`
- `POST /training/imported-osm-dqn`

Run:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python -m marl_traffic_rl_service
```
