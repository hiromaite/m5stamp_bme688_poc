# Python Logger PoC

This directory contains a minimal Python logger PoC for the M5StampS3 BME688
parallel-mode firmware.

## Layout

- `src/serial_logger.py`: serial receiver and CSV logger
- `requirements.txt`: Python dependencies
- `data/`: default output directory for captured logs

## Setup

```bash
cd pc_logger
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
cd pc_logger
source .venv/bin/activate
python src/serial_logger.py --port /dev/cu.usbmodem4101
```

Useful options:

```bash
python src/serial_logger.py --help
```

By default the logger:

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
