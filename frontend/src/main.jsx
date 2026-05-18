import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrainCircuit, CheckCircle2, CircleAlert, GitBranch, MonitorPlay, Pause, Play, Route, Search, Server } from 'lucide-react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';
import { motion } from 'framer-motion';
import { animate as animeAnimate } from 'animejs';
import './styles.css';

gsap.registerPlugin(useGSAP);

const runtimeConfig = window.__MARL_TRAFFICOPT_CONFIG__ || {};
const backendUrl = runtimeConfig.BACKEND_URL || import.meta.env.VITE_BACKEND_URL || 'http://localhost:3001';

function App() {
  const shellRef = useRef(null);
  const [backend, setBackend] = useState({ state: 'loading' });
  const [sumo, setSumo] = useState({ state: 'loading' });
  const [smoke, setSmoke] = useState({ state: 'idle' });
  const [controllers, setControllers] = useState({ state: 'loading', data: [] });
  const [scenarios, setScenarios] = useState({ state: 'loading', data: [] });
  const [geometry, setGeometry] = useState({ state: 'idle', data: null });
  const [activeRun, setActiveRun] = useState(null);
  const [guiLaunch, setGuiLaunch] = useState({ state: 'idle' });
  const [baseline, setBaseline] = useState({ state: 'idle' });
  const [experiment, setExperiment] = useState({ state: 'idle' });
  const [dqnTraining, setDqnTraining] = useState({ state: 'idle' });
  const [importedDqnTraining, setImportedDqnTraining] = useState({ state: 'idle' });
  const [demandProfile, setDemandProfile] = useState('balanced');
  const [selectedScenario, setSelectedScenario] = useState('synthetic/one_intersection_balanced');
  const [dqnEpisodes, setDqnEpisodes] = useState(4);
  const [results, setResults] = useState([]);
  const [exportsList, setExportsList] = useState([]);
  const [selectedExport, setSelectedExport] = useState({ state: 'idle' });
  const [comparison, setComparison] = useState({ state: 'loading', data: null });
  const [osmImport, setOsmImport] = useState({
    state: 'idle',
    sourcePath: 'scenarios/osm/sample-mini-cross.osm.xml',
    displayName: 'Sample Mini Cross'
  });
  const [osmSearch, setOsmSearch] = useState({
    state: 'idle',
    query: 'MG Road Bengaluru',
    displayName: ''
  });
  const [osmSmoke, setOsmSmoke] = useState({ state: 'idle' });
  const [osmInspection, setOsmInspection] = useState({ state: 'idle' });
  const [osmFixedTime, setOsmFixedTime] = useState({ state: 'idle' });
  const [osmMaxPressure, setOsmMaxPressure] = useState({ state: 'idle' });
  const [osmExperiment, setOsmExperiment] = useState({ state: 'idle' });

  useGSAP(() => {
    gsap.from('.hero, .feature-card, .panel', {
      autoAlpha: 0,
      y: 18,
      duration: 0.55,
      stagger: 0.04,
      ease: 'power2.out'
    });
  }, { scope: shellRef });

  useEffect(() => {
    fetch(`${backendUrl}/api/health`)
      .then((response) => response.json())
      .then((data) => setBackend({ state: 'ok', data }))
      .catch((error) => setBackend({ state: 'error', error: error.message }));

    fetch(`${backendUrl}/api/sumo/detect`)
      .then((response) => response.json())
      .then((data) => setSumo({ state: 'ok', data }))
      .catch((error) => setSumo({ state: 'error', error: error.message }));

    fetch(`${backendUrl}/api/controllers`)
      .then((response) => response.json())
      .then((data) => setControllers({ state: 'ok', data: data.controllers || [] }))
      .catch((error) => setControllers({ state: 'error', error: error.message, data: [] }));

    fetch(`${backendUrl}/api/scenarios`)
      .then((response) => response.json())
      .then((data) => setScenarios({ state: 'ok', data: data.scenarios || [] }))
      .catch((error) => setScenarios({ state: 'error', error: error.message, data: [] }));

    refreshResults();
    refreshExports();
    refreshComparison();
    loadGeometry(selectedScenario);
  }, []);

  function runSmokeTest() {
    setSmoke({ state: 'running' });
    fetch(`${backendUrl}/api/simulations/run-smoke-test`, { method: 'POST' })
      .then((response) => response.json())
      .then((data) => {
        setSmoke({ state: 'done', data });
        if(data.time_series?.length) {
          setActiveRun(data);
        }
      })
      .catch((error) => setSmoke({ state: 'error', error: error.message }));
  }

  function runBaseline(controllerName) {
    setBaseline({ state: 'running', controllerName });
    fetch(`${backendUrl}/api/experiments/baselines/${controllerName}`, { method: 'POST' })
      .then((response) => response.json())
      .then((data) => {
        setBaseline({ state: 'done', data });
        if(data.time_series?.length) {
          setActiveRun(data);
        }
        refreshResults();
      })
      .catch((error) => setBaseline({ state: 'error', error: error.message }));
  }

  function refreshResults() {
    fetch(`${backendUrl}/api/experiments/results`)
      .then((response) => response.json())
      .then((data) => setResults(data.results || []))
      .catch(() => setResults([]));
  }

  function refreshExports() {
    fetch(`${backendUrl}/api/experiments/exports`)
      .then((response) => response.json())
      .then((data) => setExportsList(data.exports || []))
      .catch(() => setExportsList([]));
  }

  function loadExport(experimentId) {
    setSelectedExport({ state: 'loading' });
    fetch(`${backendUrl}/api/experiments/exports/${experimentId}`)
      .then((response) => response.json())
      .then((data) => setSelectedExport({ state: 'done', data }))
      .catch((error) => setSelectedExport({ state: 'error', error: error.message }));
  }

  function refreshComparison(scenarioId = selectedScenario) {
    setComparison((current) => ({ ...current, state: 'loading' }));
    fetch(`${backendUrl}/api/experiments/comparison?scenario_id=${encodeURIComponent(scenarioId)}`)
      .then((response) => response.json())
      .then((data) => setComparison({ state: 'ok', data: data.comparison }))
      .catch((error) => setComparison({ state: 'error', error: error.message, data: null }));
  }

  function updateScenario(scenarioId) {
    setSelectedScenario(scenarioId);
    const scenario = scenarios.data.find((item) => item.scenario_id === scenarioId);
    if(scenario?.demand_profile) {
      setDemandProfile(scenario.demand_profile);
    }
    refreshComparison(scenarioId);
    loadGeometry(scenarioId);
  }

  function loadGeometry(scenarioId = selectedScenario) {
    setGeometry({ state: 'loading', data: null });
    fetch(`${backendUrl}/api/scenarios/geometry?scenario_id=${encodeURIComponent(scenarioId)}`)
      .then((response) => response.json())
      .then((data) => setGeometry({ state: data.ok ? 'done' : 'error', data, error: data.error || data.reason }))
      .catch((error) => setGeometry({ state: 'error', data: null, error: error.message }));
  }

  function importOsmScenario() {
    setOsmImport((current) => ({ ...current, state: 'running' }));
    fetch(`${backendUrl}/api/scenarios/import-osm`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        source_path: osmImport.sourcePath,
        display_name: osmImport.displayName,
        run_netconvert: true
      })
    })
      .then((response) => response.json())
      .then((data) => {
        setOsmImport((current) => ({ ...current, state: 'done', data }));
        if(data.scenario?.scenario_id) {
          selectLoadedScenario(data.scenario);
          if(data.scenario.status === 'ready') {
            runOsmSmoke(data.scenario.scenario_id);
          }
        }
        return fetch(`${backendUrl}/api/scenarios`);
      })
      .then((response) => response?.json())
      .then((data) => {
        if(data?.scenarios) {
          setScenarios({ state: 'ok', data: data.scenarios });
        }
      })
      .catch((error) => setOsmImport((current) => ({ ...current, state: 'error', error: error.message })));
  }

  function searchImportOsmScenario() {
    setOsmSearch((current) => ({ ...current, state: 'running' }));
    setOsmSmoke({ state: 'idle' });
    fetch(`${backendUrl}/api/scenarios/search-import-osm`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        query: osmSearch.query,
        display_name: osmSearch.displayName || undefined,
        run_netconvert: true
      })
    })
      .then((response) => response.json())
      .then((data) => {
        setOsmSearch((current) => ({ ...current, state: 'done', data }));
        if(data.scenario?.files?.osm) {
          setOsmImport((current) => ({
            ...current,
            sourcePath: data.scenario.files.osm,
            displayName: data.scenario.display_name || current.displayName
          }));
        }
        if(data.scenario?.scenario_id) {
          selectLoadedScenario(data.scenario);
          if(data.scenario.status === 'ready') {
            runOsmSmoke(data.scenario.scenario_id);
          }
        }
        return fetch(`${backendUrl}/api/scenarios`);
      })
      .then((response) => response?.json())
      .then((data) => {
        if(data?.scenarios) {
          setScenarios({ state: 'ok', data: data.scenarios });
        }
      })
      .catch((error) => setOsmSearch((current) => ({ ...current, state: 'error', error: error.message })));
  }

  function selectLoadedScenario(scenario) {
    setSelectedScenario(scenario.scenario_id);
    if(scenario.demand_profile) {
      setDemandProfile(scenario.demand_profile);
    }
    refreshComparison(scenario.scenario_id);
    loadGeometry(scenario.scenario_id);
  }

  function launchGui() {
    setGuiLaunch({ state: 'running' });
    fetch(`${backendUrl}/api/sumo/launch-gui`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        scenario_id: selectedScenario,
        seed: 1,
        end_time: 1500,
        period: 1,
        demand_profile: demandProfile
      })
    })
      .then((response) => response.json())
      .then((data) => setGuiLaunch({ state: 'done', data }))
      .catch((error) => setGuiLaunch({ state: 'error', error: error.message }));
  }

  function runOsmSmoke(scenarioId = selectedScenario) {
    const targetScenario = typeof scenarioId === 'string' ? scenarioId : selectedScenario;
    setOsmSmoke({ state: 'running' });
    fetch(`${backendUrl}/api/scenarios/run-osm-smoke`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        scenario_id: targetScenario,
        seed: 1,
        end_time: 1500,
        period: 1
      })
    })
      .then((response) => response.json())
      .then((data) => {
        setOsmSmoke({ state: 'done', data });
        if(data.time_series?.length) {
          setActiveRun(data);
        }
        refreshResults();
      })
      .catch((error) => setOsmSmoke({ state: 'error', error: error.message }));
  }

  function inspectOsmScenario() {
    setOsmInspection({ state: 'running' });
    fetch(`${backendUrl}/api/scenarios/inspect-osm?scenario_id=${encodeURIComponent(selectedScenario)}`)
      .then((response) => response.json())
      .then((data) => setOsmInspection({ state: 'done', data }))
      .catch((error) => setOsmInspection({ state: 'error', error: error.message }));
  }

  function runOsmFixedTime() {
    setOsmFixedTime({ state: 'running' });
    fetch(`${backendUrl}/api/scenarios/run-osm-fixed-time`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        scenario_id: selectedScenario,
        seed: 2,
        end_time: 1500,
        period: 1,
        green_steps: 30
      })
    })
      .then((response) => response.json())
      .then((data) => {
        setOsmFixedTime({ state: 'done', data });
        if(data.time_series?.length) {
          setActiveRun(data);
        }
        refreshResults();
        refreshComparison();
      })
      .catch((error) => setOsmFixedTime({ state: 'error', error: error.message }));
  }

  function runOsmMaxPressure() {
    setOsmMaxPressure({ state: 'running' });
    fetch(`${backendUrl}/api/scenarios/run-osm-max-pressure`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        scenario_id: selectedScenario,
        seed: 4,
        end_time: 1500,
        period: 1,
        min_green: 10
      })
    })
      .then((response) => response.json())
      .then((data) => {
        setOsmMaxPressure({ state: 'done', data });
        if(data.time_series?.length) {
          setActiveRun(data);
        }
        refreshResults();
        refreshComparison();
      })
      .catch((error) => setOsmMaxPressure({ state: 'error', error: error.message }));
  }

  function runImportedOsmExperiment() {
    setOsmExperiment({ state: 'running' });
    fetch(`${backendUrl}/api/experiments/imported-osm/run`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        scenario_id: selectedScenario,
        controllers: ['osm_open_loop', 'osm_fixed_time', 'osm_max_pressure'],
        seeds: [1, 2],
        end_time: 1200,
        period: 1
      })
    })
      .then((response) => response.json())
      .then((data) => {
        setOsmExperiment({ state: 'done', data });
        refreshResults();
        refreshExports();
        refreshComparison();
      })
      .catch((error) => setOsmExperiment({ state: 'error', error: error.message }));
  }

  function runExperiment() {
    setExperiment({ state: 'running' });
    fetch(`${backendUrl}/api/experiments/run`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        controllers: ['fixed_time', 'actuated', 'max_pressure'],
        seeds: [1, 2, 3],
        scenario_id: selectedScenario
      })
    })
      .then((response) => response.json())
      .then((data) => {
        setExperiment({ state: 'done', data });
        refreshResults();
        refreshComparison();
      })
      .catch((error) => setExperiment({ state: 'error', error: error.message }));
  }

  function trainDqn() {
    setDqnTraining({ state: 'running' });
    fetch(`${backendUrl}/api/training/dqn`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        episodes: Number(dqnEpisodes),
        seed: 11,
        scenario_id: selectedScenario
      })
    })
      .then((response) => response.json())
      .then((data) => {
        setDqnTraining({ state: 'done', data });
        refreshResults();
        refreshComparison();
      })
      .catch((error) => setDqnTraining({ state: 'error', error: error.message }));
  }

  function trainImportedDqn() {
    setImportedDqnTraining({ state: 'running' });
    fetch(`${backendUrl}/api/training/imported-osm-dqn`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        scenario_id: selectedScenario,
        episodes: 2,
        seed: 21,
        end_time: 120,
        period: 10,
        min_green: 10
      })
    })
      .then((response) => response.json())
      .then((data) => {
        setImportedDqnTraining({ state: 'done', data });
        refreshResults();
        refreshExports();
        refreshComparison();
      })
      .catch((error) => setImportedDqnTraining({ state: 'error', error: error.message }));
  }

  return (
    <motion.main
      className="app-shell"
      ref={shellRef}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
    >
      <section className="hero">
        <div>
          <p className="eyebrow">Phase 16 Interactive Simulation</p>
          <h1>Traffic Simulation Console</h1>
          <p className="lede">
            Search OSM, generate SUMO networks, launch SUMO-GUI, run TraCI controllers,
            and inspect telemetry from one workspace.
          </p>
        </div>
        <StatusCard status={backend} sumo={sumo} />
      </section>

      <section className="grid">
        <FeatureCard icon={<Server />} title="Service Layer" text="Backend and RL service health APIs are the first contract." />
        <FeatureCard icon={<Route />} title="Scenario Viewer" text="SUMO geometry and telemetry replay are inspectable from the dashboard." />
        <FeatureCard icon={<MonitorPlay />} title="SUMO-GUI" text="Launch native SUMO-GUI for the selected scenario when desktop SUMO tools are installed." />
        <FeatureCard icon={<GitBranch />} title="Baselines Before MARL" text="Fixed-time, actuated, and MaxPressure controllers come before learning claims." />
        <FeatureCard icon={<BrainCircuit />} title="Trainable RL" text="DQN evaluations can now be compared against baseline result records." />
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Find Or Import OSM Scenario</h2>
            <p>Search an OSM location through Nominatim/Overpass, or import a local OSM XML extract.</p>
          </div>
          <button className="action-button" onClick={searchImportOsmScenario} disabled={osmSearch.state === 'running'}>
            <Search size={16} />
            {osmSearch.state === 'running' ? 'Working...' : 'Search, Import & Simulate'}
          </button>
        </div>
        <div className="form-grid">
          <label>
            Location Search
            <input
              value={osmSearch.query}
              onChange={(event) => setOsmSearch((current) => ({ ...current, query: event.target.value }))}
              placeholder="Search a road, junction, neighborhood, or city block"
            />
          </label>
          <label>
            Display Name
            <input
              value={osmSearch.displayName}
              onChange={(event) => setOsmSearch((current) => ({ ...current, displayName: event.target.value }))}
              placeholder="Optional"
            />
          </label>
        </div>
        <SmokeResult result={osmSearch} />

        <div className="panel-header subheader">
          <div>
            <h2>Local OSM File</h2>
            <p>Use this when you already have an `.osm.xml` file on disk.</p>
          </div>
          <button className="action-button" onClick={importOsmScenario} disabled={osmImport.state === 'running'}>
            {osmImport.state === 'running' ? 'Importing...' : 'Import OSM'}
          </button>
        </div>
        <div className="form-grid">
          <label>
            Source Path
            <input
              value={osmImport.sourcePath}
              onChange={(event) => setOsmImport((current) => ({ ...current, sourcePath: event.target.value }))}
            />
          </label>
          <label>
            Display Name
            <input
              value={osmImport.displayName}
              onChange={(event) => setOsmImport((current) => ({ ...current, displayName: event.target.value }))}
            />
          </label>
        </div>
        <SmokeResult result={osmImport} />
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Scenario</h2>
            <p>Select the benchmark scenario used by multi-seed experiments and DQN training.</p>
          </div>
          <div className="actions-row">
            <select value={selectedScenario} onChange={(event) => updateScenario(event.target.value)}>
              {scenarios.data.map((scenario) => (
                <option key={scenario.scenario_id} value={scenario.scenario_id}>{scenario.display_name}</option>
              ))}
            </select>
            <button className="action-button secondary" onClick={() => runOsmSmoke()} disabled={osmSmoke.state === 'running'}>
              {osmSmoke.state === 'running' ? 'Running...' : 'Run OSM Smoke'}
            </button>
            <button className="action-button secondary" onClick={inspectOsmScenario} disabled={osmInspection.state === 'running'}>
              {osmInspection.state === 'running' ? 'Inspecting...' : 'Inspect OSM'}
            </button>
            <button className="action-button" onClick={runOsmFixedTime} disabled={osmFixedTime.state === 'running'}>
              {osmFixedTime.state === 'running' ? 'Running...' : 'Run OSM Fixed-Time'}
            </button>
            <button className="action-button" onClick={runOsmMaxPressure} disabled={osmMaxPressure.state === 'running'}>
              {osmMaxPressure.state === 'running' ? 'Running...' : 'Run OSM MaxPressure'}
            </button>
            <button className="action-button" onClick={runImportedOsmExperiment} disabled={osmExperiment.state === 'running'}>
              {osmExperiment.state === 'running' ? 'Running...' : 'Run OSM Experiment'}
            </button>
            <button className="action-button gui" onClick={launchGui} disabled={guiLaunch.state === 'running'}>
              <MonitorPlay size={16} />
              {guiLaunch.state === 'running' ? 'Launching...' : 'Open SUMO-GUI'}
            </button>
          </div>
        </div>
        <ScenarioGrid scenarios={scenarios.data} selectedScenario={selectedScenario} />
        <ThreeTrafficWorld geometry={geometry} run={activeRun} />
        <NetworkViewer geometry={geometry} />
        <SimulationReplay run={activeRun} geometry={geometry} />
        <SmokeResult result={guiLaunch} />
        <SmokeResult result={osmSmoke} />
        <SmokeResult result={osmInspection} />
        <SmokeResult result={osmFixedTime} />
        <SmokeResult result={osmMaxPressure} />
        <SmokeResult result={osmExperiment} />
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>SUMO Smoke Test</h2>
            <p>Runs the synthetic one-intersection scenario through the RL service when SUMO is installed.</p>
          </div>
          <button className="action-button" onClick={runSmokeTest} disabled={smoke.state === 'running'}>
            {smoke.state === 'running' ? 'Running...' : 'Run Smoke Test'}
          </button>
        </div>
        <SmokeResult result={smoke} />
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Baseline Controllers</h2>
            <p>Run TraCI-controlled baselines against the current one-intersection SUMO scenario.</p>
          </div>
        </div>
        <div className="controller-grid">
          {controllers.data.map((controller) => (
            <article className="controller-card" key={controller.name}>
              <h3>{controller.display_name}</h3>
              <p>{controller.description}</p>
              <small>{controller.execution_mode}</small>
              <button className="action-button" onClick={() => runBaseline(controller.name)} disabled={baseline.state === 'running'}>
                {baseline.state === 'running' && baseline.controllerName === controller.name ? 'Running...' : 'Run'}
              </button>
            </article>
          ))}
        </div>
        <SmokeResult result={baseline} />
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Saved Experiment Results</h2>
            <p>Results are written to <code>experiments/results/</code>.</p>
          </div>
          <button className="action-button secondary" onClick={refreshResults}>Refresh</button>
        </div>
        <ResultsTable results={results} />
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Controller Comparison</h2>
            <p>Summarizes saved non-training runs for the selected scenario.</p>
          </div>
          <button className="action-button secondary" onClick={() => refreshComparison()}>Refresh</button>
        </div>
        <ComparisonTable comparison={comparison} />
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Experiment Exports</h2>
            <p>Browse aggregate JSON/CSV bundles written to <code>experiments/exports/</code>.</p>
          </div>
          <button className="action-button secondary" onClick={refreshExports}>Refresh</button>
        </div>
        <ExportsTable exportsList={exportsList} onSelect={loadExport} />
        <ExportDetail result={selectedExport} />
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Multi-Seed Experiment</h2>
            <p>Runs all baselines over seeds 1, 2, and 3, then writes JSON and CSV exports.</p>
          </div>
          <div className="actions-row">
            <button className="action-button" onClick={runExperiment} disabled={experiment.state === 'running'}>
              {experiment.state === 'running' ? 'Running...' : 'Run Experiment'}
            </button>
          </div>
        </div>
        <SmokeResult result={experiment} />
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Single-Intersection DQN</h2>
            <p>Trains a lightweight DQN-style controller, runs a greedy evaluation, and exports the bundle.</p>
          </div>
          <div className="actions-row">
            <select value={dqnEpisodes} onChange={(event) => setDqnEpisodes(event.target.value)}>
              <option value="2">2 Episodes</option>
              <option value="4">4 Episodes</option>
              <option value="6">6 Episodes</option>
            </select>
            <button className="action-button" onClick={trainDqn} disabled={dqnTraining.state === 'running'}>
              {dqnTraining.state === 'running' ? 'Training...' : 'Train DQN'}
            </button>
          </div>
        </div>
        <SmokeResult result={dqnTraining} />
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Imported OSM DQN</h2>
            <p>Trains independent lightweight DQN agents for the selected imported OSM network.</p>
          </div>
          <button className="action-button" onClick={trainImportedDqn} disabled={importedDqnTraining.state === 'running'}>
            {importedDqnTraining.state === 'running' ? 'Training...' : 'Train Imported DQN'}
          </button>
        </div>
        <SmokeResult result={importedDqnTraining} />
      </section>
    </motion.main>
  );
}

