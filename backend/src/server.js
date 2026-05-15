import express from 'express';
import cors from 'cors';

const app = express();
const port = Number(process.env.PORT || 3001);
const rlServiceUrl = process.env.RL_SERVICE_URL || 'http://127.0.0.1:8000';

app.use(cors());
app.use(express.json());

app.get('/api/health', async (req, res) => {
  const rl = await checkRlService();
  res.json({
    ok: true,
    service: 'marl-trafficopt-backend',
    version: '0.1.0',
    phase: 'phase-16-interactive-sumo-osm',
    capabilities: ['health', 'rl-service-proxy', 'traci-baseline-run-proxy', 'experiment-run-proxy', 'dqn-training-proxy', 'imported-osm-dqn-proxy', 'scenario-catalog-proxy', 'scenario-geometry-proxy', 'sumo-gui-launch-proxy', 'comparison-proxy', 'osm-import-proxy', 'osm-search-import-proxy', 'osm-smoke-run-proxy', 'osm-inspection-proxy', 'osm-fixed-time-proxy', 'osm-max-pressure-proxy', 'imported-osm-experiment-proxy', 'experiment-export-browser-proxy', 'run-telemetry-proxy'],
    dependencies: {
      rlService: rl
    }
  });
});

app.get('/api/status', (req, res) => {
  res.json({
    ok: true,
    currentPhase: 'Phase 16',
    nextMilestone: 'Live browser telemetry streaming and 3D city views'
  });
});

app.get('/api/sumo/detect', async (req, res) => {
  const result = await callRlService('/sumo/detect');
  res.status(result.status).json(result.body);
});

app.post('/api/simulations/run-smoke-test', async (req, res) => {
  const result = await callRlService('/simulations/run-smoke-test', { method: 'POST' });
  res.status(result.status).json(result.body);
});

app.post('/api/sumo/launch-gui', async (req, res) => {
  const result = await callRlService('/sumo/launch-gui', {
    method: 'POST',
    body: req.body || {},
    timeoutMs: 120000
  });
  res.status(result.status).json(result.body);
});

app.get('/api/controllers', async (req, res) => {
  const result = await callRlService('/controllers');
  res.status(result.status).json(result.body);
});

app.get('/api/scenarios', async (req, res) => {
  const result = await callRlService('/scenarios');
  res.status(result.status).json(result.body);
});

app.get('/api/scenarios/geometry', async (req, res) => {
  const params = new URLSearchParams();
  if(req.query.scenario_id) {
    params.set('scenario_id', req.query.scenario_id);
  }
  const suffix = params.toString() ? `?${params.toString()}` : '';
  const result = await callRlService(`/scenarios/geometry${suffix}`);
  res.status(result.status).json(result.body);
});

app.post('/api/scenarios/import-osm', async (req, res) => {
  const result = await callRlService('/scenarios/import-osm', {
    method: 'POST',
    body: req.body || {},
    timeoutMs: 120000
  });
  res.status(result.status).json(result.body);
});

app.post('/api/scenarios/search-import-osm', async (req, res) => {
  const result = await callRlService('/scenarios/search-import-osm', {
    method: 'POST',
    body: req.body || {},
    timeoutMs: 180000
  });
  res.status(result.status).json(result.body);
});

app.post('/api/scenarios/run-osm-smoke', async (req, res) => {
  const result = await callRlService('/scenarios/run-osm-smoke', {
    method: 'POST',
    body: req.body || {},
    timeoutMs: 180000
  });
  res.status(result.status).json(result.body);
});

app.get('/api/scenarios/inspect-osm', async (req, res) => {
  const params = new URLSearchParams();
  if(req.query.scenario_id) {
    params.set('scenario_id', req.query.scenario_id);
  }
  const suffix = params.toString() ? `?${params.toString()}` : '';
  const result = await callRlService(`/scenarios/inspect-osm${suffix}`);
  res.status(result.status).json(result.body);
});

