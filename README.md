# M5StampS3 BME688 H2S Benchmark

This repository contains an `M5StampS3` firmware project and a PC-side Python
application for collecting `BME688` heater-profile data for `H2S`
benchmarking.

## Components

- `src/main.cpp`
  - firmware for `M5StampS3`
  - Bosch `BME68x SensorAPI`
  - `parallel mode`
  - runtime heater-profile control over serial
- `pc_logger/`
  - Python GUI and CLI logger
  - live plotting
  - recording and exposure-segment labeling
  - heater-profile editing from the GUI
- `docs/requirements_v1.md`
  - approved system requirements baseline

## Current Baseline

The current `main` branch includes:

- variable-length heater profiles (`1..10` steps)
- a GUI with live plots and plot-span switching
- profile editing and reset controls
- CSV recording with metadata headers

## Firmware

Build:

```bash
~/.platformio/penv/bin/pio run -e m5stack-stamps3
```

Upload:

```bash
~/.platformio/penv/bin/pio run -e m5stack-stamps3 -t upload --upload-port /dev/cu.usbmodem4101
```

## PC Logger

See [pc_logger/README.md](pc_logger/README.md).

## Windows Packaging

Packaging preparation is tracked in this repository. The current Windows build
notes live in [docs/windows_build.md](docs/windows_build.md).
