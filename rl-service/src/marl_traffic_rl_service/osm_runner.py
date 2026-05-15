from __future__ import annotations

import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from .experiments import persist_result
from .scenarios import get_scenario, scenario_to_dict
from .sumo import _sumo_home, detect_sumo_tools, parse_tripinfo


def inspect_imported_osm_scenario(scenario_id: str) -> dict:
    prepared = _prepare_imported_scenario(scenario_id, persist=False)
    if not prepared["ok"]:
        return prepared

    try:
        root = ET.parse(prepared["net_path"]).getroot()
    except ET.ParseError as error:
        return {"ok": False, "skipped": False, "error": f"Invalid SUMO network XML: {error}"}

    junctions = root.findall("junction")
    edges = [edge for edge in root.findall("edge") if not edge.attrib.get("function")]
    traffic_lights = [
        junction.attrib.get("id")
        for junction in junctions
        if junction.attrib.get("type") == "traffic_light" and junction.attrib.get("id")
    ]
    return {
        "ok": True,
        "scenario": prepared["scenario"].scenario_id,
        "scenario_id": prepared["scenario"].scenario_id,
        "scenario_spec": scenario_to_dict(prepared["scenario"]),
        "network": {
            "path": str(prepared["net_path"]),
            "junctions": len(junctions),
            "edges": len(edges),
            "traffic_lights": traffic_lights,
            "traffic_light_count": len(traffic_lights),
        },
    }


