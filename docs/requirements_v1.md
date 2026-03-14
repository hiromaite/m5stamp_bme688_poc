# H2S Benchmark System Requirements v1

## 1. Purpose

This project evaluates how well a `BME688` can function as an `H2S` sensor when
connected to an `M5StampS3`.

The system shall support:

- controlled heater-profile-based acquisition on the device side
- robust data logging on the PC side
- dataset creation for classification and regression experiments
- repeatable benchmarking of model performance under controlled conditions

This specification covers both:

- firmware running on `M5StampS3`
- PC-side logging and future GUI tooling

## 2. Current Baseline

The following milestones already exist and should be treated as baseline
references:

- `f5a6e7a`: initial `parallel-mode` firmware PoC
- `d7959e3`: Python serial logger PoC

Current firmware characteristics:

- board: `M5StampS3`
- sensor: `BME688` over I2C
- firmware library: Bosch `BME68x SensorAPI`
- active mode: `parallel mode`
- current profile: Bosch standard 10-step VSC-oriented profile
- output format: serial CSV rows with one valid data point per step

Current Python PoC characteristics:

- serial receive via `pyserial`
- raw line capture optional
- parsed CSV persistence
- simple frame summary based on `frame_id`

## 3. System Goal

The final system shall make it possible to:

1. acquire repeatable multi-step heater-response data from the BME688
2. label datasets with gas exposure conditions, especially H2S
3. store and review experiment sessions with metadata
4. train and evaluate regression and/or classification models outside the device
5. compare heater profiles, exposure conditions, and model configurations

## 4. Scope

### In Scope

- firmware for BME688 profile control and data streaming
- PC logger for capture, storage, and operator monitoring
- metadata capture needed for supervised learning
- experiment-session traceability
- support for benchmarking workflows

### Out of Scope for the Initial Product

- on-device machine learning inference
- cloud synchronization
- multi-sensor fusion beyond one BME688 unless later required
- full laboratory automation of gas exposure hardware

## 5. Assumed Workflow

1. connect M5StampS3 to PC over USB
2. connect BME688 to the M5StampS3 over I2C
3. connect the GUI to the device
4. observe live plots while firmware streams continuously
5. start recording only when the operator wants to persist data
6. start and end labeled exposure segments during the recording
7. export one CSV file for the recording interval
8. use the exported file for offline benchmarking and model development

## 6. Firmware Requirements

### 6.1 Mandatory Requirements

- The firmware shall run on `M5StampS3`.
- The firmware shall communicate with the BME688 over I2C.
- The firmware shall use Bosch `BME68x SensorAPI`.
- The firmware shall support `parallel mode`.
- The firmware shall support a 10-step heater profile.
- The firmware shall output machine-readable serial data continuously after boot.
- The firmware shall identify valid measurement rows only.
- The firmware shall expose step/order information including:
  - `frame_id`
  - `frame_step`
  - `gas_index`
  - `meas_index`
- The firmware shall output at least:
  - temperature
  - humidity
  - pressure
  - gas resistance
  - validity flags
- The firmware shall provide enough information for the PC to reconstruct one
  full 10-step cycle.
- The firmware shall load a default heater profile at startup.
- The firmware shall allow the active heater profile to be updated during runtime.
- The firmware shall treat profile updates as volatile only.
- The firmware shall revert to the default heater profile after a reboot or power
  cycle.

### 6.2 Strongly Desired Requirements

- The firmware should support switching heater profiles without major rewrites.
- The firmware should support profile metadata output at boot or session start.
- The firmware should support stable long-duration operation.
- The firmware should support a future command interface from the PC.
- The firmware should support explicit session start markers.

### 6.3 Future Requirements

- selectable profile presets
- operator-defined custom heater profiles
- richer command/response control over serial
- status reporting for sensor faults and communication faults
- timestamp synchronization strategy with the PC

## 7. PC Logger / GUI Requirements

### 7.1 Mandatory Requirements

- The PC application shall receive serial data from the M5StampS3.
- The PC application shall persist parsed data to disk.
- The PC application shall preserve raw incoming lines optionally.
- The PC application shall group rows by profile cycle or equivalent session unit.
- The PC application shall detect incomplete frames.
- The PC application shall preserve capture timestamps on the PC side.
- The PC application shall associate captured rows with session metadata.
- The GUI shall save received data as log data while it is connected and active.
- The GUI shall provide `Record` and `Stop` controls.
- The GUI shall save only the data received during an active recording interval as
  the exported CSV dataset.
- The GUI shall allow the operator to choose a serial port from a scanned port list.
- The GUI shall allow the operator to start a connection to the selected port.
- The GUI shall receive the current heater profile from the firmware after
  communication is established.