app.post('/api/scenarios/run-osm-fixed-time', async (req, res) => {
  const result = await callRlService('/scenarios/run-osm-fixed-time', {
    method: 'POST',
    body: req.body || {},
    timeoutMs: 180000
  });
  res.status(result.status).json(result.body);
});

app.post('/api/scenarios/run-osm-max-pressure', async (req, res) => {
  const result = await callRlService('/scenarios/run-osm-max-pressure', {
    method: 'POST',
    body: req.body || {},
    timeoutMs: 180000
  });
  res.status(result.status).json(result.body);
});

app.post('/api/experiments/imported-osm/run', async (req, res) => {
  const result = await callRlService('/experiments/imported-osm/run', {
    method: 'POST',
    body: req.body || {},
    timeoutMs: 240000
  });
  res.status(result.status).json(result.body);
});

app.post('/api/experiments/baselines/:controllerName', async (req, res) => {
  const result = await callRlService(`/experiments/baselines/${encodeURIComponent(req.params.controllerName)}`, {
    method: 'POST'
  });
  res.status(result.status).json(result.body);
});

app.get('/api/experiments/results', async (req, res) => {
  const result = await callRlService('/experiments/results');
  res.status(result.status).json(result.body);
});

app.get('/api/experiments/results/:runId', async (req, res) => {
  const result = await callRlService(`/experiments/results/${encodeURIComponent(req.params.runId)}`);
  res.status(result.status).json(result.body);
});

app.get('/api/experiments/exports', async (req, res) => {
  const result = await callRlService('/experiments/exports');
  res.status(result.status).json(result.body);
});

app.get('/api/experiments/exports/:experimentId', async (req, res) => {
  const result = await callRlService(`/experiments/exports/${encodeURIComponent(req.params.experimentId)}`);
  res.status(result.status).json(result.body);
});

app.get('/api/experiments/comparison', async (req, res) => {
  const params = new URLSearchParams();
  if(req.query.scenario_id) {
    params.set('scenario_id', req.query.scenario_id);
  }
  if(req.query.demand_profile) {
    params.set('demand_profile', req.query.demand_profile);
  }
  const suffix = params.toString() ? `?${params.toString()}` : '';
  const result = await callRlService(`/experiments/comparison${suffix}`);
  res.status(result.status).json(result.body);
});

app.post('/api/experiments/run', async (req, res) => {
  const result = await callRlService('/experiments/run', {
    method: 'POST',
    body: req.body || {},
    timeoutMs: 180000
  });
  res.status(result.status).json(result.body);
});

app.post('/api/training/dqn', async (req, res) => {
  const result = await callRlService('/training/dqn', {
    method: 'POST',
    body: req.body || {},
    timeoutMs: 240000
  });
  res.status(result.status).json(result.body);
});

app.post('/api/training/imported-osm-dqn', async (req, res) => {
  const result = await callRlService('/training/imported-osm-dqn', {
    method: 'POST',
    body: req.body || {},
    timeoutMs: 240000
  });
  res.status(result.status).json(result.body);
});

async function checkRlService() {
  try {
    const response = await fetch(`${rlServiceUrl}/health`, { signal: AbortSignal.timeout(1500) });
    if(!response.ok) {
      return { ok: false, url: rlServiceUrl, status: response.status };
    }
    const data = await response.json();
    return { ok: true, url: rlServiceUrl, service: data.service, version: data.version };
  } catch (error) {
    return { ok: false, url: rlServiceUrl, error: error.message };
  }
}

async function callRlService(path, options = {}) {
  try {
    const response = await fetch(`${rlServiceUrl}${path}`, {
      method: options.method || 'GET',
      headers: { 'content-type': 'application/json' },
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: AbortSignal.timeout(options.timeoutMs || 35000)
    });
    const body = await response.json();
    return { status: response.status, body };
  } catch (error) {
    return {
      status: 503,
      body: {
        ok: false,
        error: 'RL service unavailable',
        detail: error.message,
        rlServiceUrl
      }
    };
  }
}

app.listen(port, () => {
  console.log(`Backend listening on http://localhost:${port}`);
});
