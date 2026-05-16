# Deployment

## Recommended Hosting

The easiest public demo setup is:

- Frontend: Vercel or Railway static Node service.
- Backend API: Railway Node service.
- RL/SUMO service: Railway Docker service.

For this project, Railway is the simplest all-in-one host because it can run the Python/SUMO Docker service. Vercel alone is not enough because SUMO and TraCI need a backend runtime.

Native `sumo-gui` is desktop software. It works locally, but normal cloud hosting can only run headless SUMO. The browser 3D world still works in hosted mode.

## Railway Deployment

Create three Railway services from the same GitHub repo.

Railway config files are already included:

```text
rl-service/railway.json
backend/railway.json
frontend/railway.json
```

These force Dockerfile builds and set health checks.

### 1. RL/SUMO Service

Create a new Railway service:

- Source: this GitHub repository.
- Root directory: `rl-service`
- Builder: Dockerfile
- Config file path: `/rl-service/railway.json`

Environment variables:

```text
PORT=8000
SUMO_HOME=/usr/share/sumo
```

The Dockerfile installs:

- `sumo`
- `sumo-tools`
- Python package dependencies
- the local RL service package

Health URL after deploy:

```text
https://<rl-service>.up.railway.app/health
```

### 2. Backend Service

Create a second Railway service:

- Source: this GitHub repository.
- Root directory: `backend`
- Builder: Dockerfile
- Config file path: `/backend/railway.json`

Environment variables:

```text
PORT=3001
RL_SERVICE_URL=https://<rl-service>.up.railway.app
```

Health URL:

```text
https://<backend>.up.railway.app/api/health
```

### 3. Frontend Service

Create a third Railway service:

- Source: this GitHub repository.
- Root directory: `frontend`
- Builder: Dockerfile
- Config file path: `/frontend/railway.json`

Environment variables:

```text
PORT=5173
VITE_BACKEND_URL=https://<backend>.up.railway.app
```

Important: `VITE_BACKEND_URL` is a build-time Vite variable. Set it before the frontend deploy builds.

Frontend URL:

```text
https://<frontend>.up.railway.app
```

## Local Docker Compose

From the repo root:

```bash
docker compose up --build
```

Local URLs:

```text
Frontend: http://localhost:5173
Backend:  http://localhost:3001/api/health
RL API:   http://localhost:8000/health
```

## What Is Included In Git

Included:

- source code
- docs
- Dockerfiles
- lockfiles
- small sample OSM scenario
- reproducible scenario import pipeline

Excluded:

- `node_modules`
- Python virtual environments
- generated experiment results
- generated SUMO route/trip files
- generated screenshots
- large downloaded OSM city networks

Users can regenerate city networks from the app using the OSM search/import workflow.

## CLI Check

Railway deployment still requires logging in to the Railway account that owns the project:

```powershell
railway login
```

Then run:

```powershell
.\scripts\railway-deploy-check.ps1 -RailwayCli "railway"
```

This script verifies the CLI and reminds you which three services to create.

## Full CLI Deployment

After authenticating Railway, this repo includes a full deployment script:

```powershell
railway login
.\scripts\railway-full-deploy.ps1 -RailwayCli "railway" -ProjectName "MARL-TrafficOpt"
```

On this Windows workspace, you can also run:

```powershell
.\deploy-railway.ps1
```

or double-click:

```text
deploy-railway.bat
```

In a non-interactive environment, set a Railway token first:

```powershell
$env:RAILWAY_TOKEN="your_railway_token"
.\scripts\railway-full-deploy.ps1 -RailwayCli "railway" -ProjectName "MARL-TrafficOpt"
```

The script:

- creates a Railway project,
- creates `rl-service`, `backend`, and `frontend` services,
- sets service variables,
- deploys each service from its folder,
- generates public Railway domains,
- wires backend to RL service and frontend to backend.
