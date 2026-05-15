from __future__ import annotations

import shutil
import os
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .controllers import controller_to_dict, get_controller
from .experiments import persist_result
from .scenarios import get_scenario, scenario_to_dict


REPO_ROOT = Path(__file__).resolve().parents[3]
SCENARIO_ROOT = REPO_ROOT / "scenarios" / "synthetic" / "one_intersection"


@dataclass(frozen=True)
class ToolStatus:
    name: str
    path: str | None
    available: bool


def detect_sumo_tools() -> dict:
    tools = {name: _detect_tool(name) for name in ("sumo", "sumo-gui", "netconvert", "duarouter")}
    sumo_home = _sumo_home()
    return {
        "sumo": tools["sumo"].__dict__,
        "sumo_gui": tools["sumo-gui"].__dict__,
        "netconvert": tools["netconvert"].__dict__,
        "duarouter": tools["duarouter"].__dict__,
        "ready": tools["sumo"].available,
        "gui_ready": tools["sumo-gui"].available,
        "sumo_home": str(sumo_home) if sumo_home is not None else None,
    }


def run_one_intersection_smoke_test(timeout_seconds: int = 30) -> dict:
    return run_one_intersection_open_loop_baseline("fixed_time", timeout_seconds=timeout_seconds, persist=False)


def run_one_intersection_baseline(
    controller_name: str,
    timeout_seconds: int = 30,
    persist: bool = True,
    seed: int = 1,
    demand_profile: str | None = None,
    scenario_id: str | None = None,
) -> dict:
    return run_one_intersection_traci_baseline(
        controller_name,
        timeout_seconds=timeout_seconds,
        persist=persist,
        seed=seed,
        demand_profile=demand_profile,
        scenario_id=scenario_id,
    )


