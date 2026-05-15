from __future__ import annotations

import random
import subprocess
import time
from datetime import datetime, timezone

from .dqn import LinearDqnAgent, Transition
from .experiments import persist_experiment_bundle, persist_result
from .osm_runner import (
    _aggregate_generic_time_series,
    _candidate_green_phases,
    _generate_routes,
    _phase_pressure,
    _prepare_imported_scenario,
    _route_stats,
    _snapshot_generic,
    _write_config,
    inspect_imported_osm_scenario,
)
from .scenarios import scenario_to_dict
from .sumo import parse_tripinfo


def train_imported_osm_dqn(
    scenario_id: str,
    episodes: int = 3,
    seed: int = 1,
    end_time: int = 180,
    period: int = 10,
    min_green: int = 10,
) -> dict:
    if episodes < 1:
        return {"ok": False, "error": "episodes must be at least 1"}
    if episodes > 12:
        return {"ok": False, "error": "episodes is capped at 12 for imported OSM local runs"}

    prepared = _prepare_imported_scenario(scenario_id, persist=False)
    if not prepared["ok"]:
        return prepared

    scenario = prepared["scenario"]
    rng = random.Random(seed)
    agents: dict[str, LinearDqnAgent] = {}
    training_runs = []
    started = time.perf_counter()

    try:
        import traci  # type: ignore
    except Exception as error:
        return {
            "ok": False,
            "skipped": True,
            "reason": f"TraCI Python package is unavailable: {error}",
            "scenario": scenario.scenario_id,
            "scenario_id": scenario.scenario_id,
            "scenario_spec": scenario_to_dict(scenario),
            "tools": prepared["tools"],
        }

    for episode in range(1, episodes + 1):
        epsilon = max(0.08, 0.55 * (0.72 ** (episode - 1)))
        run = _run_imported_dqn_episode(
            traci=traci,
            prepared=prepared,
            agents=agents,
            rng=rng,
            episode=episode,
            episode_seed=seed + episode - 1,
            epsilon=epsilon,
            end_time=end_time,
            period=period,
            min_green=min_green,
            training=True,
        )
        if not run.get("ok"):
            return run
        training_runs.append(persist_result(run))

    evaluation = _run_imported_dqn_episode(
        traci=traci,
        prepared=prepared,
        agents=agents,
        rng=rng,
        episode=episodes + 1,
        episode_seed=seed + episodes,
        epsilon=0.0,
        end_time=end_time,
        period=period,
        min_green=min_green,
        training=False,
    )
    if not evaluation.get("ok"):
        return evaluation
    evaluation = persist_result(evaluation)

    bundle = {
        "ok": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario.scenario_id,
        "scenario_id": scenario.scenario_id,
        "scenario_spec": scenario_to_dict(scenario),
        "algorithm": "imported_osm_linear_dqn",
        "experiment_type": "imported_osm_dqn_training",
        "seed": seed,
        "episodes": episodes,
        "end_time": end_time,
        "period": period,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "runs": [*training_runs, evaluation],
        "training_runs": training_runs,
        "evaluation": evaluation,
        "models": {tls_id: agent.export() for tls_id, agent in agents.items()},
        "limitations": [
            "Phase 14 uses independent lightweight linear DQN agents per imported-network traffic light.",
            "Demand is generated with randomTrips.py and is not calibrated.",
            "Use greedy evaluation for engineering comparison only.",
        ],
    }
    return persist_experiment_bundle(bundle)


