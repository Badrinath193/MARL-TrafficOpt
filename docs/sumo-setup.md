# SUMO Setup

Phase 2 requires the following commands to be available on `PATH`:

```text
sumo
netconvert
```

## Windows

1. Install SUMO from the official Eclipse SUMO distribution, or use the Python package:

```powershell
pip install eclipse-sumo
```

2. If using the Python package, add the Python user Scripts directory to `PATH`. On this machine that is:

```text
C:\Users\tshiv\AppData\Roaming\Python\Python314\Scripts
```

3. Set `SUMO_HOME` to the installed package directory. On this machine that is:

```text
C:\Users\tshiv\AppData\Roaming\Python\Python314\site-packages\sumo
```

Alternative manual installer steps:

1. Install SUMO from the official Eclipse SUMO distribution.
2. Add the SUMO `bin` directory to `PATH`.
3. Open a new terminal.
4. Verify:

```powershell
where.exe sumo
where.exe netconvert
sumo --version
netconvert --version
```

## Smoke Test

Start the RL service:

```powershell
cd rl-service
python -m marl_traffic_rl_service
```

Run:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/sumo/detect
Invoke-RestMethod -Uri http://127.0.0.1:8000/simulations/run-smoke-test -Method Post
```

If SUMO is missing, the smoke test returns `skipped: true`. If SUMO is installed, it generates the one-intersection network, runs SUMO headlessly, and returns trip metrics.

## Note on `netconvert`

Some Windows Application Control policies may block `netconvert.exe` even when `sumo.exe` works. The Phase 2 smoke test handles this by using SUMO's packaged `cross.net.xml` as the runtime network when available.