- The GUI shall retain the heater profile received from the firmware and use it as
  the current profile state in the application.
- The GUI shall provide a settings modal for heater-profile editing.
- The GUI shall send heater-profile updates to the firmware.
- The GUI shall disable profile-editing actions while recording is active.
- The GUI shall support exposure-segment queueing and labeling.
- The GUI shall apply labels at the exposure-segment level during export.
- The GUI shall visualize incoming data in real time.
- The GUI shall provide two graphs:
  - temperature, pressure, humidity
  - ten sensor-resistance traces and heater-control temperature
- The GUI shall support display-span switching with simple controls for:
  - 10 minutes
  - 30 minutes
  - 1 hour
  - 5 hours
  - full session
- The GUI shall support practical graph interaction such as:
  - pan
  - zoom
  - axis-scale changes including logarithmic view where useful
- The GUI shall allow logarithmic scaling to be configured per axis.
- The GUI shall be designed with future Windows 11 executable packaging in mind.

### 7.2 Strongly Desired Requirements

- The application should provide a GUI for session control.
- The application should display current serial connection status.
- The application should show incoming data health:
  - frame completeness
  - valid/invalid counts
  - dropped or malformed lines
- The application should visualize step-wise gas response during capture.
- The application should support operator notes.
- The GUI should prevent the Windows system from entering idle sleep while the
  application is actively recording, if the operating system permits it.
- The GUI should support decimation or thinning for long-duration plotting.

### 7.3 Future Requirements

- profile selection from GUI
- live plotting enhancements
- experiment templates
- dataset browser
- training-run linkage and benchmark result review

## 8. Data Requirements

### 8.1 Per-Row Sensor Data

The current expected sensor record contains:

- `frame_id`
- `batch_id`
- `frame_step`
- `host_ms`
- `field_index`
- `gas_index`
- `meas_index`
- `temp_c`
- `humidity_pct`
- `pressure_hpa`
- `gas_kohms`
- `status_hex`
- `gas_valid`
- `heat_stable`
- PC receive timestamp

### 8.2 Session Metadata

The system shall be able to store:

- session identifier
- operator name or ID
- datetime started/stopped
- firmware commit or version
- heater profile ID and full profile contents
- sensor ID or hardware identifier
- board ID or serial port
- exposure label
- target gas type
- target concentration
- unit of concentration
- exposure start/end timing
- ambient conditions if available
- notes

Session metadata shall be stored in the CSV header.

### 8.3 Dataset-Level Metadata

- train/validation/test split policy
- label source and confidence
- calibration context
- experiment protocol version

## 9. Benchmarking Requirements

The system shall support at least two analysis modes:

- classification
  - examples: H2S present/absent, gas class discrimination
- regression
  - example: H2S concentration estimation

The recorded data shall be sufficient to derive features from:

- individual step gas resistance values
- temporal profile shape
- derived ratios or deltas between steps
- temperature/humidity/pressure context

The initial benchmark direction is:

- classification-first workflow
- with LoD-oriented evaluation as the practical objective
- while keeping concentration-regression support in scope from the beginning

The LoD definition basis is:

- use air-measurement output as baseline
- use `3 sigma` of the air-output distribution as the threshold basis
- evaluate at the exposure-segment level

The recommended initial concentration ladder is:

- `0 ppm`
- `0.25 ppm`
- `0.5 ppm`
- `1 ppm`
- `2 ppm`
- `5 ppm`
- `10 ppm`

The recommended initial success metrics are:

- classification primary:
  - balanced accuracy
  - Matthews correlation coefficient (MCC)
- classification secondary:
  - F1 score
  - AUROC
- regression:
  - MAE
  - RMSE
  - R²

The initial practical LoD decision rule is:

- determine an air-derived threshold using `mean_air + 3 sigma_air`
- evaluate at the exposure-segment level
- define the initial practical LoD as the lowest concentration rung at which:
  - at least `95%` of labeled exposure segments exceed the air-derived threshold
  - and air-vs-H2S segment classification achieves:
    - balanced accuracy `>= 0.80`
    - MCC `>= 0.60`

## 10. Recommended Architecture Direction

### Firmware

- continue using Bosch `BME68x SensorAPI`
- keep serial CSV as the default streaming transport
- extend with simple text command handling for profile control

### PC Application

Recommended phased approach:

1. logger CLI PoC
2. logger core library
3. simple GUI shell
4. richer experiment-management GUI

Recommended initial technical stack:

- Python `3.9+`
- `venv`
- `pyserial`
- `PySide6`
- `pyqtgraph`

Deployment direction:

- design the GUI so that it can be packaged for Windows 11
- prefer `pyside6-deploy` compatible project structure from the beginning
- keep `PyInstaller` as a fallback option if needed for tooling reasons

Windows power-management direction:

