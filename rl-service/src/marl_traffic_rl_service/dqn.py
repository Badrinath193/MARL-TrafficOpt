from __future__ import annotations

import random
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .experiments import persist_experiment_bundle, persist_result
from .scenarios import get_scenario, scenario_to_dict
from .sumo import (
    SCENARIO_ROOT,
    _aggregate_time_series,
    _candidate_green_phases,
    _packaged_cross_network,
    _phase_incoming_queue,
    _phase_pressure,
    _snapshot,
    _yellow_after,
    _write_routes,
    detect_sumo_tools,
    parse_tripinfo,
)


@dataclass
class Transition:
    state: list[float]
    action: int
    reward: float
    next_state: list[float]
    done: bool


class LinearDqnAgent:
    def __init__(
        self,
        state_size: int,
        action_size: int,
        rng: random.Random,
        learning_rate: float = 0.04,
        gamma: float = 0.92,
        replay_limit: int = 700,
    ) -> None:
        self.state_size = state_size
        self.action_size = action_size
        self.rng = rng
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.replay_limit = replay_limit
        self.weights = [[rng.uniform(-0.02, 0.02) for _ in range(state_size + 1)] for _ in range(action_size)]
        self.replay: list[Transition] = []

    def q_values(self, state: list[float]) -> list[float]:
        features = [1.0, *state]
        return [sum(weight * feature for weight, feature in zip(action_weights, features)) for action_weights in self.weights]

    def act(self, state: list[float], epsilon: float) -> int:
        if self.rng.random() < epsilon:
            return self.rng.randrange(self.action_size)
        values = self.q_values(state)
        return max(range(self.action_size), key=lambda index: values[index])

    def remember(self, transition: Transition) -> None:
        self.replay.append(transition)
        if len(self.replay) > self.replay_limit:
            self.replay.pop(0)

    def train_batch(self, batch_size: int = 24) -> float:
        if not self.replay:
            return 0.0
        batch = self.rng.sample(self.replay, min(batch_size, len(self.replay)))
        losses = []
        for transition in batch:
            prediction = self.q_values(transition.state)[transition.action]
            future = 0.0 if transition.done else max(self.q_values(transition.next_state))
            target = transition.reward + self.gamma * future
            error = target - prediction
            features = [1.0, *transition.state]
            for index, feature in enumerate(features):
                self.weights[transition.action][index] += self.learning_rate * error * feature
            losses.append(error * error)
        return round(sum(losses) / len(losses), 5)

    def export(self) -> dict:
        return {
            "type": "linear_dqn",
            "state_size": self.state_size,
            "action_size": self.action_size,
            "learning_rate": self.learning_rate,
            "gamma": self.gamma,
            "weights": [[round(value, 6) for value in row] for row in self.weights],
        }