def _run_imported_dqn_episode(
    traci,
    prepared: dict,
    agents: dict[str, LinearDqnAgent],
    rng: random.Random,
    episode: int,
    episode_seed: int,
    epsilon: float,
    end_time: int,
    period: int,
    min_green: int,
    training: bool,
) -> dict:
    scenario = prepared["scenario"]
    scenario_dir = prepared["scenario_dir"]
    tools = prepared["tools"]
    routes_path = scenario_dir / "generated.rou.xml"
    tripinfo_path = scenario_dir / "traci_imported_dqn_tripinfo.xml"
    config_path = scenario_dir / "osm_traci_imported_dqn.sumocfg"

    route_result = _generate_routes(
        net_path=prepared["net_path"],
        routes_path=routes_path,
        seed=episode_seed,
        end_time=end_time,
        period=period,
    )
    if route_result["returncode"] != 0:
        return {
            "ok": False,
            "skipped": False,
            "stage": "route_generation",
            "reason": "randomTrips.py failed to generate valid routes.",
            "scenario": scenario.scenario_id,
            "scenario_id": scenario.scenario_id,
            "returncode": route_result["returncode"],
            "stdout": route_result["stdout"],
            "stderr": route_result["stderr"],
        }

    _write_config(config_path, prepared["net_path"], routes_path, end_time)

    cmd = [
        tools["sumo"]["path"],
        "-c",
        str(config_path),
        "--no-step-log",
        "true",
        "--duration-log.disable",
        "true",
        "--tripinfo-output",
        str(tripinfo_path),
        "--seed",
        str(episode_seed),
    ]
    label = f"marl_imported_dqn_{episode}_{time.time_ns()}"
    conn = None
    started = time.perf_counter()
    phase_changes = 0
    training_steps = 0
    total_reward = 0.0
    last_loss = 0.0
    time_series = []
    tls_context = {}
    tls_green_start = {}
    last_state = {}
    last_action = {}

    try:
        traci.start(cmd, label=label, stdout=subprocess.DEVNULL)
        conn = traci.getConnection(label)
        tls_ids = list(conn.trafficlight.getIDList())
        if not tls_ids:
            return {
                "ok": False,
                "skipped": True,
                "reason": "Imported OSM network has no controllable traffic lights.",
                "scenario": scenario.scenario_id,
                "scenario_id": scenario.scenario_id,
                "scenario_spec": scenario_to_dict(scenario),
                "network_inspection": inspect_imported_osm_scenario(scenario.scenario_id).get("network"),
                "tools": tools,
            }

        for tls_id in tls_ids:
            program = conn.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)[0]
            links = conn.trafficlight.getControlledLinks(tls_id)
            candidate_phases = _candidate_green_phases(program) or list(range(max(1, len(program.phases))))
            tls_context[tls_id] = {
                "program": program,
                "links": links,
                "candidate_phases": candidate_phases,
            }
            tls_green_start[tls_id] = 0.0
            state = _state_vector(conn, program, links, candidate_phases, conn.trafficlight.getPhase(tls_id))
            if tls_id not in agents:
                agents[tls_id] = LinearDqnAgent(
                    state_size=len(state),
                    action_size=len(candidate_phases),
                    rng=rng,
                    learning_rate=0.035,
                    gamma=0.92,
                )

        while conn.simulation.getMinExpectedNumber() > 0:
            sim_time = conn.simulation.getTime()
            if sim_time > end_time:
                break

            for tls_id in tls_ids:
                context = tls_context[tls_id]
                current_phase = conn.trafficlight.getPhase(tls_id)
                state = _state_vector(
                    conn,
                    context["program"],
                    context["links"],
                    context["candidate_phases"],
                    current_phase,
                )
                if tls_id in last_state and tls_id in last_action and training:
                    reward = _reward(conn)
                    total_reward += reward
                    agents[tls_id].remember(Transition(last_state[tls_id], last_action[tls_id], reward, state, False))
                    last_loss = agents[tls_id].train_batch()
                    training_steps += 1

                if sim_time - tls_green_start[tls_id] < min_green:
                    continue
                action = agents[tls_id].act(state, epsilon)
                target_phase = context["candidate_phases"][action]
                if target_phase != current_phase:
                    conn.trafficlight.setPhase(tls_id, target_phase)
                    tls_green_start[tls_id] = sim_time
                    phase_changes += 1
                last_state[tls_id] = state
                last_action[tls_id] = action

            conn.simulationStep()
            if int(conn.simulation.getTime()) % 10 == 0:
                time_series.append(_snapshot_generic(conn, conn.simulation.getTime(), tls_ids))

        if training:
            for tls_id in list(last_state):
                context = tls_context[tls_id]
                final_state = _state_vector(
                    conn,
                    context["program"],
                    context["links"],
                    context["candidate_phases"],
                    conn.trafficlight.getPhase(tls_id),
                )
                reward = _reward(conn)
                total_reward += reward
                agents[tls_id].remember(Transition(last_state[tls_id], last_action[tls_id], reward, final_state, True))
                last_loss = agents[tls_id].train_batch()

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
    except Exception as error:
        return {
            "ok": False,
            "skipped": False,
            "stage": "imported_dqn_traci",
            "error": str(error),
            "scenario": scenario.scenario_id,
            "scenario_id": scenario.scenario_id,
            "episode": episode,
            "seed": episode_seed,
        }
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass

    metrics = parse_tripinfo(tripinfo_path)
    metrics.update(_route_stats(routes_path))
    metrics.update(_aggregate_generic_time_series(time_series))
    metrics["total_reward"] = round(total_reward, 3)
    metrics["last_training_loss"] = last_loss

    return {
        "ok": True,
        "skipped": False,
        "scenario": scenario.scenario_id,
        "scenario_id": scenario.scenario_id,
        "scenario_spec": scenario_to_dict(scenario),
        "network_source": scenario.network,
        "execution": "imported_osm_dqn_training" if training else "imported_osm_dqn_greedy_eval",
        "controller": {
            "name": "osm_dqn",
            "display_name": "Imported OSM Linear DQN",
            "description": "Independent lightweight DQN agents for imported-network traffic lights.",
            "execution_mode": "traci_controlled_learning",
            "parameters": {
                "episode": episode,
                "epsilon": epsilon,
                "seed": episode_seed,
                "end_time": end_time,
                "period": period,
                "min_green": min_green,
                "traffic_lights": list(agents),
            },
        },
        "algorithm": "imported_osm_linear_dqn",
        "episode": episode,
        "training": training,
        "seed": episode_seed,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": duration_ms,
        "phase_changes": phase_changes,
        "training_steps": training_steps,
        "metrics": metrics,
        "time_series": time_series[-40:],
    }


def _state_vector(conn, program, controlled_links, candidate_phases: list[int], current_phase: int) -> list[float]:
    state = []
    for phase in candidate_phases:
        phase_state = program.phases[phase].state
        state.append(min(_phase_queue(conn, phase_state, controlled_links) / 20.0, 1.5))
    for phase in candidate_phases:
        phase_state = program.phases[phase].state
        state.append(max(min(_phase_pressure(conn, phase_state, controlled_links) / 20.0, 1.5), -1.5))
    for phase in candidate_phases:
        state.append(1.0 if phase == current_phase else 0.0)
    return state


def _phase_queue(conn, state: str, controlled_links) -> float:
    score = 0.0
    seen = set()
    for index, signal in enumerate(state):
        if signal not in {"G", "g"} or index >= len(controlled_links):
            continue
        for link in controlled_links[index]:
            incoming = link[0]
            if incoming and incoming not in seen:
                seen.add(incoming)
                score += conn.lane.getLastStepHaltingNumber(incoming)
    return score


def _reward(conn) -> float:
    lane_queue = sum(conn.lane.getLastStepHaltingNumber(lane_id) for lane_id in conn.lane.getIDList())
    waiting = sum(conn.vehicle.getWaitingTime(vehicle_id) for vehicle_id in conn.vehicle.getIDList())
    return round(-(lane_queue + 0.02 * waiting), 4)