function StatusCard({ status, sumo }) {
  const ok = status.state === 'ok' && status.data?.ok;
  const sumoReady = sumo.state === 'ok' && sumo.data?.tools?.ready;
  return (
    <aside className={`status-card ${ok ? 'ok' : status.state}`}>
      {ok ? <CheckCircle2 /> : <CircleAlert />}
      <div>
        <h2>Backend Status</h2>
        <p>{ok ? 'Connected' : status.state === 'loading' ? 'Checking...' : 'Unavailable'}</p>
        {status.data?.dependencies?.rlService && (
          <small>RL service: {status.data.dependencies.rlService.ok ? 'connected' : 'not connected'}</small>
        )}
        {sumo.state !== 'loading' && (
          <small>SUMO tools: {sumoReady ? 'ready' : 'not detected'}</small>
        )}
        {status.error && <small>{status.error}</small>}
      </div>
    </aside>
  );
}

function SmokeResult({ result }) {
  if(result.state === 'idle') {
    return null;
  }
  if(result.state === 'running') {
    return <div className="result-summary running">Running...</div>;
  }
  if(result.state === 'error') {
    return <div className="result-summary error">{result.error}</div>;
  }
  const data = result.data || {};
  const metrics = data.metrics || {};
  const scenario = data.scenario_id || data.scenario?.scenario_id || data.scenario || data.scenario?.display_name;
  const statusText = data.ok ? 'Completed' : data.skipped ? 'Skipped' : 'Failed';
  return (
    <details className={`result-details ${data.ok ? 'ok' : 'error'}`}>
      <summary>
        <span>{statusText}</span>
        {scenario && <small>{scenario}</small>}
        {metrics.vehicles_arrived !== undefined && <small>{metrics.vehicles_arrived} arrived</small>}
        {metrics.average_waiting_time_s !== undefined && <small>{metrics.average_waiting_time_s}s avg wait</small>}
      </summary>
      <pre className="result-box">
        {JSON.stringify(data, null, 2)}
      </pre>
    </details>
  );
}

