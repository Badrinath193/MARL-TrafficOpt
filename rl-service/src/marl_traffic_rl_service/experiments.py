from __future__ import annotations

import json
import csv
import statistics
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = REPO_ROOT / "experiments" / "results"
EXPORTS_DIR = REPO_ROOT / "experiments" / "exports"


def persist_result(result: dict) -> dict:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = result.get("run_id") or f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"
    result = {**result, "run_id": run_id}
    path = RESULTS_DIR / f"{run_id}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return {**result, "result_path": str(path)}


def persist_experiment_bundle(bundle: dict) -> dict:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    experiment_id = bundle.get("experiment_id") or f"exp_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"
    bundle = {**bundle, "experiment_id": experiment_id}
    json_path = EXPORTS_DIR / f"{experiment_id}.json"
    csv_path = EXPORTS_DIR / f"{experiment_id}.csv"
    json_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    write_experiment_csv(bundle, csv_path)
    return {**bundle, "json_export_path": str(json_path), "csv_export_path": str(csv_path)}


def list_results() -> list[dict]:
    if not RESULTS_DIR.exists():
        return []
    rows = []
    for path in sorted(RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            rows.append(
                {
                    "run_id": data.get("run_id", path.stem),
                    "controller": data.get("controller", {}).get("name"),
                    "ok": data.get("ok"),
                    "scenario": data.get("scenario"),
                    "scenario_id": data.get("scenario_id", data.get("scenario")),
                    "demand_profile": data.get("demand_profile"),
                    "seed": data.get("seed"),
                    "training": data.get("training"),
                    "created_at": data.get("created_at"),
                    "result_path": str(path),
                    "execution": data.get("execution"),
                    "phase_changes": data.get("phase_changes"),
                    "metrics": data.get("metrics", {}),
                }
            )
        except json.JSONDecodeError:
            continue
    return rows


def get_result(run_id: str) -> dict:
    path = RESULTS_DIR / f"{run_id}.json"
    if not path.exists():
        return {"ok": False, "error": f"Result not found: {run_id}"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return {"ok": False, "error": f"Invalid result JSON: {error}"}
    return {
        "ok": True,
        "result": data,
        "telemetry": summarize_time_series(data.get("time_series", [])),
    }


def list_exports() -> list[dict]:
    if not EXPORTS_DIR.exists():
        return []
    rows = []
    for path in sorted(EXPORTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        experiment_id = data.get("experiment_id", path.stem)
        rows.append(
            {
                "experiment_id": experiment_id,
                "ok": data.get("ok"),
                "scenario_id": data.get("scenario_id", data.get("scenario")),
                "experiment_type": data.get("experiment_type", data.get("algorithm", "synthetic_baseline")),
                "controllers": data.get("controllers"),
                "seeds": data.get("seeds"),
                "runs": len(data.get("runs", [])),
                "created_at": data.get("created_at"),
                "json_export_path": str(path),
                "csv_export_path": str(EXPORTS_DIR / f"{experiment_id}.csv"),
                "aggregate": data.get("aggregate", {}),
            }
        )
    return rows


def get_export(experiment_id: str) -> dict:
    path = EXPORTS_DIR / f"{experiment_id}.json"
    if not path.exists():
        return {"ok": False, "error": f"Experiment export not found: {experiment_id}"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return {"ok": False, "error": f"Invalid experiment export JSON: {error}"}
    return {
        "ok": True,
        "export": data,
        "run_count": len(data.get("runs", [])),
        "aggregate": data.get("aggregate", {}),
    }


def summarize_time_series(time_series: list[dict]) -> dict:
    if not time_series:
        return {
            "samples": 0,
            "queue": {"min": 0, "max": 0, "mean": 0},
            "vehicles": {"min": 0, "max": 0, "mean": 0},
        }
    queues = [row.get("queue", 0) for row in time_series if isinstance(row.get("queue", 0), int | float)]
    vehicles = [row.get("vehicles", 0) for row in time_series if isinstance(row.get("vehicles", 0), int | float)]

    def stats(values: list[int | float]) -> dict:
        if not values:
            return {"min": 0, "max": 0, "mean": 0}
        return {
            "min": min(values),
            "max": max(values),
            "mean": round(statistics.mean(values), 3),
        }

    return {
        "samples": len(time_series),
        "queue": stats(queues),
        "vehicles": stats(vehicles),
        "last_sample": time_series[-1],
    }


def compare_results(scenario_id: str | None = None, demand_profile: str | None = None) -> dict:
    rows = [
        row
        for row in list_results()
        if row.get("ok")
        and row.get("controller")
        and not row.get("training")
        and (scenario_id is None or row.get("scenario_id") == scenario_id)
        and (demand_profile is None or row.get("demand_profile") == demand_profile)
    ]
    return {
        "filters": {
            "scenario_id": scenario_id,
            "demand_profile": demand_profile,
        },
        "runs": len(rows),
        "controllers": aggregate_runs(rows),
        "latest_runs": rows[:20],
    }


def aggregate_runs(runs: list[dict]) -> dict:
    metrics = [
        "vehicles_arrived",
        "average_duration_s",
        "average_waiting_time_s",
        "average_time_loss_s",
        "average_queue",
        "max_queue",
        "average_active_vehicles",
    ]
    by_controller: dict[str, list[dict]] = {}
    for run in runs:
        controller_value = run.get("controller", "unknown")
        controller = controller_value.get("name", "unknown") if isinstance(controller_value, dict) else controller_value
        by_controller.setdefault(controller, []).append(run)

    aggregate = {}
    for controller, controller_runs in by_controller.items():
        aggregate[controller] = {
            "runs": len(controller_runs),
            "ok_runs": sum(1 for run in controller_runs if run.get("ok")),
            "metrics": {},
        }
        for metric in metrics:
            values = [
                run.get("metrics", {}).get(metric)
                for run in controller_runs
                if isinstance(run.get("metrics", {}).get(metric), int | float)
            ]
            if not values:
                continue
            aggregate[controller]["metrics"][metric] = {
                "mean": round(statistics.mean(values), 4),
                "stdev": round(statistics.stdev(values), 4) if len(values) > 1 else 0,
                "min": min(values),
                "max": max(values),
            }
    return aggregate


def write_experiment_csv(bundle: dict, path: Path) -> None:
    rows = []
    for run in bundle.get("runs", []):
        metrics = run.get("metrics", {})
        rows.append(
            {
                "experiment_id": bundle.get("experiment_id"),
                "run_id": run.get("run_id"),
                "controller": run.get("controller", {}).get("name"),
                "seed": run.get("seed"),
                "demand_profile": run.get("demand_profile"),
                "ok": run.get("ok"),
                "vehicles_arrived": metrics.get("vehicles_arrived"),
                "average_duration_s": metrics.get("average_duration_s"),
                "average_waiting_time_s": metrics.get("average_waiting_time_s"),
                "average_time_loss_s": metrics.get("average_time_loss_s"),
                "average_queue": metrics.get("average_queue"),
                "max_queue": metrics.get("max_queue"),
                "phase_changes": run.get("phase_changes"),
            }
        )

    fieldnames = list(rows[0].keys()) if rows else ["experiment_id"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