- use the Win32 `SetThreadExecutionState` API as best-effort sleep suppression
  during active recording

## 11. Approved Design Decisions

- Heater-control main path: `parallel mode`
- Sensor API main path: Bosch `BME68x SensorAPI`
- Initial profile: Bosch standard 10-step profile
- PC-side development inside this repository: yes
- Python environment isolation with local `venv`: yes
- Initial benchmark direction: classification-first with LoD-oriented evaluation
- Label granularity: exposure-segment based labeling
- Initial GUI scope: minimal GUI with staged expansion
- Initial export format: CSV only
- Metadata placement: CSV header
- Firmware behavior: continuous streaming after boot
- Profile behavior:
  - one default profile loaded on boot
  - GUI-driven profile update supported
  - updated profile is temporary and does not survive a power cycle
- Plotting behavior:
  - ten resistance traces are always overlaid
  - heater temperature uses a secondary axis
  - temperature and humidity share one axis
  - pressure uses a separate axis
  - logarithmic scaling is configurable per axis
  - long-session plot decimation is desirable

## 12. Approved GUI Operation Flow

Recommended and approved interaction flow:

1. `Scan` serial ports
2. `Connect` to the selected port
3. receive the active profile from firmware
4. update live plots continuously
5. prepare or queue the next exposure-segment label
6. press `Record` to begin data persistence
7. press `Start Segment` to begin the labeled exposure segment
8. press `End Segment` to close the labeled exposure segment
9. press `Stop` to stop recording and finalize CSV export

This separates:

- continuous observation
- explicit recording
- explicit exposure labeling

## 13. Approved Serial Protocol Direction

### 13.1 Device to PC

The firmware shall continuously output text lines.

Line families:

- `[csv] ...`
- `[profile] key=value`
- `[status] key=value`
- `[event] key=value`

### 13.2 PC to Device

The GUI shall send one command per line.

Initial command set:

- `GET_PROFILE`
- `SET_PROFILE temp=... dur=... base_ms=...`
- `RESET_PROFILE`
- `PING`

### 13.3 Protocol Rules

- CSV streaming remains active by default.
- Profile update commands are not sent while recording is active.
- Firmware responds to control commands with short `[event]`, `[status]`, or
  `[profile]` lines.

## 14. Approved CSV Metadata Header Format

The CSV file shall use:

- comment-prefixed metadata lines beginning with `# `
- `key=value` syntax for metadata
- a normal CSV table header at the first non-comment line

Recommended file structure:

```text
# file_format=h2s_benchmark_csv_v1
# exported_at_iso=2026-03-14T13:30:00+09:00
# operator_id=hiromasa
# session_id=20260314_133000_run01
# recording_id=rec_001
# firmware_git_commit=f5a6e7a
# gui_git_commit=<commit-or-dirty>
# board_type=M5StampS3
# sensor_type=BME688
# sensor_id=
# serial_port=/dev/cu.usbmodem4101
# baudrate=115200
# heater_profile_id=default_vsc_10step
# heater_profile_temp_c=320,100,100,100,200,200,200,320,320,320
# heater_profile_duration_mult=5,2,10,30,5,5,5,5,5,5
# heater_profile_time_base_ms=140
# label_target_gas=H2S
# label_unit=ppm
# label_scope=exposure_segment
# concentration_ladder_ppm=0,0.25,0.5,1,2,5,10
# lod_rule=air_mean_plus_3sigma
# notes=
frame_id,batch_id,frame_step,host_ms,field_index,gas_index,meas_index,temp_c,humidity_pct,pressure_hpa,gas_kohms,status_hex,gas_valid,heat_stable,received_at_iso,segment_id,segment_label,segment_target_ppm,segment_start_iso,segment_end_iso
...
```

Mandatory CSV metadata keys:

- `file_format`
- `exported_at_iso`
- `operator_id`
- `session_id`
- `firmware_git_commit`
- `gui_git_commit`
- `board_type`
- `sensor_type`
- `serial_port`
- `heater_profile_id`
- `heater_profile_temp_c`
- `heater_profile_duration_mult`
- `heater_profile_time_base_ms`
- `label_target_gas`
- `label_unit`
- `label_scope`

Strongly desired metadata keys:

- `recording_id`
- `sensor_id`
- `concentration_ladder_ppm`
- `lod_rule`
- `notes`

## 15. Remaining Implementation Details

The following items remain open at implementation-detail level, but do not
block this v1 specification:

- exact concentration ladder may be refined after early exposure experiments
- final acceptance thresholds may be tuned after pilot data analysis
- exact GUI widget layout details
- whether individual resistance traces can be toggled on or off
- whether plot decimation is automatic only or also user-configurable
- exact serial parsing and error-recovery behavior