function FeatureCard({ icon, title, text }) {
  return (
    <motion.article className="feature-card" whileHover={{ y: -3, borderColor: 'rgba(34, 197, 94, 0.48)' }} transition={{ duration: 0.18 }}>
      <div className="icon">{icon}</div>
      <h2>{title}</h2>
      <p>{text}</p>
    </motion.article>
  );
}

function ScenarioGrid({ scenarios, selectedScenario }) {
  if(!scenarios.length) {
    return <pre className="result-box">No scenarios loaded.</pre>;
  }
  return (
    <div className="scenario-grid">
      {scenarios.map((scenario) => (
        <article className={`scenario-card ${scenario.scenario_id === selectedScenario ? 'selected' : ''}`} key={scenario.scenario_id}>
          <h3>{scenario.display_name}</h3>
          <p>{scenario.description}</p>
          <small>{scenario.demand_profile} · {scenario.status}</small>
        </article>
      ))}
    </div>
  );
}

function NetworkViewer({ geometry }) {
  if(geometry.state === 'idle' || geometry.state === 'loading') {
    return <pre className="result-box">Loading network geometry...</pre>;
  }
  if(geometry.state === 'error') {
    return <pre className="result-box error">{geometry.error || 'Geometry unavailable'}</pre>;
  }
  const data = geometry.data;
  const bounds = data.bounds || { min_x: 0, min_y: 0, max_x: 1, max_y: 1 };
  const width = Math.max(1, bounds.max_x - bounds.min_x);
  const height = Math.max(1, bounds.max_y - bounds.min_y);
  const pad = 24;
  const viewWidth = 720;
  const viewHeight = 360;
  const scale = Math.min((viewWidth - pad * 2) / width, (viewHeight - pad * 2) / height);
  const project = (point) => ({
    x: pad + (point.x - bounds.min_x) * scale,
    y: viewHeight - pad - (point.y - bounds.min_y) * scale
  });
  return (
    <div className="network-viewer">
      <div className="viewer-meta">
        <span>{data.summary?.edges ?? 0} edges</span>
        <span>{data.summary?.junctions ?? 0} junctions</span>
        <span>{data.summary?.traffic_lights ?? 0} signals</span>
      </div>
      <svg viewBox={`0 0 ${viewWidth} ${viewHeight}`} role="img" aria-label="SUMO network geometry">
        {data.edges.map((edge) => {
          const points = edge.shape.map(project).map((point) => `${point.x},${point.y}`).join(' ');
          return <polyline key={edge.id} points={points} fill="none" strokeWidth={Math.max(2, edge.lane_count + 1)} />;
        })}
        {data.junctions.map((junction) => {
          const point = project(junction);
          const isSignal = junction.type === 'traffic_light';
          return <circle key={junction.id} cx={point.x} cy={point.y} r={isSignal ? 6 : 3} className={isSignal ? 'signal-node' : 'junction-node'} />;
        })}
      </svg>
    </div>
  );
}

