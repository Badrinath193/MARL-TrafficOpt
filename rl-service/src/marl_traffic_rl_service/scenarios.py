from __future__ import annotations

import json
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
OSM_SCENARIO_ROOT = REPO_ROOT / "scenarios" / "osm"


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    display_name: str
    description: str
    network: str
    demand_profile: str
    status: str
    limitations: list[str]
    source: str = "built-in"
    scenario_path: str | None = None


SCENARIOS: dict[str, ScenarioSpec] = {
    "synthetic/one_intersection_balanced": ScenarioSpec(
        scenario_id="synthetic/one_intersection_balanced",
        display_name="One Intersection Balanced",
        description="Single signalized cross intersection with balanced four-direction demand.",
        network="packaged-cross-net",
        demand_profile="balanced",
        status="ready",
        limitations=["Uses SUMO's packaged cross network for reliable local execution."],
    ),
    "synthetic/one_intersection_east_west_peak": ScenarioSpec(
        scenario_id="synthetic/one_intersection_east_west_peak",
        display_name="One Intersection East-West Peak",
        description="Single signalized cross intersection with heavier east-west demand.",
        network="packaged-cross-net",
        demand_profile="east_west_peak",
        status="ready",
        limitations=["Demand changes, geometry remains the packaged cross network."],
    ),
    "synthetic/one_intersection_north_south_peak": ScenarioSpec(
        scenario_id="synthetic/one_intersection_north_south_peak",
        display_name="One Intersection North-South Peak",
        description="Single signalized cross intersection with heavier north-south demand.",
        network="packaged-cross-net",
        demand_profile="north_south_peak",
        status="ready",
        limitations=["Demand changes, geometry remains the packaged cross network."],
    ),
}


def list_scenarios() -> list[dict]:
    scenarios = [scenario_to_dict(scenario) for scenario in SCENARIOS.values()]
    scenarios.extend(scenario_to_dict(scenario) for scenario in _imported_scenarios())
    return scenarios


def get_scenario(scenario_id: str | None = None) -> ScenarioSpec:
    normalized = scenario_id or "synthetic/one_intersection_balanced"
    if normalized in SCENARIOS:
        return SCENARIOS[normalized]
    imported = {scenario.scenario_id: scenario for scenario in _imported_scenarios()}
    if normalized in imported:
        return imported[normalized]
    allowed = ", ".join(sorted([*SCENARIOS, *imported]))
    raise ValueError(f"Unknown scenario '{normalized}'. Expected one of: {allowed}")


