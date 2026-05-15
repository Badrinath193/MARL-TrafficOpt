# One Intersection SUMO Scenario

Minimal four-approach signalized intersection for Phase 2 smoke testing.

Files:

- `one_intersection.nod.xml` / `one_intersection.edg.xml` - editable source geometry.
- Runtime network - the smoke test uses SUMO's packaged `cross.net.xml` when available, or can be extended to generate from source geometry with `netconvert`.
- `one_intersection.rou.xml` - simple straight-through traffic demand.
- `one_intersection.sumocfg` - simulation config.

Purpose:

- Verify SUMO is installed.
- Verify the RL service can launch SUMO headlessly.
- Verify trip metrics can be parsed from `tripinfo.xml`.

This is not yet a benchmark scenario.