function ThreeTrafficWorld({ geometry, run }) {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);
  const animationRef = useRef(null);
  const vehicleGroupRef = useRef(null);
  const cameraRef = useRef(null);
  const telemetryRef = useRef([]);
  const [worldError, setWorldError] = useState(null);
  const telemetry = run?.time_series || [];
  const data = geometry.state === 'done' ? geometry.data : null;
  const paths = useMemo(() => {
    if(!data?.edges?.length) {
      return [];
    }
    return data.edges
      .map((edge) => (edge.shape || [])
        .filter((point) => Number.isFinite(point?.x) && Number.isFinite(point?.y))
        .map((point) => ({ x: point.x, y: point.y })))
      .filter((shape) => shape.length >= 2);
  }, [data]);
  const sceneKey = data?.scenario_id || data?.scenario || JSON.stringify(data?.summary || {});

  useEffect(() => {
    telemetryRef.current = telemetry;
  }, [telemetry]);

  useEffect(() => {
    const mount = mountRef.current;
    if(!mount || !data) {
      return undefined;
    }
    setWorldError(null);

    const width = Math.max(320, mount.clientWidth);
    const height = Math.max(360, mount.clientHeight);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x071016);
    scene.fog = new THREE.Fog(0x071016, 90, 360);
    const camera = new THREE.PerspectiveCamera(48, width / height, 0.1, 1200);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8));
    renderer.setSize(width, height);
    renderer.shadowMap.enabled = true;
    mount.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enableZoom = true;
    controls.enablePan = true;
    controls.minDistance = 18;
    controls.maxDistance = 340;
    controls.maxPolarAngle = Math.PI * 0.48;

    const bounds = data.bounds || { min_x: 0, min_y: 0, max_x: 1, max_y: 1 };
    const spanX = Math.max(1, bounds.max_x - bounds.min_x);
    const spanY = Math.max(1, bounds.max_y - bounds.min_y);
    const worldScale = 180 / Math.max(spanX, spanY);
    const centerX = (bounds.min_x + bounds.max_x) / 2;
    const centerY = (bounds.min_y + bounds.max_y) / 2;
    const project = (point) => {
      if(!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)) {
        return new THREE.Vector3(0, 0, 0);
      }
      return new THREE.Vector3(
        (point.x - centerX) * worldScale,
        0,
        -(point.y - centerY) * worldScale
      );
    };

    scene.add(new THREE.HemisphereLight(0xa9dcff, 0x102018, 2.6));
    const sun = new THREE.DirectionalLight(0xffffff, 2.2);
    sun.position.set(-80, 120, 60);
    sun.castShadow = true;
    scene.add(sun);

    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(360, 360),
      new THREE.MeshStandardMaterial({ color: 0x0b1620, roughness: 0.92, metalness: 0.05 })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);

    const roadMaterial = new THREE.MeshStandardMaterial({ color: 0x2a2d38, roughness: 0.72 });
    const laneMaterial = new THREE.MeshBasicMaterial({ color: 0xfff4b8, transparent: true, opacity: 0.45 });
    const maxRoadEdges = 900;
    const edgeStep = Math.max(1, Math.ceil(data.edges.length / maxRoadEdges));
    data.edges.filter((_, index) => index % edgeStep === 0).forEach((edge) => {
      const shape = (edge.shape || []).filter((point) => Number.isFinite(point?.x) && Number.isFinite(point?.y));
      for(let index = 0; index < shape.length - 1; index += 1) {
        const start = project(shape[index]);
        const end = project(shape[index + 1]);
        const mid = start.clone().lerp(end, 0.5);
        const length = start.distanceTo(end);
        if(length < 0.3) {
          continue;
        }
        const road = new THREE.Mesh(
          new THREE.BoxGeometry(Math.max(length, 0.4), 0.08, Math.max(1.4, (edge.lane_count || 1) * 0.9)),
          roadMaterial
        );
        road.position.set(mid.x, 0.04, mid.z);
        road.rotation.y = -Math.atan2(end.z - start.z, end.x - start.x);
        road.receiveShadow = true;
        scene.add(road);

        if(length > 3) {
          const lane = new THREE.Mesh(new THREE.BoxGeometry(length * 0.82, 0.02, 0.05), laneMaterial);
          lane.position.set(mid.x, 0.11, mid.z);
          lane.rotation.y = road.rotation.y;
          scene.add(lane);
        }
      }
    });

    const signalMaterial = new THREE.MeshStandardMaterial({ color: 0x20e682, emissive: 0x0a6d3e, emissiveIntensity: 1.3 });
    const junctionMaterial = new THREE.MeshStandardMaterial({ color: 0x44b2ff, emissive: 0x082a44, emissiveIntensity: 0.7 });
    const buildingMaterial = new THREE.MeshStandardMaterial({ color: 0x172231, roughness: 0.8, metalness: 0.15 });
    const maxJunctions = 360;
    const junctionStep = Math.max(1, Math.ceil(data.junctions.length / maxJunctions));
    data.junctions.filter((junction, index) => junction.type === 'traffic_light' || index % junctionStep === 0).forEach((junction, index) => {
      if(!Number.isFinite(junction?.x) || !Number.isFinite(junction?.y)) {
        return;
      }
      const pos = project(junction);
      const node = new THREE.Mesh(
        new THREE.CylinderGeometry(junction.type === 'traffic_light' ? 0.75 : 0.35, junction.type === 'traffic_light' ? 0.75 : 0.35, 0.45, 16),
        junction.type === 'traffic_light' ? signalMaterial : junctionMaterial
      );
      node.position.set(pos.x, 0.35, pos.z);
      scene.add(node);

      if(index % 7 === 0 && index < 220) {
        const height = 3 + ((index * 7) % 11);
        const building = new THREE.Mesh(new THREE.BoxGeometry(2.2, height, 2.2), buildingMaterial);
        building.position.set(pos.x + 4 + ((index % 3) * 1.5), height / 2, pos.z - 4);
        building.castShadow = true;
        building.receiveShadow = true;
        scene.add(building);
      }
    });

    const vehicleGroup = new THREE.Group();
    const vehicleMaterial = new THREE.MeshStandardMaterial({ color: 0xfbbf24, emissive: 0x4d3000, emissiveIntensity: 0.65 });
    const vehicles = Array.from({ length: 240 }, (_, index) => {
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(0.72, 0.38, 1.18), vehicleMaterial);
      mesh.castShadow = true;
      mesh.visible = false;
      mesh.userData.pathIndex = index % Math.max(1, paths.length);
      mesh.userData.offset = index / 240;
      vehicleGroup.add(mesh);
      return mesh;
    });
    scene.add(vehicleGroup);

    const radius = Math.max(95, Math.min(190, Math.max(spanX, spanY) * worldScale * 0.8));
    camera.position.set(0, radius * 0.68, radius);
    camera.lookAt(0, 0, 0);
    controls.target.set(0, 0, 0);
    controls.update();
    gsap.fromTo(camera.position, { y: radius * 0.95, z: radius * 1.25 }, {
      y: radius * 0.68,
      z: radius,
      duration: 1.2,
      ease: 'power3.out',
      onUpdate: () => {
        controls.target.set(0, 0, 0);
        controls.update();
      }
    });

    sceneRef.current = scene;
    cameraRef.current = camera;
    vehicleGroupRef.current = vehicleGroup;
    let started = performance.now();

    function placeVehicle(mesh, path, progress) {
      if(!path || path.length < 2) {
        mesh.visible = false;
        return;
      }
      const segmentFloat = progress * (path.length - 1);
      const segmentIndex = Math.min(path.length - 2, Math.floor(segmentFloat));
      const local = segmentFloat - segmentIndex;
      if(!path[segmentIndex] || !path[segmentIndex + 1]) {
        mesh.visible = false;
        return;
      }
      const start = project(path[segmentIndex]);
      const end = project(path[segmentIndex + 1]);
      const pos = start.lerp(end, local);
      mesh.position.set(pos.x, 0.42, pos.z);
      mesh.rotation.y = -Math.atan2(end.z - start.z, end.x - start.x) + Math.PI / 2;
      mesh.visible = true;
    }

    function animate(now) {
      const elapsed = (now - started) / 1000;
      const liveTelemetry = telemetryRef.current;
      const frame = liveTelemetry.length ? liveTelemetry[Math.floor((elapsed * 2) % liveTelemetry.length)] : null;
      const count = Math.min(vehicles.length, Math.max(48, frame?.vehicles || Math.min(180, paths.length * 3)));
      vehicles.forEach((mesh, index) => {
        if(index >= count || !paths.length) {
          mesh.visible = false;
          return;
        }
        const path = paths[(mesh.userData.pathIndex + Math.floor(elapsed * 0.35)) % paths.length];
        placeVehicle(mesh, path, (elapsed * 0.08 + mesh.userData.offset) % 1);
      });
      if(!controls.enabled) {
        camera.position.x = Math.sin(elapsed * 0.08) * radius * 0.16;
        camera.position.z = radius + Math.cos(elapsed * 0.08) * radius * 0.12;
      }
      controls.update();
      try {
        renderer.render(scene, camera);
        animationRef.current = requestAnimationFrame(animate);
      } catch (error) {
        setWorldError(error.message || '3D renderer failed.');
      }
    }
    animationRef.current = requestAnimationFrame(animate);
    renderer.domElement.addEventListener('webglcontextlost', (event) => {
      event.preventDefault();
      setWorldError('WebGL context was lost. Reload or select a smaller map extract.');
    });

    function resize() {
      const nextWidth = Math.max(320, mount.clientWidth);
      const nextHeight = Math.max(360, mount.clientHeight);
      camera.aspect = nextWidth / nextHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(nextWidth, nextHeight);
    }
    window.addEventListener('resize', resize);

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationRef.current);
      gsap.killTweensOf(camera.position);
      controls.dispose();
      scene.traverse((object) => {
        if(object.geometry) {
          object.geometry.dispose();
        }
        if(object.material) {
          if(Array.isArray(object.material)) {
            object.material.forEach((material) => material.dispose());
          } else {
            object.material.dispose();
          }
        }
      });
      renderer.dispose();
      mount.replaceChildren();
    };
  }, [sceneKey, paths]);

  if(geometry.state === 'idle' || geometry.state === 'loading') {
    return <div className="world-panel empty">Loading 3D world...</div>;
  }
  if(geometry.state === 'error') {
    return <div className="world-panel empty">3D world unavailable: {geometry.error}</div>;
  }
  if(worldError) {
    return <div className="world-panel empty">3D world paused: {worldError}</div>;
  }

  const summary = data?.summary || {};
  const latest = telemetry[telemetry.length - 1];
  return (
    <div className="world-panel">
      <div className="world-toolbar">
        <div>
          <h3>3D Traffic World</h3>
          <small>{summary.edges || 0} roads · {summary.junctions || 0} junctions · {summary.traffic_lights || 0} signals · drag to rotate · wheel/pinch to zoom</small>
        </div>
        <div className="world-metrics">
          <MetricPulse value={latest?.vehicles ?? 0} label="vehicles" />
          <MetricPulse value={latest?.queue ?? 0} label="queued" />
          <MetricPulse value={latest?.total_waiting_time ?? 0} label="s wait" />
        </div>
      </div>
      <div className="three-mount" ref={mountRef} />
    </div>
  );
}

