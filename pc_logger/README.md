# PC Logger

This directory contains the PC-side tooling for the M5StampS3 BME688
parallel-mode workflow.

## Layout

- `src/serial_logger.py`: serial receiver and CSV logger CLI PoC
- `main.py`: packaging-friendly GUI entry point
- `src/gui_app.py`: GUI implementation
- `src/app_metadata.py`: app name and version constants
- `src/serial_protocol.py`: shared serial parsing helpers
- `pc_logger.pyproject`: Qt project description
- `pysidedeploy.spec`: Qt deployment config
- `requirements.txt`: Python dependencies
- `data/`: default output directory for captured logs

## Setup

```bash
cd pc_logger
source .venv/bin/activate
pip install -r requirements.txt
```

## Run CLI Logger

```bash
cd pc_logger
source .venv/bin/activate
python src/serial_logger.py --port /dev/cu.usbmodem4101
```

## Run GUI

```bash
cd pc_logger
source .venv/bin/activate
python main.py
```

Useful options for the CLI logger:

```bash
python src/serial_logger.py --help
```

The GUI currently provides:

- port scan and connect/disconnect
- live status view
- record/stop controls
- start/end exposure segment controls
- current heater profile display
- variable-length heater-profile editing (`1..10` steps)
- profile reset control
- live environmental plot
- live gas-resistance plus heater-temperature plot
- plot-span switching

The CLI logger by default:

- listens at `115200` baud
- captures only firmware lines that begin with `[csv]`
- writes parsed rows to `data/session_YYYYmmdd_HHMMSS.csv`
- prints a short progress line whenever a frame reaches 10 steps

## Output schema

The logger expects firmware lines in this format:

```text
[csv] frame_id,batch_id,frame_step,host_ms,field_index,gas_index,meas_index,temp_c,humidity_pct,pressure_hpa,gas_kohms,status_hex,gas_valid,heat_stable
```

The saved CSV file uses the same columns plus:

- `received_at_iso`
- `source_line`

The GUI currently understands these line families:

- `[csv] ...`
- `[profile] key=value`
- `[status] key=value`
- `[event] key=value`

## Packaging Direction

The current packaging target is Windows 11.

Primary deployment path:

- `pyside6-deploy`
- `standalone` mode first

Fallback path:

- `PyInstaller`

See [../docs/windows_build.md](../docs/windows_build.md) for the current Windows build notes.
