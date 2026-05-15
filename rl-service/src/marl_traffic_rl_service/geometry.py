from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from .scenarios import get_scenario, scenario_to_dict
from .sumo import _packaged_cross_network


def get_scenario_geometry(scenario_id: str) -> dict:
    try:
        scenario = get_scenario(scenario_id)
    except ValueError as error:
        return {"ok": False, "error": str(error)}

    net_path = _network_path_for_scenario(scenario)
    if net_path is None or not net_path.exists():
        return {
            "ok": False,
            "skipped": True,
            "reason": "No SUMO network XML is available for this scenario.",
            "scenario": scenario.scenario_id,
            "scenario_id": scenario.scenario_id,
            "scenario_spec": scenario_to_dict(scenario),
        }

    try:
        root = ET.parse(net_path).getroot()
    except ET.ParseError as error:
        return {"ok": False, "error": f"Invalid SUMO network XML: {error}"}

    edges = []
    bounds = {"min_x": None, "min_y": None, "max_x": None, "max_y": None}
    for edge in root.findall("edge"):
        if edge.attrib.get("function") == "internal":
            continue
        lanes = edge.findall("lane")
        if not lanes:
            continue
        shape = _parse_shape(lanes[0].attrib.get("shape", ""))
        if len(shape) < 2:
            continue
        for point in shape:
            _expand_bounds(bounds, point)
        edges.append(
            {
                "id": edge.attrib.get("id"),
                "from": edge.attrib.get("from"),
                "to": edge.attrib.get("to"),
                "shape": shape,
                "lane_count": len(lanes),
            }
        )

    traffic_lights = []
    junctions = []
    for junction in root.findall("junction"):
        if junction.attrib.get("type") == "internal":
            continue
        point = {
            "x": float(junction.attrib.get("x", "0")),
            "y": float(junction.attrib.get("y", "0")),
        }
        _expand_bounds(bounds, point)
        row = {
            "id": junction.attrib.get("id"),
            "type": junction.attrib.get("type"),
            **point,
        }
        junctions.append(row)
        if row["type"] == "traffic_light":
            traffic_lights.append(row)

    return {
        "ok": True,
        "scenario": scenario.scenario_id,
        "scenario_id": scenario.scenario_id,
        "scenario_spec": scenario_to_dict(scenario),
        "network_path": str(net_path),
        "bounds": _final_bounds(bounds),
        "edges": edges,
        "junctions": junctions,
        "traffic_lights": traffic_lights,
        "summary": {
            "edges": len(edges),
            "junctions": len(junctions),
            "traffic_lights": len(traffic_lights),
        },
    }


def _network_path_for_scenario(scenario) -> Path | None:
    if scenario.source == "osm-import" and scenario.scenario_path:
        return Path(scenario.scenario_path) / "network.net.xml"
    if scenario.network == "packaged-cross-net":
        return _packaged_cross_network()
    return None


def _parse_shape(value: str) -> list[dict]:
    points = []
    for token in value.split():
        if "," not in token:
            continue
        x_value, y_value = token.split(",", 1)
        points.append({"x": float(x_value), "y": float(y_value)})
    return points


def _expand_bounds(bounds: dict, point: dict) -> None:
    x_value = point["x"]
    y_value = point["y"]
    bounds["min_x"] = x_value if bounds["min_x"] is None else min(bounds["min_x"], x_value)
    bounds["max_x"] = x_value if bounds["max_x"] is None else max(bounds["max_x"], x_value)
    bounds["min_y"] = y_value if bounds["min_y"] is None else min(bounds["min_y"], y_value)
    bounds["max_y"] = y_value if bounds["max_y"] is None else max(bounds["max_y"], y_value)


def _final_bounds(bounds: dict) -> dict:
    if bounds["min_x"] is None:
        return {"min_x": 0, "min_y": 0, "max_x": 1, "max_y": 1}
    return bounds