def run_imported_osm_fixed_time(
    scenario_id: str,
    seed: int = 1,
    end_time: int = 300,
    period: int = 8,
    green_steps: int = 30,
    persist: bool = True,
) -> dict:
    prepared = _prepare_imported_scenario(scenario_id, persist=persist)
    if not prepared["ok"]:
        return prepared

    tools = prepared["tools"]
    scenario = prepared["scenario"]
    scenario_dir = prepared["scenario_dir"]
    routes_path = scenario_dir / "generated.rou.xml"
    tripinfo_path = scenario_dir / "traci_fixed_time_tripinfo.xml"
    config_path = scenario_dir / "osm_traci_fixed_time.sumocfg"

    route_result = _generate_routes(
        net_path=prepared["net_path"],
        routes_path=routes_path,
        seed=seed,
        end_time=end_time,
        period=period,
    )
    if route_result["returncode"] != 0:
        result = {
            "ok": False,
            "skipped": False,
            "stage": "route_generation",
            "reason": "randomTrips.py failed to generate valid routes.",
            "scenario": scenario.scenario_id,
            "scenario_id": scenario.scenario_id,
            "scenario_spec": scenario_to_dict(scenario),
            "returncode": route_result["returncode"],
            "stdout": route_result["stdout"],
            "stderr": route_result["stderr"],
            "tools": tools,
        }
        return persist_result(result) if persist else result

    _write_config(config_path, prepared["net_path"], routes_path, end_time)

    try:
        import traci  # type: ignore
    except Exception as error:
        return _skip_result(
            scenario=scenario,
            reason=f"TraCI Python package is unavailable: {error}",
            persist=persist,
            extra={"tools": tools},
        )

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
        str(seed),
    ]
    label = f"marl_osm_fixed_time_{time.time_ns()}"
    started = time.perf_counter()
    time_series = []
    tls_phase_counts: dict[str, int] = {}
    phase_changes = 0
    conn = None

    try:
        traci.start(cmd, label=label, stdout=subprocess.DEVNULL)
        conn = traci.getConnection(label)
        tls_ids = list(conn.trafficlight.getIDList())
        if not tls_ids:
            result = {
                "ok": False,
                "skipped": True,
                "reason": "Imported OSM network has no controllable traffic lights.",
                "scenario": scenario.scenario_id,
                "scenario_id": scenario.scenario_id,
                "scenario_spec": scenario_to_dict(scenario),
                "network_inspection": inspect_imported_osm_scenario(scenario.scenario_id).get("network"),
                "tools": tools,
            }
            return persist_result(result) if persist else result

        for tls_id in tls_ids:
            program = conn.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)[0]
            tls_phase_counts[tls_id] = max(1, len(program.phases))

        while conn.simulation.getMinExpectedNumber() > 0:
            sim_time = conn.simulation.getTime()
            if sim_time > end_time:
                break

            for tls_id, phase_count in tls_phase_counts.items():
                target_phase = int(sim_time // green_steps) % phase_count
                if conn.trafficlight.getPhase(tls_id) != target_phase:
                    conn.trafficlight.setPhase(tls_id, target_phase)
                    phase_changes += 1

            conn.simulationStep()
            if int(sim_time) % 10 == 0:
                time_series.append(_snapshot_generic(conn, sim_time, tls_ids))

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
    except Exception as error:
        result = {
            "ok": False,
            "skipped": False,
            "stage": "traci_fixed_time",
            "error": str(error),
            "scenario": scenario.scenario_id,
            "scenario_id": scenario.scenario_id,
            "scenario_spec": scenario_to_dict(scenario),
            "tools": tools,
        }
        return persist_result(result) if persist else result
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass

    metrics = parse_tripinfo(tripinfo_path)
    metrics.update(_route_stats(routes_path))
    metrics.update(_aggregate_generic_time_series(time_series))
    result = {
        "ok": True,
        "skipped": False,
        "scenario": scenario.scenario_id,
        "scenario_id": scenario.scenario_id,
        "scenario_spec": scenario_to_dict(scenario),
        "network_source": scenario.network,
        "execution": "imported_osm_traci_fixed_time",
        "controller": {
            "name": "osm_fixed_time",
            "display_name": "OSM Fixed-Time",
            "description": "Fixed-time TraCI controller applied to all discovered imported-network traffic lights.",
            "execution_mode": "traci_controlled",
            "parameters": {
                "seed": seed,
                "end_time": end_time,
                "period": period,
                "green_steps": green_steps,
                "traffic_lights": list(tls_phase_counts),
            },
        },
        "seed": seed,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": duration_ms,
        "phase_changes": phase_changes,
        "tools": tools,
        "route_generation": {
            "routes_path": str(routes_path),
            "stdout": route_result["stdout"],
            "stderr": route_result["stderr"],
        },
        "metrics": metrics,
        "time_series": time_series[-40:],
        "limitations": [
            "Phase 10 imported OSM fixed-time control uses generic phase cycling.",
            "It does not yet optimize phases or use MaxPressure on imported networks.",
        ],
    }
    return persist_result(result) if persist else result


def run_imported_osm_max_pressure(
    scenario_id: str,
    seed: int = 1,
    end_time: int = 300,
    period: int = 8,
    min_green: int = 10,
    persist: bool = True,
) -> dict:
    prepared = _prepare_imported_scenario(scenario_id, persist=persist)
    if not prepared["ok"]:
        return prepared

    tools = prepared["tools"]
    scenario = prepared["scenario"]
    scenario_dir = prepared["scenario_dir"]
    routes_path = scenario_dir / "generated.rou.xml"
    tripinfo_path = scenario_dir / "traci_max_pressure_tripinfo.xml"
    config_path = scenario_dir / "osm_traci_max_pressure.sumocfg"

    route_result = _generate_routes(
        net_path=prepared["net_path"],
        routes_path=routes_path,
        seed=seed,
        end_time=end_time,
        period=period,
    )
    if route_result["returncode"] != 0:
        result = {
            "ok": False,
            "skipped": False,
            "stage": "route_generation",
            "reason": "randomTrips.py failed to generate valid routes.",
            "scenario": scenario.scenario_id,
            "scenario_id": scenario.scenario_id,
            "scenario_spec": scenario_to_dict(scenario),
            "returncode": route_result["returncode"],
            "stdout": route_result["stdout"],
            "stderr": route_result["stderr"],
            "tools": tools,
        }
        return persist_result(result) if persist else result

    _write_config(config_path, prepared["net_path"], routes_path, end_time)

    try:
        import traci  # type: ignore
    except Exception as error:
        return _skip_result(
            scenario=scenario,
            reason=f"TraCI Python package is unavailable: {error}",
            persist=persist,
            extra={"tools": tools},
        )

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
        str(seed),
    ]
    label = f"marl_osm_max_pressure_{time.time_ns()}"
    started = time.perf_counter()
    time_series = []
    tls_programs = {}
    tls_links = {}
    tls_green_phases = {}
    tls_green_start = {}
    phase_changes = 0
    conn = None

    try:
        traci.start(cmd, label=label, stdout=subprocess.DEVNULL)
        conn = traci.getConnection(label)
        tls_ids = list(conn.trafficlight.getIDList())
        if not tls_ids:
            result = {
                "ok": False,
                "skipped": True,
                "reason": "Imported OSM network has no controllable traffic lights.",
                "scenario": scenario.scenario_id,
                "scenario_id": scenario.scenario_id,
                "scenario_spec": scenario_to_dict(scenario),
                "network_inspection": inspect_imported_osm_scenario(scenario.scenario_id).get("network"),
                "tools": tools,
            }
            return persist_result(result) if persist else result

        for tls_id in tls_ids:
            program = conn.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)[0]
            green_phases = _candidate_green_phases(program)
            if not green_phases:
                green_phases = list(range(max(1, len(program.phases))))
            tls_programs[tls_id] = program
            tls_links[tls_id] = conn.trafficlight.getControlledLinks(tls_id)
            tls_green_phases[tls_id] = green_phases
            tls_green_start[tls_id] = 0.0

        while conn.simulation.getMinExpectedNumber() > 0:
            sim_time = conn.simulation.getTime()
            if sim_time > end_time:
                break

            for tls_id in tls_ids:
                current = conn.trafficlight.getPhase(tls_id)
                if sim_time - tls_green_start[tls_id] < min_green:
                    continue
                scores = {
                    phase: _phase_pressure(conn, tls_programs[tls_id].phases[phase].state, tls_links[tls_id])
                    for phase in tls_green_phases[tls_id]
                }
                target_phase = max(scores, key=scores.get)
                if target_phase != current:
                    conn.trafficlight.setPhase(tls_id, target_phase)
                    tls_green_start[tls_id] = sim_time
                    phase_changes += 1

            conn.simulationStep()
            if int(sim_time) % 10 == 0:
                time_series.append(_snapshot_generic(conn, sim_time, tls_ids))

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
    except Exception as error:
        result = {
            "ok": False,
            "skipped": False,
            "stage": "traci_max_pressure",
            "error": str(error),
            "scenario": scenario.scenario_id,
            "scenario_id": scenario.scenario_id,
            "scenario_spec": scenario_to_dict(scenario),
            "tools": tools,
        }
        return persist_result(result) if persist else result
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass

    metrics = parse_tripinfo(tripinfo_path)
    metrics.update(_route_stats(routes_path))
    metrics.update(_aggregate_generic_time_series(time_series))
    result = {
        "ok": True,
        "skipped": False,
        "scenario": scenario.scenario_id,
        "scenario_id": scenario.scenario_id,
        "scenario_spec": scenario_to_dict(scenario),
        "network_source": scenario.network,
        "execution": "imported_osm_traci_max_pressure",
        "controller": {
            "name": "osm_max_pressure",
            "display_name": "OSM MaxPressure",
            "description": "MaxPressure TraCI controller applied to imported-network traffic lights.",
            "execution_mode": "traci_controlled",
            "parameters": {
                "seed": seed,
                "end_time": end_time,
                "period": period,
                "min_green": min_green,
                "traffic_lights": tls_ids,
            },
        },
        "seed": seed,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": duration_ms,
        "phase_changes": phase_changes,
        "tools": tools,
        "route_generation": {
            "routes_path": str(routes_path),
            "stdout": route_result["stdout"],
            "stderr": route_result["stderr"],
        },
        "metrics": metrics,
        "time_series": time_series[-40:],
        "limitations": [
            "Phase 11 imported OSM MaxPressure uses queue pressure over SUMO controlled links.",
            "It does not yet include yellow-transition synthesis for arbitrary imported programs.",
        ],
    }
    return persist_result(result) if persist else result