function MetricPulse({ value, label }) {
  const ref = useRef(null);
  useEffect(() => {
    if(!ref.current) {
      return undefined;
    }
    let animation;
    try {
      animation = animeAnimate(ref.current, {
        scale: [1, 1.08, 1],
        duration: 420,
        ease: 'outQuad'
      });
    } catch {
      animation = null;
    }
    return () => animation?.cancel?.();
  }, [value]);
  return <span ref={ref}>{value} {label}</span>;
}

function SimulationReplay({ run, geometry }) {
  const [frameIndex, setFrameIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const frames = run?.time_series || [];

  useEffect(() => {
    setFrameIndex(0);
    setPlaying(false);
  }, [run?.run_id]);

  useEffect(() => {
    if(!playing || frames.length < 2) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      setFrameIndex((current) => current >= frames.length - 1 ? 0 : current + 1);
    }, 500);
    return () => window.clearInterval(timer);
  }, [playing, frames.length]);

  if(!run || !frames.length) {
    return (
      <div className="simulation-replay empty">
        Run a TraCI baseline, OSM fixed-time, or OSM MaxPressure controller to replay telemetry here.
      </div>
    );
  }

  const data = geometry.data;
  const bounds = data?.bounds || { min_x: 0, min_y: 0, max_x: 1, max_y: 1 };
  const width = Math.max(1, bounds.max_x - bounds.min_x);
  const height = Math.max(1, bounds.max_y - bounds.min_y);
  const pad = 24;
  const viewWidth = 720;
  const viewHeight = 300;
  const scale = Math.min((viewWidth - pad * 2) / width, (viewHeight - pad * 2) / height);
  const project = (point) => ({
    x: pad + (point.x - bounds.min_x) * scale,
    y: viewHeight - pad - (point.y - bounds.min_y) * scale
  });
  const frame = frames[Math.min(frameIndex, frames.length - 1)];
  const edges = data?.edges || [];
  const vehicleCount = Math.min(40, Math.max(0, Number(frame.vehicles || 0)));
  const vehicleDots = Array.from({ length: vehicleCount }, (_, index) => {
    const edge = edges[index % Math.max(1, edges.length)];
    const shape = edge?.shape || [];
    if(shape.length < 2) {
      return null;
    }
    const a = project(shape[0]);
    const b = project(shape[shape.length - 1]);
    const progress = ((frameIndex * 0.11) + (index / Math.max(1, vehicleCount))) % 1;
    return {
      id: `${edge.id}-${index}`,
      x: a.x + (b.x - a.x) * progress,
      y: a.y + (b.y - a.y) * progress
    };
  }).filter(Boolean);

  return (
    <div className="simulation-replay">
      <div className="replay-header">
        <div>
          <h3>Interactive Telemetry Replay</h3>
          <small>{run.controller?.display_name || run.controller?.name || 'Simulation'} · {run.scenario_id || run.scenario}</small>
        </div>
        <button className="icon-button" onClick={() => setPlaying((value) => !value)} title={playing ? 'Pause replay' : 'Play replay'}>
          {playing ? <Pause size={18} /> : <Play size={18} />}
        </button>
      </div>
      <svg viewBox={`0 0 ${viewWidth} ${viewHeight}`} role="img" aria-label="Traffic telemetry replay">
        {edges.map((edge) => {
          const points = edge.shape.map(project).map((point) => `${point.x},${point.y}`).join(' ');
          return <polyline key={edge.id} points={points} fill="none" strokeWidth={Math.max(2, edge.lane_count + 1)} />;
        })}
        {vehicleDots.map((dot) => <circle key={dot.id} cx={dot.x} cy={dot.y} r="4" className="vehicle-dot" />)}
      </svg>
      <input
        className="replay-slider"
        type="range"
        min="0"
        max={frames.length - 1}
        value={frameIndex}
        onChange={(event) => setFrameIndex(Number(event.target.value))}
      />
      <div className="replay-metrics">
        <span>t={frame.time}s</span>
        <span>vehicles {frame.vehicles}</span>
        <span>queue {frame.queue}</span>
        <span>waiting {frame.total_waiting_time}s</span>
      </div>
    </div>
  );
}