def train_single_intersection_dqn(
    episodes: int = 4,
    seed: int = 1,
    demand_profile: str | None = None,
    scenario_id: str | None = None,
    timeout_seconds: int = 60,
) -> dict:
    if episodes < 1:
        return {"ok": False, "error": "episodes must be at least 1"}
    if episodes > 20:
        return {"ok": False, "error": "episodes is capped at 20 for local runs"}

    try:
        scenario = get_scenario(scenario_id)
    except ValueError as error:
        return {"ok": False, "error": str(error)}
    if scenario.network != "packaged-cross-net":
        return {
            "ok": False,
            "skipped": True,
            "reason": f"Scenario '{scenario.scenario_id}' is cataloged but not executable by the DQN runner yet.",
            "scenario": scenario.scenario_id,
            "scenario_id": scenario.scenario_id,
            "scenario_spec": scenario_to_dict(scenario),
        }
    demand_profile = demand_profile or scenario.demand_profile

    tools = detect_sumo_tools()
    if not tools["ready"]:
        return {
            "ok": False,
            "skipped": True,
            "reason": "SUMO is not available.",
            "tools": tools,
        }

    try:
        import traci  # type: ignore
    except Exception as error:
        return {
            "ok": False,
            "skipped": True,
            "reason": f"TraCI Python package is unavailable: {error}",
            "tools": tools,
        }

    if _packaged_cross_network() is None:
        return {
            "ok": False,
            "skipped": True,
            "reason": "Packaged SUMO cross.net.xml not found.",
            "tools": tools,
        }

    rng = random.Random(seed)
    agent: LinearDqnAgent | None = None
    episode_runs = []
    started = time.perf_counter()

    for episode in range(1, episodes + 1):
        epsilon = max(0.08, 0.55 * (0.72 ** (episode - 1)))
        episode_seed = seed + episode - 1
        run = _run_dqn_episode(
            traci=traci,
            tools=tools,
            agent=agent,
            rng=rng,
            episode=episode,
            episode_seed=episode_seed,
            demand_profile=demand_profile,
            scenario_id=scenario.scenario_id,
            epsilon=epsilon,
            timeout_seconds=timeout_seconds,
            training=True,
        )
        if not run.get("ok"):
            return run
        agent = run.pop("_agent")
        episode_runs.append(persist_result(run))

    evaluation = _run_dqn_episode(
        traci=traci,
        tools=tools,
        agent=agent,
        rng=rng,
        episode=episodes + 1,
        episode_seed=seed + episodes,
        demand_profile=demand_profile,
        scenario_id=scenario.scenario_id,
        epsilon=0.0,
        timeout_seconds=timeout_seconds,
        training=False,
    )
    if not evaluation.get("ok"):
        return evaluation
    evaluation.pop("_agent", None)
    evaluation = persist_result(evaluation)

    bundle = {
        "ok": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario.scenario_id,
        "scenario_id": scenario.scenario_id,
        "scenario_spec": scenario_to_dict(scenario),
        "algorithm": "linear_dqn",
        "seed": seed,
        "demand_profile": demand_profile,
        "episodes": episodes,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "runs": [*episode_runs, evaluation],
        "training_runs": episode_runs,
        "evaluation": evaluation,
        "model": agent.export() if agent is not None else None,
        "limitations": [
            "Phase 6 uses a lightweight linear DQN-style approximator to avoid heavyweight ML dependencies.",
            "Training is scoped to SUMO's packaged cross-intersection scenario.",
            "Use the greedy evaluation result for baseline comparison, not the exploratory training episodes.",
        ],
    }
    return persist_experiment_bundle(bundle)