def run_imported_osm_smoke(
    scenario_id: str,
    seed: int = 1,
    end_time: int = 300,
    period: int = 8,
    persist: bool = True,
) -> dict:
    prepared = _prepare_imported_scenario(scenario_id, persist=persist)
    if not prepared["ok"]:
        return prepared
    scenario = prepared["scenario"]
    scenario_dir = prepared["scenario_dir"]
    tools = prepared["tools"]
    random_trips = prepared["random_trips"]

    routes_path = scenario_dir / "generated.rou.xml"
    tripinfo_path = scenario_dir / "tripinfo.xml"
    config_path = scenario_dir / "osm_smoke.sumocfg"

    route_result = _generate_routes(
        net_path=prepared["net_path"],
        routes_path=routes_path,
        seed=seed,
        end_time=end_time,
        period=period,
    )
    if route_result["returncode"] != 0:
        result = {
            "ok": False,
            "skipped": False,
            "stage": "route_generation",
            "reason": "randomTrips.py failed to generate valid routes.",
            "scenario": scenario.scenario_id,
            "scenario_id": scenario.scenario_id,
            "scenario_spec": scenario_to_dict(scenario),
            "returncode": route_result["returncode"],
            "stdout": route_result["stdout"],
            "stderr": route_result["stderr"],
            "tools": tools,
        }
        return persist_result(result) if persist else result

    _write_config(config_path, prepared["net_path"], routes_path, end_time)

    started = time.perf_counter()
    sumo_result = subprocess.run(
        [
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
            str(seed),
        ],
        cwd=scenario_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    if sumo_result.returncode != 0:
        result = {
            "ok": False,
            "skipped": False,
            "stage": "sumo",
            "reason": "SUMO failed to run the imported OSM smoke scenario.",
            "scenario": scenario.scenario_id,
            "scenario_id": scenario.scenario_id,
            "scenario_spec": scenario_to_dict(scenario),
            "returncode": sumo_result.returncode,
            "stdout": sumo_result.stdout[-2000:],
            "stderr": sumo_result.stderr[-2000:],
            "tools": tools,
        }
        return persist_result(result) if persist else result

    result = {
        "ok": True,
        "skipped": False,
        "scenario": scenario.scenario_id,
        "scenario_id": scenario.scenario_id,
        "scenario_spec": scenario_to_dict(scenario),
        "network_source": scenario.network,
        "execution": "imported_osm_open_loop",
        "controller": {
            "name": "osm_open_loop",
            "display_name": "OSM Open Loop",
            "description": "Generic route-generation smoke runner for imported OSM networks.",
            "execution_mode": "sumo_open_loop",
            "parameters": {"seed": seed, "end_time": end_time, "period": period},
        },
        "seed": seed,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": duration_ms,
        "tools": tools,
        "route_generation": {
            "script": str(random_trips),
            "routes_path": str(routes_path),
            "stdout": route_result["stdout"],
            "stderr": route_result["stderr"],
        },
        "metrics": {
            **parse_tripinfo(tripinfo_path),
            **_route_stats(routes_path),
        },
        "limitations": [
            "Phase 9 imported OSM execution is open-loop and does not control traffic lights yet.",
            "Generated trips are synthetic random trips, not calibrated real demand.",
        ],
    }
    return persist_result(result) if persist else result


def _prepare_imported_scenario(scenario_id: str, persist: bool) -> dict:
    try:
        scenario = get_scenario(scenario_id)
    except ValueError as error:
        return {"ok": False, "skipped": False, "error": str(error)}

    if scenario.source != "osm-import":
        return {
            "ok": False,
            "skipped": True,
            "reason": "Only imported OSM scenarios can use the imported OSM runners.",
            "scenario": scenario.scenario_id,
            "scenario_id": scenario.scenario_id,
            "scenario_spec": scenario_to_dict(scenario),
        }

    if scenario.scenario_path is None:
        return {
            "ok": False,
            "skipped": True,
            "reason": "Imported scenario has no scenario_path metadata.",
            "scenario": scenario.scenario_id,
            "scenario_id": scenario.scenario_id,
            "scenario_spec": scenario_to_dict(scenario),
        }

    scenario_dir = Path(scenario.scenario_path)
    net_path = scenario_dir / "network.net.xml"
    if not net_path.exists():
        return _skip_result(
            scenario=scenario,
            reason="Imported scenario has no network.net.xml. Re-run OSM import with working netconvert before route generation.",
            persist=persist,
        )

    tools = detect_sumo_tools()
    if not tools["ready"]:
        return _skip_result(
            scenario=scenario,
            reason="SUMO is not available.",
            persist=persist,
            extra={"tools": tools},
        )

    random_trips = _random_trips_script()
    if random_trips is None:
        return _skip_result(
            scenario=scenario,
            reason="SUMO randomTrips.py was not found, so routes cannot be generated for the imported network.",
            persist=persist,
            extra={"tools": tools},
        )

    return {
        "ok": True,
        "scenario": scenario,
        "scenario_dir": scenario_dir,
        "net_path": net_path,
        "tools": tools,
        "random_trips": random_trips,
    }


def _generate_routes(net_path: Path, routes_path: Path, seed: int, end_time: int, period: int) -> dict:
    random_trips = _random_trips_script()
    if random_trips is None:
        return {"returncode": 1, "stdout": "", "stderr": "randomTrips.py not found"}
    result = subprocess.run(
        [
            "python",
            str(random_trips),
            "-n",
            str(net_path),
            "-r",
            str(routes_path),
            "--end",
            str(end_time),
            "--period",
            str(period),
            "--seed",
            str(seed),
            "--validate",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout[-2000:],
        "stderr": result.stderr[-2000:],
    }


def _write_config(config_path: Path, net_path: Path, routes_path: Path, end_time: int) -> None:
    config_path.write_text(
        "\n".join(
            [
                "<configuration>",
                "  <input>",
                f'    <net-file value="{net_path.name}"/>',
                f'    <route-files value="{routes_path.name}"/>',
                "  </input>",
                "  <time>",
                f'    <end value="{end_time}"/>',
                "  </time>",
                "</configuration>",
            ]
        ),
        encoding="utf-8",
    )


def _skip_result(scenario, reason: str, persist: bool, extra: dict | None = None) -> dict:
    result = {
        "ok": False,
        "skipped": True,
        "reason": reason,
        "scenario": scenario.scenario_id,
        "scenario_id": scenario.scenario_id,
        "scenario_spec": scenario_to_dict(scenario),
    }
    if extra:
        result.update(extra)
    return persist_result(result) if persist else result


def _random_trips_script() -> Path | None:
    home = _sumo_home()
    if home is None:
        return None
    candidate = home / "tools" / "randomTrips.py"
    return candidate if candidate.exists() else None


def _route_stats(path: Path) -> dict:
    if not path.exists():
        return {"routes_generated": 0, "vehicles_generated": 0}
    root = ET.parse(path).getroot()
    return {
        "routes_generated": len(root.findall("route")),
        "vehicles_generated": len(root.findall("vehicle")),
    }


def _candidate_green_phases(program) -> list[int]:
    phases = []
    for index, phase in enumerate(program.phases):
        state = phase.state
        if ("G" in state or "g" in state) and "y" not in state.lower():
            phases.append(index)
    return phases


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


def _snapshot_generic(conn, sim_time: float, tls_ids: list[str]) -> dict:
    lane_ids = conn.lane.getIDList()
    queue = sum(conn.lane.getLastStepHaltingNumber(lane_id) for lane_id in lane_ids)
    vehicles = conn.vehicle.getIDCount()
    waiting = sum(conn.vehicle.getWaitingTime(vehicle_id) for vehicle_id in conn.vehicle.getIDList())
    return {
        "time": round(sim_time, 1),
        "vehicles": vehicles,
        "queue": int(queue),
        "total_waiting_time": round(waiting, 3),
        "traffic_lights": {tls_id: conn.trafficlight.getPhase(tls_id) for tls_id in tls_ids},
    }


def _aggregate_generic_time_series(time_series: list[dict]) -> dict:
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