def import_osm_scenario(
    source_path: str,
    display_name: str | None = None,
    scenario_slug: str | None = None,
    run_netconvert: bool = True,
) -> dict:
    source = _resolve_source_path(source_path)
    if not source.exists() or not source.is_file():
        return {"ok": False, "error": f"OSM source file not found: {source}"}
    if source.suffix.lower() not in {".osm", ".xml"} and not source.name.lower().endswith(".osm.xml"):
        return {"ok": False, "error": "Expected an .osm, .xml, or .osm.xml source file."}

    validation = validate_osm_file(source)
    if not validation["ok"]:
        return validation

    name = display_name or source.stem.replace(".osm", "").replace("_", " ").replace("-", " ").title()
    slug = _safe_slug(scenario_slug or name)
    scenario_dir = OSM_SCENARIO_ROOT / slug
    scenario_dir.mkdir(parents=True, exist_ok=True)
    osm_target = scenario_dir / "source.osm.xml"
    if source.resolve() != osm_target.resolve():
        shutil.copy2(source, osm_target)

    netconvert_result = _run_netconvert(
        osm_target,
        scenario_dir / "network.net.xml",
        tls_nodes=None,
    ) if run_netconvert else {
        "attempted": False,
        "ok": False,
        "reason": "netconvert execution disabled for this import.",
    }

    status = "ready" if netconvert_result.get("ok") else "imported"
    if netconvert_result.get("ok"):
        limitations = [
            "Ready for SUMO route generation, smoke runs, SUMO-GUI launch, and imported-network TraCI controllers.",
            "Demand is generated synthetically with SUMO randomTrips unless calibrated demand is provided.",
        ]
    else:
        limitations = [
            "OSM source was cataloged, but no executable SUMO network was produced.",
        ]
        limitations.append(netconvert_result.get("reason", "SUMO netconvert did not produce a network."))

    metadata = {
        "scenario_id": f"osm/{slug}",
        "display_name": name,
        "description": f"Imported OSM scenario from {source.name}.",
        "network": "osm-netconvert" if netconvert_result.get("ok") else "osm-source",
        "demand_profile": "external",
        "status": status,
        "limitations": limitations,
        "source": "osm-import",
        "scenario_path": str(scenario_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "osm_stats": validation["stats"],
        "netconvert": netconvert_result,
        "files": {
            "osm": str(osm_target),
            "net": str(scenario_dir / "network.net.xml") if (scenario_dir / "network.net.xml").exists() else None,
        },
    }
    (scenario_dir / "scenario.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {"ok": True, "scenario": metadata}


def search_and_import_osm_scenario(
    query: str,
    display_name: str | None = None,
    scenario_slug: str | None = None,
    run_netconvert: bool = True,
) -> dict:
    query = query.strip()
    if len(query) < 3:
        return {"ok": False, "error": "Enter a location search query with at least 3 characters."}

    geocode = _nominatim_search(query)
    if not geocode["ok"]:
        return geocode
    place = geocode["place"]
    bbox = place["boundingbox"]
    south, north, west, east = [float(value) for value in bbox]
    if abs(north - south) > 0.08 or abs(east - west) > 0.08:
        center_lat = (north + south) / 2
        center_lon = (east + west) / 2
        half_size = 0.025
        south, north = center_lat - half_size, center_lat + half_size
        west, east = center_lon - half_size, center_lon + half_size

    osm_xml = _download_overpass_highways(south=south, west=west, north=north, east=east)
    if not osm_xml["ok"]:
        return {**osm_xml, "geocode": place}

    name = display_name or place.get("display_name", query).split(",", 1)[0]
    slug = _safe_slug(scenario_slug or name)
    source_path = OSM_SCENARIO_ROOT / f"{slug}.osm.xml"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(osm_xml["xml"], encoding="utf-8")
    imported = import_osm_scenario(
        source_path=str(source_path),
        display_name=name,
        scenario_slug=slug,
        run_netconvert=run_netconvert,
    )
    imported["geocode"] = place
    imported["bbox"] = {"south": south, "west": west, "north": north, "east": east}
    return imported


def validate_osm_file(path: Path) -> dict:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        return {"ok": False, "error": f"Invalid XML: {error}"}
    if _strip_namespace(root.tag) != "osm":
        return {"ok": False, "error": f"Expected root <osm>, got <{root.tag}>."}
    nodes = 0
    ways = 0
    highways = 0
    highway_node_refs: dict[str, int] = {}
    traffic_signal_nodes = []
    for element in root:
        tag = _strip_namespace(element.tag)
        if tag == "node":
            nodes += 1
            if any(
                _strip_namespace(child.tag) == "tag"
                and child.attrib.get("k") == "highway"
                and child.attrib.get("v") == "traffic_signals"
                for child in element
            ):
                node_id = element.attrib.get("id")
                if node_id:
                    traffic_signal_nodes.append(node_id)
        elif tag == "way":
            ways += 1
            is_highway = any(_strip_namespace(child.tag) == "tag" and child.attrib.get("k") == "highway" for child in element)
            if is_highway:
                highways += 1
                for child in element:
                    if _strip_namespace(child.tag) == "nd" and child.attrib.get("ref"):
                        ref = child.attrib["ref"]
                        highway_node_refs[ref] = highway_node_refs.get(ref, 0) + 1
    if nodes == 0 or ways == 0:
        return {"ok": False, "error": "OSM file must contain at least one node and one way."}
    return {
        "ok": True,
        "stats": {
            "nodes": nodes,
            "ways": ways,
            "highway_ways": highways,
            "traffic_light_candidates": sorted(traffic_signal_nodes),
            "highway_intersection_candidates": sorted(ref for ref, count in highway_node_refs.items() if count >= 2)[:200],
        },
    }


def scenario_to_dict(scenario: ScenarioSpec) -> dict:
    return {
        "scenario_id": scenario.scenario_id,
        "display_name": scenario.display_name,
        "description": scenario.description,
        "network": scenario.network,
        "demand_profile": scenario.demand_profile,
        "status": scenario.status,
        "limitations": scenario.limitations,
        "source": scenario.source,
        "scenario_path": scenario.scenario_path,
    }


def _imported_scenarios() -> list[ScenarioSpec]:
    if not OSM_SCENARIO_ROOT.exists():
        return []
    scenarios = []
    for path in sorted(OSM_SCENARIO_ROOT.glob("*/scenario.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        scenarios.append(
            ScenarioSpec(
                scenario_id=data.get("scenario_id", f"osm/{path.parent.name}"),
                display_name=data.get("display_name", path.parent.name),
                description=data.get("description", "Imported OSM scenario."),
                network=data.get("network", "osm-source"),
                demand_profile=data.get("demand_profile", "external"),
                status=data.get("status", "imported"),
                limitations=_current_limitations(data),
                source=data.get("source", "osm-import"),
                scenario_path=data.get("scenario_path", str(path.parent)),
            )
        )
    return scenarios


def _run_netconvert(osm_path: Path, net_path: Path, tls_nodes: list[str] | None = None) -> dict:
    from .sumo import detect_sumo_tools

    tools = detect_sumo_tools()
    netconvert = tools.get("netconvert", {})
    if not netconvert.get("available"):
        return {
            "attempted": False,
            "ok": False,
            "reason": "netconvert is not available. Scenario was cataloged from OSM source only.",
            "tools": tools,
        }
    try:
        command = [
            netconvert["path"],
            "--osm-files",
            str(osm_path),
            "--output-file",
            str(net_path),
            "--tls.guess",
            "true",
            "--remove-edges.isolated",
            "true",
        ]
        if tls_nodes:
            command.extend(["--tls.set", ",".join(tls_nodes)])
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=90,
        )
    except Exception as error:
        return {
            "attempted": True,
            "ok": False,
            "reason": f"netconvert failed to start: {error}",
            "tools": tools,
        }
    if result.returncode != 0:
        return {
            "attempted": True,
            "ok": False,
            "reason": "netconvert returned a non-zero exit code.",
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
            "tools": tools,
        }
    return {
        "attempted": True,
        "ok": True,
        "returncode": result.returncode,
        "net_path": str(net_path),
        "stdout": result.stdout[-2000:],
        "stderr": result.stderr[-2000:],
        "tools": tools,
    }


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "osm-scenario"


def _current_limitations(data: dict) -> list[str]:
    if data.get("status") == "ready" and data.get("network") == "osm-netconvert":
        return [
            "Ready for SUMO route generation, smoke runs, SUMO-GUI launch, and imported-network TraCI controllers.",
            "Demand is generated synthetically with SUMO randomTrips unless calibrated demand is provided.",
        ]
    return data.get("limitations", [])


def _strip_namespace(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _resolve_source_path(source_path: str) -> Path:
    raw = Path(source_path).expanduser()
    if raw.is_absolute():
        return raw.resolve()
    repo_candidate = (REPO_ROOT / raw).resolve()
    if repo_candidate.exists():
        return repo_candidate
    cwd_candidate = raw.resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return repo_candidate


def _nominatim_search(query: str) -> dict:
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": query, "format": "jsonv2", "limit": "1"}
    )
    request = urllib.request.Request(url, headers={"User-Agent": "MARL-TrafficOpt/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            places = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        return {"ok": False, "error": f"Location search failed: {error}"}
    if not places:
        return {"ok": False, "error": f"No OSM location found for '{query}'."}
    return {"ok": True, "place": places[0]}


def _download_overpass_highways(south: float, west: float, north: float, east: float) -> dict:
    query = f"""
[out:xml][timeout:30];
(
  way["highway"]({south},{west},{north},{east});
  node(w);
);
out body;
>;
out skel qt;
"""
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    request = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=data,
        headers={"User-Agent": "MARL-TrafficOpt/0.1"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            xml = response.read().decode("utf-8")
    except Exception as error:
        return {"ok": False, "error": f"Overpass OSM download failed: {error}"}
    if "<way" not in xml or "<node" not in xml:
        return {"ok": False, "error": "Overpass returned no drivable OSM ways for this bounding box."}
    return {"ok": True, "xml": xml}