function ComparisonTable({ comparison }) {
  if(comparison.state === 'loading') {
    return <pre className="result-box">Loading comparison...</pre>;
  }
  if(comparison.state === 'error') {
    return <pre className="result-box error">{comparison.error}</pre>;
  }
  const controllers = comparison.data?.controllers || {};
  const rows = Object.entries(controllers);
  if(!rows.length) {
    return <pre className="result-box">No comparable saved runs for this scenario yet.</pre>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Controller</th>
            <th>Runs</th>
            <th>Avg Delay</th>
            <th>Avg Time Loss</th>
            <th>Avg Queue</th>
            <th>Throughput</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([controller, summary]) => (
            <tr key={controller}>
              <td>{controller}</td>
              <td>{summary.ok_runs}/{summary.runs}</td>
              <td>{formatMean(summary.metrics?.average_waiting_time_s)}</td>
              <td>{formatMean(summary.metrics?.average_time_loss_s)}</td>
              <td>{formatMean(summary.metrics?.average_queue)}</td>
              <td>{formatMean(summary.metrics?.vehicles_arrived)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ExportsTable({ exportsList, onSelect }) {
  if(!exportsList.length) {
    return <pre className="result-box">No exported experiment bundles yet.</pre>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Experiment</th>
            <th>Type</th>
            <th>Scenario</th>
            <th>Runs</th>
            <th>Seeds</th>
            <th>Open</th>
          </tr>
        </thead>
        <tbody>
          {exportsList.slice(0, 12).map((row) => (
            <tr key={row.experiment_id}>
              <td>{row.experiment_id}</td>
              <td>{row.experiment_type}</td>
              <td>{row.scenario_id}</td>
              <td>{row.runs}</td>
              <td>{Array.isArray(row.seeds) ? row.seeds.join(', ') : '-'}</td>
              <td>
                <button className="table-button" onClick={() => onSelect(row.experiment_id)}>View</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ExportDetail({ result }) {
  if(result.state === 'idle') {
    return null;
  }
  if(result.state === 'loading') {
    return <pre className="result-box">Loading export...</pre>;
  }
  if(result.state === 'error') {
    return <pre className="result-box error">{result.error}</pre>;
  }
  const aggregate = result.data?.aggregate || {};
  const rows = Object.entries(aggregate);
  if(!rows.length) {
    return <pre className="result-box">Export has no aggregate metrics.</pre>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Controller</th>
            <th>Runs</th>
            <th>Avg Delay</th>
            <th>Avg Time Loss</th>
            <th>Avg Queue</th>
            <th>Throughput</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([controller, summary]) => (
            <tr key={controller}>
              <td>{controller}</td>
              <td>{summary.ok_runs}/{summary.runs}</td>
              <td>{formatMean(summary.metrics?.average_waiting_time_s)}</td>
              <td>{formatMean(summary.metrics?.average_time_loss_s)}</td>
              <td>{formatMean(summary.metrics?.average_queue)}</td>
              <td>{formatMean(summary.metrics?.vehicles_arrived)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatMean(metric) {
  if(!metric || metric.mean === undefined) {
    return '-';
  }
  return metric.stdev ? `${metric.mean} ± ${metric.stdev}` : String(metric.mean);
}

function ResultsTable({ results }) {
  if(!results.length) {
    return <pre className="result-box">No saved results yet.</pre>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Run</th>
            <th>Controller</th>
            <th>Arrived</th>
            <th>Avg Delay</th>
            <th>Avg Time Loss</th>
            <th>Phase Changes</th>
          </tr>
        </thead>
        <tbody>
          {results.map((row) => (
            <tr key={row.run_id}>
              <td>{row.run_id}</td>
              <td>{row.controller}</td>
              <td>{row.metrics?.vehicles_arrived ?? '-'}</td>
              <td>{row.metrics?.average_waiting_time_s ?? '-'}s</td>
              <td>{row.metrics?.average_time_loss_s ?? '-'}s</td>
              <td>{row.phase_changes ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
