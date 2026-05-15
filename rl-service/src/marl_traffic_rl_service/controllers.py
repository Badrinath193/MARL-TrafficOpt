from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ControllerSpec:
    name: str
    display_name: str
    description: str
    execution_mode: str
    parameters: dict


CONTROLLERS: dict[str, ControllerSpec] = {
    "fixed_time": ControllerSpec(
        name="fixed_time",
        display_name="Fixed-Time",
        description="Static phase cycle used as the minimum baseline.",
        execution_mode="traci_controlled",
        parameters={"cycle_s": 60, "green_s": 27, "yellow_s": 3},
    ),
    "actuated": ControllerSpec(
        name="actuated",
        display_name="Actuated Queue",
        description="Queue-threshold controller that extends or switches green based on observed lane queues.",
        execution_mode="traci_controlled",
        parameters={"min_green_s": 10, "max_green_s": 45, "queue_threshold": 6},
    ),
    "max_pressure": ControllerSpec(
        name="max_pressure",
        display_name="MaxPressure",
        description="Pressure-based controller using incoming minus outgoing queue pressure per candidate phase.",
        execution_mode="traci_controlled",
        parameters={"phase_selection": "argmax(incoming_queue - outgoing_queue)"},
    ),
}


def list_controllers() -> list[dict]:
    return [controller_to_dict(spec) for spec in CONTROLLERS.values()]


def get_controller(name: str) -> ControllerSpec:
    try:
        return CONTROLLERS[name]
    except KeyError as exc:
        allowed = ", ".join(sorted(CONTROLLERS))
        raise ValueError(f"Unknown controller '{name}'. Expected one of: {allowed}") from exc


def controller_to_dict(spec: ControllerSpec) -> dict:
    return {
        "name": spec.name,
        "display_name": spec.display_name,
        "description": spec.description,
        "execution_mode": spec.execution_mode,
        "parameters": spec.parameters,
    }