def run_one_intersection_open_loop_baseline(controller_name: str, timeout_seconds: int = 30, persist: bool = True) -> dict:
    try:
        controller = get_controller(controller_name)
    except ValueError as error:
        return {"ok": False, "skipped": False, "error": str(error)}

    tools = detect_sumo_tools()
    if not tools["ready"]:
        result = {
            "ok": False,
            "skipped": True,
            "reason": "SUMO tools are not available on PATH. Install SUMO and ensure sumo/netconvert are available.",
            "tools": tools,
            "scenario": str(SCENARIO_ROOT),
            "controller": controller_to_dict(controller),
        }
        return persist_result(result) if persist else result

    if not SCENARIO_ROOT.exists():
        result = {
            "ok": False,
            "skipped": False,
            "reason": f"Scenario directory not found: {SCENARIO_ROOT}",
            "tools": tools,
            "controller": controller_to_dict(controller),
        }
        return persist_result(result) if persist else result

    with tempfile.TemporaryDirectory(prefix="marl_traffic_sumo_") as tmp:
        run_dir = Path(tmp)
        for file in SCENARIO_ROOT.iterdir():
            if file.is_file() and file.suffix in {".xml", ".sumocfg"}:
                shutil.copy2(file, run_dir / file.name)

        net_source = _packaged_cross_network()
        if net_source is not None:
            shutil.copy2(net_source, run_dir / "one_intersection.net.xml")
            network_source = "packaged-cross-net"
        elif tools["netconvert"]["available"]:
            net_result = subprocess.run(
                [
                    tools["netconvert"]["path"],
                    "--node-files",
                    "one_intersection.nod.xml",
                    "--edge-files",
                    "one_intersection.edg.xml",
                    "--output-file",
                    "one_intersection.net.xml",
                    "--tls.guess",
                    "true",
                ],
                cwd=run_dir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            if net_result.returncode != 0:
                result = {
                    "ok": False,
                    "skipped": False,
                    "stage": "netconvert",
                    "returncode": net_result.returncode,
                    "stdout": net_result.stdout[-2000:],
                    "stderr": net_result.stderr[-2000:],
                    "tools": tools,
                    "controller": controller_to_dict(controller),
                }
                return persist_result(result) if persist else result
            network_source = "netconvert"
        else:
            result = {
                "ok": False,
                "skipped": True,
                "reason": "SUMO is installed, but neither packaged cross.net.xml nor netconvert is available.",
                "tools": tools,
                "controller": controller_to_dict(controller),
            }
            return persist_result(result) if persist else result

        started = time.perf_counter()
        sumo_result = subprocess.run(
            [
                tools["sumo"]["path"],
                "-c",
                "one_intersection.sumocfg",
                "--no-step-log",
                "true",
                "--duration-log.disable",
                "true",
                "--tripinfo-output",
                "tripinfo.xml",
            ],
            cwd=run_dir,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        if sumo_result.returncode != 0:
            result = {
                "ok": False,
                "skipped": False,
                "stage": "sumo",
                "returncode": sumo_result.returncode,
                "stdout": sumo_result.stdout[-2000:],
                "stderr": sumo_result.stderr[-2000:],
                "tools": tools,
                "controller": controller_to_dict(controller),
            }
            return persist_result(result) if persist else result

        metrics = parse_tripinfo(run_dir / "tripinfo.xml")
        result = {
            "ok": True,
            "skipped": False,
            "scenario": "synthetic/one_intersection",
            "network_source": network_source,
            "controller": controller_to_dict(controller),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "tools": tools,
            "metrics": metrics,
            "limitations": [
                "Open-loop subprocess run. Use TraCI baseline endpoints for controlled signal execution.",
            ],
        }
        return persist_result(result) if persist else result


def run_one_intersection_traci_baseline(
    controller_name: str,
    timeout_seconds: int = 45,
    persist: bool = True,
    seed: int = 1,
    demand_profile: str | None = None,
    scenario_id: str | None = None,
) -> dict:
    try:
        controller = get_controller(controller_name)
        scenario = get_scenario(scenario_id)
    except ValueError as error:
        return {"ok": False, "skipped": False, "error": str(error)}
    if scenario.network != "packaged-cross-net":
        result = {
            "ok": False,
            "skipped": True,
            "reason": f"Scenario '{scenario.scenario_id}' is cataloged but not executable by the one-intersection runner yet.",
            "scenario": scenario.scenario_id,
            "scenario_id": scenario.scenario_id,
            "scenario_spec": scenario_to_dict(scenario),
            "controller": controller_to_dict(controller),
        }
        return persist_result(result) if persist else result
    demand_profile = demand_profile or scenario.demand_profile

    tools = detect_sumo_tools()
    if not tools["ready"]:
        result = {
            "ok": False,
            "skipped": True,
            "reason": "SUMO is not available.",
            "tools": tools,
            "controller": controller_to_dict(controller),
        }
        return persist_result(result) if persist else result

    try:
        import traci  # type: ignore
    except Exception as error:
        result = {
            "ok": False,
            "skipped": True,
            "reason": f"TraCI Python package is unavailable: {error}",
            "tools": tools,
            "controller": controller_to_dict(controller),
        }
        return persist_result(result) if persist else result

    with tempfile.TemporaryDirectory(prefix="marl_traffic_traci_") as tmp:
        run_dir = Path(tmp)
        for file in SCENARIO_ROOT.iterdir():
            if file.is_file() and file.suffix in {".xml", ".sumocfg"}:
                shutil.copy2(file, run_dir / file.name)
        _write_routes(run_dir / "one_intersection.rou.xml", demand_profile=demand_profile, seed=seed)

        net_source = _packaged_cross_network()
        if net_source is None:
            result = {
                "ok": False,
                "skipped": True,
                "reason": "Packaged SUMO cross.net.xml not found.",
                "tools": tools,
                "controller": controller_to_dict(controller),
            }
            return persist_result(result) if persist else result
        shutil.copy2(net_source, run_dir / "one_intersection.net.xml")

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
            str(seed),
        ]

        label = f"marl_{controller_name}_{time.time_ns()}"
        started = time.perf_counter()
        time_series: list[dict] = []
        phase_changes = 0
        last_phase = None
        current_green_start = 0.0
        tls_id = None
        conn = None

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
            pending_phase = None
            pending_at = None

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

                selected_phase = _select_phase(
                    conn=conn,
                    tls_id=tls_id,
                    controller_name=controller_name,
                    program=program,
                    controlled_links=controlled_links,
                    candidate_phases=candidate_phases,
                    sim_time=sim_time,
                    current_green_start=current_green_start,
                    current_phase=last_phase,
                )

                if selected_phase is not None and selected_phase != last_phase and pending_phase is None:
                    yellow_phase = _yellow_after(last_phase)
                    if controller_name != "fixed_time" and yellow_phase is not None and selected_phase in candidate_phases:
                        conn.trafficlight.setPhase(tls_id, yellow_phase)
                        last_phase = yellow_phase
                        pending_phase = selected_phase
                        pending_at = sim_time + 3
                        phase_changes += 1
                    else:
                        conn.trafficlight.setPhase(tls_id, selected_phase)
                        last_phase = selected_phase
                        current_green_start = sim_time
                        phase_changes += 1

                conn.simulationStep()

                if int(sim_time) % 10 == 0:
                    time_series.append(_snapshot(conn, tls_id, sim_time))

            duration_ms = round((time.perf_counter() - started) * 1000, 2)
        except Exception as error:
            result = {
                "ok": False,
                "skipped": False,
                "stage": "traci",
                "error": str(error),
                "tools": tools,
                "controller": controller_to_dict(controller),
            }
            return persist_result(result) if persist else result
        finally:
            try:
                if conn is not None:
                    conn.close()
            except Exception:
                pass

        metrics = parse_tripinfo(tripinfo)
        metrics.update(_aggregate_time_series(time_series))
        result = {
            "ok": True,
            "skipped": False,
            "scenario": scenario.scenario_id,
            "scenario_id": scenario.scenario_id,
            "scenario_spec": scenario_to_dict(scenario),
            "network_source": "packaged-cross-net",
            "execution": "traci_controlled",
            "controller": controller_to_dict(controller),
            "seed": seed,
            "demand_profile": demand_profile,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "phase_changes": phase_changes,
            "tools": tools,
            "metrics": metrics,
            "time_series": time_series[-40:],
            "limitations": [
                "Phase 4 uses TraCI to set traffic-light phases.",
                "The network is SUMO's packaged cross scenario for reliable local smoke testing.",
                "Controller logic is intentionally minimal and will be expanded before MARL comparisons.",
            ],
        }
        return persist_result(result) if persist else result


def _candidate_green_phases(program) -> list[int]:
    phases = []
    for index, phase in enumerate(program.phases):
        state = phase.state
        if "G" in state or "g" in state:
            if "y" not in state.lower():
                phases.append(index)
    return phases


def _write_routes(path: Path, demand_profile: str, seed: int) -> None:
    profiles = {
        "balanced": {"north_south": 7, "south_north": 8, "east_west": 6, "west_east": 9},
        "east_west_peak": {"north_south": 10, "south_north": 11, "east_west": 4, "west_east": 5},
        "north_south_peak": {"north_south": 4, "south_north": 5, "east_west": 10, "west_east": 11},
    }
    periods = profiles.get(demand_profile)
    if periods is None:
        allowed = ", ".join(sorted(profiles))
        raise ValueError(f"Unknown demand profile '{demand_profile}'. Expected one of: {allowed}")

    jitter = seed % 3
    route_edges = {
        "east_west": "1fi 1si 2o 2fo",
        "west_east": "2fi 2si 1o 1fo",
        "north_south": "3fi 3si 4o 4fo",
        "south_north": "4fi 4si 3o 3fo",
    }
    lines = [
        "<routes>",
        '  <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="5.0" maxSpeed="13.89"/>',
    ]
    for route_id, edges in route_edges.items():
        lines.append(f'  <route id="{route_id}" edges="{edges}"/>')
    for index, route_id in enumerate(route_edges):
        period = max(3, periods[route_id] + ((jitter + index) % 2))
        lines.append(
            f'  <flow id="flow_{route_id}" type="car" route="{route_id}" begin="0" end="300" period="{period}"/>'
        )
    lines.append("</routes>")
    path.write_text("\n".join(lines), encoding="utf-8")


def _yellow_after(phase: int | None) -> int | None:
    return {
        0: 1,
        2: 3,
        4: 5,
        6: 7,
    }.get(phase)


def _select_phase(conn, tls_id: str, controller_name: str, program, controlled_links, candidate_phases: list[int], sim_time: float, current_green_start: float, current_phase: int | None) -> int | None:
    if controller_name == "fixed_time":
        cycle = int(sim_time) % 72
        if cycle < 33:
            return 0 if 0 in candidate_phases else candidate_phases[0]
        if cycle < 36:
            return 1
        if cycle < 69:
            return 4 if 4 in candidate_phases else candidate_phases[-1]
        return 5

    elapsed = sim_time - current_green_start
    if current_phase is not None and elapsed < 10:
        return current_phase

    if controller_name == "actuated":
        scores = {phase: _phase_incoming_queue(conn, program.phases[phase].state, controlled_links) for phase in candidate_phases}
        best = max(scores, key=scores.get)
        if current_phase is not None and elapsed < 45 and scores.get(current_phase, 0) >= 6:
            return current_phase
        return best

    if controller_name == "max_pressure":
        scores = {phase: _phase_pressure(conn, program.phases[phase].state, controlled_links) for phase in candidate_phases}
        return max(scores, key=scores.get)

    return current_phase


def _phase_incoming_queue(conn, state: str, controlled_links) -> float:
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


def _phase_pressure(conn, state: str, controlled_links) -> float:
    pressure = 0.0
    seen = set()
    for index, signal in enumerate(state):
        if signal not in {"G", "g"} or index >= len(controlled_links):
            continue
        for link in controlled_links[index]:
            incoming, outgoing = link[0], link[1]
            key = (incoming, outgoing)
            if not incoming or key in seen:
                continue
            seen.add(key)
            incoming_q = conn.lane.getLastStepHaltingNumber(incoming)
            outgoing_q = conn.lane.getLastStepHaltingNumber(outgoing) if outgoing else 0
            pressure += incoming_q - outgoing_q
    return pressure


def _snapshot(conn, tls_id: str, sim_time: float) -> dict:
    lane_ids = conn.lane.getIDList()
    queue = sum(conn.lane.getLastStepHaltingNumber(lane_id) for lane_id in lane_ids)
    vehicles = conn.vehicle.getIDCount()
    waiting = sum(conn.vehicle.getWaitingTime(vehicle_id) for vehicle_id in conn.vehicle.getIDList())
    return {
        "time": round(sim_time, 1),
        "phase": conn.trafficlight.getPhase(tls_id),
        "vehicles": vehicles,
        "queue": int(queue),
        "total_waiting_time": round(waiting, 3),
    }


def _aggregate_time_series(time_series: list[dict]) -> dict:
    if not time_series:
        return {
            "average_queue": 0,
            "max_queue": 0,
            "average_active_vehicles": 0,
        }
    return {
        "average_queue": round(sum(row["queue"] for row in time_series) / len(time_series), 3),
        "max_queue": max(row["queue"] for row in time_series),
        "average_active_vehicles": round(sum(row["vehicles"] for row in time_series) / len(time_series), 3),
    }


def _detect_tool(name: str) -> ToolStatus:
    path = shutil.which(name)
    if path:
        return ToolStatus(name=name, path=path, available=True)

    home = _sumo_home()
    if home is not None:
        candidate = home / "bin" / f"{name}.exe"
        if candidate.exists():
            return ToolStatus(name=name, path=str(candidate), available=True)
        candidate = home / "bin" / name
        if candidate.exists():
            return ToolStatus(name=name, path=str(candidate), available=True)

    return ToolStatus(name=name, path=None, available=False)


def _sumo_home() -> Path | None:
    env_home = os.environ.get("SUMO_HOME")
    if env_home:
        env_path = Path(env_home)
        if env_path.exists():
            return env_path
    common_linux = Path("/usr/share/sumo")
    if common_linux.exists():
        os.environ["SUMO_HOME"] = str(common_linux)
        return common_linux
    try:
        import sumo  # type: ignore

        os.environ["SUMO_HOME"] = str(sumo.SUMO_HOME)
        return Path(sumo.SUMO_HOME)
    except Exception:
        return None


def _packaged_cross_network() -> Path | None:
    home = _sumo_home()
    if home is None:
        return None
    candidate = home / "tools" / "game" / "cross" / "cross.net.xml"
    return candidate if candidate.exists() else None


def parse_tripinfo(path: Path) -> dict:
    if not path.exists():
        return {
            "vehicles_arrived": 0,
            "average_duration_s": 0,
            "average_waiting_time_s": 0,
            "average_time_loss_s": 0,
        }

    root = ET.parse(path).getroot()
    trips = root.findall("tripinfo")
    if not trips:
        return {
            "vehicles_arrived": 0,
            "average_duration_s": 0,
            "average_waiting_time_s": 0,
            "average_time_loss_s": 0,
        }

    def avg(attr: str) -> float:
        values = [float(trip.attrib.get(attr, "0")) for trip in trips]
        return round(sum(values) / len(values), 3)

    return {
        "vehicles_arrived": len(trips),
        "average_duration_s": avg("duration"),
        "average_waiting_time_s": avg("waitingTime"),
        "average_time_loss_s": avg("timeLoss"),
    }
