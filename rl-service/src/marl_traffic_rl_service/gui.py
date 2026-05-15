from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from .osm_runner import _generate_routes, _prepare_imported_scenario, _write_config
from .scenarios import get_scenario, scenario_to_dict
from .sumo import SCENARIO_ROOT, _packaged_cross_network, _write_routes, detect_sumo_tools


REPO_ROOT = Path(__file__).resolve().parents[3]
GUI_RUN_ROOT = REPO_ROOT / "experiments" / "gui"


def launch_sumo_gui(
    scenario_id: str,
    seed: int = 1,
    end_time: int = 300,
    period: int = 8,
    demand_profile: str | None = None,
) -> dict:
    tools = detect_sumo_tools()
    sumo_gui = tools.get("sumo_gui", {})
    if not sumo_gui.get("available"):
        return {
            "ok": False,
            "skipped": True,
            "reason": "sumo-gui is not available. Install SUMO desktop tools and ensure sumo-gui is on PATH.",
            "tools": tools,
        }

    try:
        scenario = get_scenario(scenario_id)
    except ValueError as error:
        return {"ok": False, "skipped": False, "error": str(error), "tools": tools}

    if scenario.source == "osm-import":
        prepared = _prepare_imported_scenario(scenario_id, persist=False)
        if not prepared["ok"]:
            return prepared
        scenario_dir = prepared["scenario_dir"]
        routes_path = scenario_dir / "gui_generated.rou.xml"
        config_path = scenario_dir / "gui.sumocfg"
        route_result = _generate_routes(
            net_path=prepared["net_path"],
            routes_path=routes_path,
            seed=seed,
            end_time=end_time,
            period=period,
        )
        if route_result["returncode"] != 0:
            return {
                "ok": False,
                "skipped": False,
                "stage": "route_generation",
                "reason": "randomTrips.py failed before launching SUMO-GUI.",
                "returncode": route_result["returncode"],
                "stdout": route_result["stdout"],
                "stderr": route_result["stderr"],
                "tools": tools,
            }
        _write_config(config_path, prepared["net_path"], routes_path, end_time)
        cwd = scenario_dir
    elif scenario.network == "packaged-cross-net":
        GUI_RUN_ROOT.mkdir(parents=True, exist_ok=True)
        run_dir = GUI_RUN_ROOT / f"synthetic_{int(time.time())}_{seed}"
        run_dir.mkdir(parents=True, exist_ok=True)
        for file in SCENARIO_ROOT.iterdir():
            if file.is_file() and file.suffix in {".xml", ".sumocfg"}:
                shutil.copy2(file, run_dir / file.name)
        net_source = _packaged_cross_network()
        if net_source is None:
            return {
                "ok": False,
                "skipped": True,
                "reason": "Packaged SUMO cross.net.xml was not found.",
                "tools": tools,
            }
        shutil.copy2(net_source, run_dir / "one_intersection.net.xml")
        _write_routes(run_dir / "one_intersection.rou.xml", demand_profile or scenario.demand_profile, seed)
        config_path = run_dir / "one_intersection.sumocfg"
        cwd = run_dir
    else:
        return {
            "ok": False,
            "skipped": True,
            "reason": f"Scenario '{scenario.scenario_id}' is not launchable in SUMO-GUI yet.",
            "scenario": scenario_to_dict(scenario),
            "tools": tools,
        }

    process = subprocess.Popen(
        [
            sumo_gui["path"],
            "-c",
            str(config_path),
            "--start",
            "--quit-on-end",
            "--delay",
            "80",
        ],
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return {
        "ok": True,
        "skipped": False,
        "message": "SUMO-GUI launched. It opens as a native desktop window, not inside the browser.",
        "pid": process.pid,
        "scenario_id": scenario.scenario_id,
        "config_path": str(config_path),
        "tools": tools,
    }