def _run_dqn_episode(
    traci,
    tools: dict,
    agent: LinearDqnAgent | None,
    rng: random.Random,
    episode: int,
    episode_seed: int,
    demand_profile: str,
    scenario_id: str,
    epsilon: float,
    timeout_seconds: int,
    training: bool,
) -> dict:
    with tempfile.TemporaryDirectory(prefix="marl_traffic_dqn_") as tmp:
        run_dir = Path(tmp)
        for file in SCENARIO_ROOT.iterdir():
            if file.is_file() and file.suffix in {".xml", ".sumocfg"}:
                shutil.copy2(file, run_dir / file.name)
        _write_routes(run_dir / "one_intersection.rou.xml", demand_profile=demand_profile, seed=episode_seed)

        network = _packaged_cross_network()
        if network is None:
            return {"ok": False, "skipped": True, "reason": "Packaged SUMO cross.net.xml not found."}
        shutil.copy2(network, run_dir / "one_intersection.net.xml")

        tripinfo = run_dir / "tripinfo.xml"
        cmd = [
            tools["sumo"]["path"],
            "-c",
            str(run_dir / "one_intersection.sumocfg"),
            "--no-step-log",
            "true",
            "--duration-log.disable",
            "true",
            "--tripinfo-output",
            str(tripinfo),
            "--seed",
            str(episode_seed),
        ]

        label = f"marl_dqn_{episode}_{time.time_ns()}"
        time_series: list[dict] = []
        phase_changes = 0
        training_steps = 0
        total_reward = 0.0
        last_loss = 0.0
        last_action = None
        last_state = None
        last_phase = None
        pending_phase = None
        pending_at = None
        current_green_start = 0.0
        conn = None
        started = time.perf_counter()

        try:
            traci.start(cmd, label=label, stdout=subprocess.DEVNULL)
            conn = traci.getConnection(label)
            tls_ids = conn.trafficlight.getIDList()
            tls_id = tls_ids[0] if tls_ids else None
            if tls_id is None:
                raise RuntimeError("Scenario has no traffic light.")

            controlled_links = conn.trafficlight.getControlledLinks(tls_id)
            program = conn.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)[0]
            candidate_phases = _candidate_green_phases(program)
            if not candidate_phases:
                raise RuntimeError("No green phases found in traffic-light program.")
            if agent is None:
                state_size = len(_state_vector(conn, program, controlled_links, candidate_phases, None))
                agent = LinearDqnAgent(state_size=state_size, action_size=len(candidate_phases), rng=rng)

            while conn.simulation.getMinExpectedNumber() > 0:
                sim_time = conn.simulation.getTime()
                if sim_time > 300:
                    break

                if pending_phase is not None and pending_at is not None and sim_time >= pending_at:
                    conn.trafficlight.setPhase(tls_id, pending_phase)
                    last_phase = pending_phase
                    current_green_start = sim_time
                    phase_changes += 1
                    pending_phase = None
                    pending_at = None

                state = _state_vector(conn, program, controlled_links, candidate_phases, last_phase)
                if last_state is not None and last_action is not None and training:
                    reward = _reward(conn, switched=False)
                    total_reward += reward
                    agent.remember(Transition(last_state, last_action, reward, state, False))
                    last_loss = agent.train_batch()
                    training_steps += 1

                elapsed = sim_time - current_green_start
                if pending_phase is None and (last_phase is None or elapsed >= 10):
                    action = agent.act(state, epsilon)
                    selected_phase = candidate_phases[action]
                    if selected_phase != last_phase:
                        yellow_phase = _yellow_after(last_phase)
                        if yellow_phase is not None:
                            conn.trafficlight.setPhase(tls_id, yellow_phase)
                            last_phase = yellow_phase
                            pending_phase = selected_phase
                            pending_at = sim_time + 3
                        else:
                            conn.trafficlight.setPhase(tls_id, selected_phase)
                            last_phase = selected_phase
                            current_green_start = sim_time
                        phase_changes += 1
                    last_state = state
                    last_action = action

                conn.simulationStep()
                if int(sim_time) % 10 == 0:
                    time_series.append(_snapshot(conn, tls_id, sim_time))

            if last_state is not None and last_action is not None and training:
                final_state = _state_vector(conn, program, controlled_links, candidate_phases, last_phase)
                reward = _reward(conn, switched=False)
                total_reward += reward
                agent.remember(Transition(last_state, last_action, reward, final_state, True))
                last_loss = agent.train_batch()

            duration_ms = round((time.perf_counter() - started) * 1000, 2)
        except Exception as error:
            return {
                "ok": False,
                "skipped": False,
                "stage": "dqn_traci",
                "error": str(error),
                "episode": episode,
                "seed": episode_seed,
            }
        finally:
            try:
                if conn is not None:
                    conn.close()
            except Exception:
                pass

        metrics = parse_tripinfo(tripinfo)
        metrics.update(_aggregate_time_series(time_series))
        metrics["total_reward"] = round(total_reward, 3)
        metrics["last_training_loss"] = last_loss
        return {
            "ok": True,
            "skipped": False,
            "scenario": scenario_id,
            "scenario_id": scenario_id,
            "network_source": "packaged-cross-net",
            "execution": "traci_controlled_dqn_training" if training else "traci_controlled_dqn_greedy_eval",
            "controller": {
                "name": "dqn",
                "display_name": "Linear DQN",
                "description": "Lightweight DQN-style traffic-signal learner with replay and epsilon-greedy exploration.",
                "execution_mode": "traci_controlled_learning",
                "parameters": {
                    "episode": episode,
                    "epsilon": epsilon,
                    "min_green_s": 10,
                    "control_interval_s": 1,
                },
            },
            "algorithm": "linear_dqn",
            "episode": episode,
            "training": training,
            "seed": episode_seed,
            "demand_profile": demand_profile,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "phase_changes": phase_changes,
            "training_steps": training_steps,
            "metrics": metrics,
            "time_series": time_series[-40:],
            "_agent": agent,
        }


def _state_vector(conn, program, controlled_links, candidate_phases: list[int], current_phase: int | None) -> list[float]:
    state = []
    for phase in candidate_phases:
        phase_state = program.phases[phase].state
        state.append(min(_phase_incoming_queue(conn, phase_state, controlled_links) / 20.0, 1.5))
    for phase in candidate_phases:
        phase_state = program.phases[phase].state
        state.append(max(min(_phase_pressure(conn, phase_state, controlled_links) / 20.0, 1.5), -1.5))
    for phase in candidate_phases:
        state.append(1.0 if phase == current_phase else 0.0)
    return state


def _reward(conn, switched: bool) -> float:
    lane_queue = sum(conn.lane.getLastStepHaltingNumber(lane_id) for lane_id in conn.lane.getIDList())
    waiting = sum(conn.vehicle.getWaitingTime(vehicle_id) for vehicle_id in conn.vehicle.getIDList())
    switch_penalty = 0.25 if switched else 0.0
    return round(-(lane_queue + 0.02 * waiting + switch_penalty), 4)
