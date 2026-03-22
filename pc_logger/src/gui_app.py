from __future__ import annotations

import csv
import ctypes
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Event
from typing import Dict, List, Optional, Tuple

import pyqtgraph as pg
import serial
from PySide6 import __file__ as PYSIDE6_FILE
from PySide6.QtCore import QCoreApplication, QStandardPaths, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QBrush, QPen
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QGraphicsDropShadowEffect,
    QGraphicsRectItem,
    QInputDialog,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from serial.tools import list_ports

from app_metadata import APP_ID, APP_NAME, APP_VERSION
from serial_protocol import OUTPUT_COLUMNS, enrich_csv_row, parse_serial_line
from stability_analyzer import (
    STABILITY_STATE_STABLE,
    STABILITY_STATE_UNKNOWN,
    STABILITY_STATE_UNSTABLE,
    StabilityConfig,
    StabilitySnapshot,
    analyze_gas_stability,
)


WINDOWS_ES_CONTINUOUS = 0x80000000
WINDOWS_ES_SYSTEM_REQUIRED = 0x00000001
WINDOWS_ES_DISPLAY_REQUIRED = 0x00000002
SPAN_OPTIONS: List[Tuple[str, Optional[float]]] = [
    ("10 min", 10 * 60.0),
    ("30 min", 30 * 60.0),
    ("1 hour", 60 * 60.0),
    ("5 hours", 5 * 60 * 60.0),
    ("All", None),
]
MAX_PLOT_POINTS_SHORT = 1800
MAX_PLOT_POINTS_MEDIUM = 1200
MAX_PLOT_POINTS_LONG = 800
CSV_FLUSH_INTERVAL_SECONDS = 5.0
CSV_FLUSH_ROW_THRESHOLD = 25
CSV_FLUSH_TIMER_INTERVAL_MS = 250
PLOT_REFRESH_INTERVAL_MS = 150
PLOT_RETENTION_SECONDS = 7 * 60 * 60.0
EVENT_LOG_MAX_LINES = 1000
TIME_AXIS_MODES: List[Tuple[str, str]] = [
    ("Relative", "relative"),
    ("Clock", "clock"),
]
PROFILE_PRESETS_FILENAME = "heater_profile_presets.json"
STABILITY_SETTINGS_FILENAME = "stability_settings.json"


def configure_qt_runtime() -> None:
    pyside_dir = Path(PYSIDE6_FILE).resolve().parent
    plugin_candidates = [
        pyside_dir / "plugins",
        pyside_dir / "Qt" / "plugins",
    ]
    qt_lib_candidates = [
        pyside_dir / "Qt" / "lib",
        pyside_dir / "lib",
        pyside_dir,
    ]

    plugins_dir = next((path for path in plugin_candidates if path.is_dir()), plugin_candidates[-1])
    platform_plugins_dir = plugins_dir / "platforms"
    qt_lib_dir = next((path for path in qt_lib_candidates if path.is_dir()), qt_lib_candidates[-1])

    if not os.environ.get("QT_PLUGIN_PATH"):
        os.environ["QT_PLUGIN_PATH"] = str(plugins_dir)
    if not os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH"):
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platform_plugins_dir)
    if not os.environ.get("DYLD_FRAMEWORK_PATH"):
        os.environ["DYLD_FRAMEWORK_PATH"] = str(qt_lib_dir)
    if not os.environ.get("DYLD_LIBRARY_PATH"):
        os.environ["DYLD_LIBRARY_PATH"] = str(qt_lib_dir)

    QCoreApplication.setLibraryPaths([str(plugins_dir)])


@dataclass
class SegmentState:
    segment_id: str
    label: str
    target_ppm: str
    start_iso: str
    start_elapsed: float
    end_iso: str = ""
    end_elapsed: Optional[float] = None


class TimeAxisItem(pg.AxisItem):
    def __init__(self, orientation: str = "bottom") -> None:
        super().__init__(orientation=orientation)
        self.mode = "relative"
        self.latest_elapsed = 0.0
        self.session_start_epoch: Optional[float] = None

    def set_mode(self, mode: str) -> None:
        self.mode = mode

    def set_reference(self, latest_elapsed: float, session_start_epoch: Optional[float]) -> None:
        self.latest_elapsed = latest_elapsed
        self.session_start_epoch = session_start_epoch

    def tickStrings(self, values, scale, spacing):  # type: ignore[override]
        labels = []
        for value in values:
            if self.mode == "clock":
                if self.session_start_epoch is None:
                    labels.append("")
                else:
                    labels.append(datetime.fromtimestamp(self.session_start_epoch + value).strftime("%H:%M:%S"))
                continue

            delta = value - self.latest_elapsed
            sign = "-" if delta < 0 else ""
            total_seconds = max(0, int(round(abs(delta))))
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            labels.append(f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}")
        return labels


class SerialWorker(QThread):
    line_received = Signal(str)
    connection_changed = Signal(bool, str)
    error_occurred = Signal(str)

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 0.5):
        super().__init__()
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._stop_requested = Event()
        self._serial: Optional[serial.Serial] = None

    def run(self) -> None:
        try:
            self._serial = serial.Serial(self._port, self._baudrate, timeout=self._timeout, write_timeout=self._timeout)
            self.connection_changed.emit(True, self._port)
            while not self._stop_requested.is_set() and self._serial:
                line_bytes = self._serial.readline()
                if self._stop_requested.is_set():
                    break
                if not line_bytes:
                    continue
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if line:
                    self.line_received.emit(line)
        except serial.SerialException as exc:
            self.error_occurred.emit(str(exc))
        finally:
            if self._serial:
                try:
                    self._serial.close()
                except serial.SerialException:
                    pass
            self.connection_changed.emit(False, self._port)

    def stop(self) -> None:
        self._stop_requested.set()
        if not self._serial or not self._serial.is_open:
            return
        try:
            self._serial.cancel_read()
        except (AttributeError, serial.SerialException):
            pass

    def send_command(self, command: str) -> None:
        if self._stop_requested.is_set() or not self._serial or not self._serial.is_open:
            return
        self._serial.write((command.strip() + "\n").encode("utf-8"))
        self._serial.flush()


class ProfileDialog(QDialog):
    MAX_PROFILE_STEPS = 10

    def __init__(self, parent: QWidget, current_profile: Dict[str, str]):
        super().__init__(parent)
        self.setWindowTitle("Profile Settings")

        self.base_edit = QLineEdit(current_profile.get("heater_profile_time_base_ms", "140"))
        self.step_temp_edits: List[QLineEdit] = []
        self.step_duration_edits: List[QLineEdit] = []
        self._profile_values: Dict[str, str] = {}

        temp_values = self._split_profile_values(
            current_profile.get("heater_profile_temp_c", "320,100,100,100,200,200,200,320,320,320")
        )
        duration_values = self._split_profile_values(
            current_profile.get("heater_profile_duration_mult", "5,2,10,30,5,5,5,5,5,5")
        )

        form = QFormLayout()
        form.addRow("Time Base (ms)", self.base_edit)

        step_grid = QGridLayout()
        step_grid.addWidget(QLabel("Step"), 0, 0)
        step_grid.addWidget(QLabel("Temperature (C)"), 0, 1)
        step_grid.addWidget(QLabel("Duration Mult"), 0, 2)

        for step_index in range(self.MAX_PROFILE_STEPS):
            temp_edit = QLineEdit(temp_values[step_index] if step_index < len(temp_values) else "")
            dur_edit = QLineEdit(duration_values[step_index] if step_index < len(duration_values) else "")
            temp_edit.setPlaceholderText("unused")
            dur_edit.setPlaceholderText("unused")
            self.step_temp_edits.append(temp_edit)
            self.step_duration_edits.append(dur_edit)

            step_grid.addWidget(QLabel(str(step_index + 1)), step_index + 1, 0)
            step_grid.addWidget(temp_edit, step_index + 1, 1)
            step_grid.addWidget(dur_edit, step_index + 1, 2)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(step_grid)
        layout.addWidget(buttons)

    @staticmethod
    def _split_profile_values(raw_value: str) -> List[str]:
        return [part.strip() for part in raw_value.split(",") if part.strip()]

    def _collect_profile_values(self) -> Optional[Dict[str, str]]:
        temperatures: List[str] = []
        durations: List[str] = []

        for index, (temp_edit, dur_edit) in enumerate(zip(self.step_temp_edits, self.step_duration_edits), start=1):
            temp_value = temp_edit.text().strip()
            dur_value = dur_edit.text().strip()

            if not temp_value and not dur_value:
                continue

            if not temp_value or not dur_value:
                QMessageBox.warning(
                    self,
                    "Incomplete Step",
                    f"Step {index} must have both temperature and duration, or both left blank.",
                )
                return None

            try:
                temp_int = int(temp_value)
                dur_int = int(dur_value)
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Invalid Step",
                    f"Step {index} must use integer values for temperature and duration.",
                )
                return None

            if temp_int < 0 or temp_int > 400:
                QMessageBox.warning(self, "Invalid Temperature", f"Step {index} temperature must be between 0 and 400 C.")
                return None

            if dur_int < 1 or dur_int > 255:
                QMessageBox.warning(self, "Invalid Duration", f"Step {index} duration multiplier must be between 1 and 255.")
                return None

            temperatures.append(str(temp_int))
            durations.append(str(dur_int))

        if not temperatures:
            QMessageBox.warning(self, "Empty Profile", "Enter at least one complete heater step.")
            return None

        base_value = self.base_edit.text().strip()
        try:
            base_int = int(base_value)
        except ValueError:
            QMessageBox.warning(self, "Invalid Time Base", "Time base must be an integer.")
            return None

        if base_int < 1 or base_int > 1000:
            QMessageBox.warning(self, "Invalid Time Base", "Time base must be between 1 and 1000 ms.")
            return None

        return {
            "heater_profile_temp_c": ",".join(temperatures),
            "heater_profile_duration_mult": ",".join(durations),
            "heater_profile_time_base_ms": str(base_int),
            "profile_len": str(len(temperatures)),
        }

    def accept(self) -> None:  # type: ignore[override]
        profile_values = self._collect_profile_values()
        if profile_values is None:
            return
        self._profile_values = profile_values
        super().accept()

    def profile_command(self) -> str:
        if not self._profile_values:
            profile_values = self._collect_profile_values()
            if profile_values is None:
                return ""
            self._profile_values = profile_values
        return (
            f"SET_PROFILE temp={self._profile_values['heater_profile_temp_c']} "
            f"dur={self._profile_values['heater_profile_duration_mult']} "
            f"base_ms={self._profile_values['heater_profile_time_base_ms']}"
        )

    def profile_state(self) -> Dict[str, str]:
        return dict(self._profile_values)


class StabilitySettingsDialog(QDialog):
    def __init__(self, parent: QWidget, config: StabilityConfig):
        super().__init__(parent)
        self.setWindowTitle("Stability Settings")

        self.threshold_edit = QLineEdit(f"{config.ratio_threshold * 100:.1f}")
        self.recent_window_edit = QLineEdit(str(int(config.recent_window_seconds)))
        self.history_window_edit = QLineEdit(str(int(config.history_window_seconds)))
        self.required_count_edit = QLineEdit(str(int(config.required_channel_count)))
        self._config = config

        form = QFormLayout(self)
        form.addRow("Threshold (%)", self.threshold_edit)
        form.addRow("Recent Window (s)", self.recent_window_edit)
        form.addRow("History Window (s)", self.history_window_edit)
        form.addRow("Required Stable Channels", self.required_count_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def accept(self) -> None:  # type: ignore[override]
        try:
            threshold_percent = float(self.threshold_edit.text().strip())
            recent_window_seconds = float(self.recent_window_edit.text().strip())
            history_window_seconds = float(self.history_window_edit.text().strip())
            required_channel_count = int(self.required_count_edit.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Invalid Values", "すべての項目に有効な数値を入力してください。")
            return

        if threshold_percent < 0 or threshold_percent > 100:
            QMessageBox.warning(self, "Invalid Threshold", "Threshold は 0 から 100 の範囲で入力してください。")
            return
        if recent_window_seconds <= 0:
            QMessageBox.warning(self, "Invalid Recent Window", "Recent Window は 0 より大きくしてください。")
            return
        if history_window_seconds < recent_window_seconds:
            QMessageBox.warning(self, "Invalid History Window", "History Window は Recent Window 以上にしてください。")
            return
        if required_channel_count < 1 or required_channel_count > 10:
            QMessageBox.warning(self, "Invalid Channel Count", "Required Stable Channels は 1 から 10 の範囲で入力してください。")
            return

        self._config = StabilityConfig(
            history_window_seconds=history_window_seconds,
            recent_window_seconds=recent_window_seconds,
            ratio_threshold=threshold_percent / 100.0,
            required_channel_count=required_channel_count,
        )
        super().accept()

    def config(self) -> StabilityConfig:
        return self._config


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1440, 900)

        self.worker: Optional[SerialWorker] = None
        self.is_connected = False
        self.is_recording = False
        self.current_segment: Optional[SegmentState] = None
        self.segment_counter = 0
        self.recording_path: Optional[Path] = None
        self.recording_temp_path: Optional[Path] = None
        self.csv_file = None
        self.csv_writer = None
        self.pending_csv_rows = 0
        self.last_csv_flush_at = 0.0
        self.profile_state: Dict[str, str] = {
            "heater_profile_id": "unknown",
            "heater_profile_temp_c": "",
            "heater_profile_duration_mult": "",
            "heater_profile_time_base_ms": "",
        }
        self.profile_presets: Dict[str, Dict[str, str]] = {}
        self.stability_config = self._load_stability_settings_from_disk()
        self.latest_stability_snapshot = StabilitySnapshot.empty(
            channel_count=10,
            required_channel_count=self.stability_config.required_channel_count,
        )
        self.data_buffers = {
            "environment": {
                "time": [],
                "temp": [],
                "humidity": [],
                "pressure": [],
            },
            "heater": {
                "time": [],
                "value": [],
            },
            "gas": [{"time": [], "value": []} for _ in range(10)],
        }
        self.last_plot_time_ms = None
        self.last_pong_iso = ""
        self.selected_span_seconds: Optional[float] = None
        self.selected_span_label: Optional[str] = "All"
        self.time_axis_mode = "relative"
        self.last_selected_port = ""
        self.session_start_epoch: Optional[float] = None
        self.plot_dirty = False
        self._suppress_span_reset_until = 0.0
        self.completed_segments: List[SegmentState] = []
        self.segment_band_items: List[QGraphicsRectItem] = []
        self.recording_glow_phase = 0.0

        self._build_ui()
        self._setup_plots()
        self._wire_events()
        self._load_profile_presets()
        self.refresh_ports()

        self.plot_timer = QTimer(self)
        self.plot_timer.timeout.connect(self._refresh_plots_if_dirty)
        self.plot_timer.start(PLOT_REFRESH_INTERVAL_MS)

        self.csv_flush_timer = QTimer(self)
        self.csv_flush_timer.setSingleShot(True)
        self.csv_flush_timer.timeout.connect(self._flush_csv)

        self.recording_glow_timer = QTimer(self)
        self.recording_glow_timer.timeout.connect(self._advance_recording_indicator)
        self.recording_glow_timer.setInterval(120)
        QTimer.singleShot(0, self._notify_partial_recordings)
        self._update_stability_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setSpacing(12)
        left_column = QVBoxLayout()
        left_column.setSpacing(12)
        right_column = QVBoxLayout()
        right_column.setSpacing(12)

        controls = QGroupBox("Connection and Session")
        controls.setMaximumWidth(380)
        controls_layout = QVBoxLayout(controls)

        self.port_combo = QComboBox()
        self.scan_button = QPushButton("Scan")
        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)

        self.record_button = QPushButton("Record")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.clear_plots_button = QPushButton("Clear Plots")

        self.start_segment_button = QPushButton("Start Segment")
        self.end_segment_button = QPushButton("End Segment")
        self.start_segment_button.setEnabled(False)
        self.end_segment_button.setEnabled(False)

        self.profile_button = QPushButton("Profile Settings")
        self.reset_profile_button = QPushButton("Reset Profile")
        self.save_preset_button = QPushButton("Save Preset")
        self.load_preset_button = QPushButton("Load Preset")
        self.profile_button.setEnabled(False)
        self.reset_profile_button.setEnabled(False)
        self.save_preset_button.setEnabled(False)
        self.load_preset_button.setEnabled(False)
        self.profile_preset_combo = QComboBox()
        self.profile_preset_combo.setPlaceholderText("Saved presets")

        self.label_edit = QLineEdit("air_baseline")
        self.target_ppm_edit = QLineEdit("0")
        self.operator_edit = QLineEdit("operator")
        self.stability_summary_label = QLabel("Waiting for data")
        self.stability_lamp_widgets: List[QLabel] = []
        self.stability_settings_button = QPushButton("Stability Settings")

        self.status_label = QLabel("Disconnected")
        self.profile_label = QLabel("Profile: unknown")
        self.profile_label.setWordWrap(True)

        connection_group = QGroupBox("Connection")
        connection_layout = QVBoxLayout(connection_group)
        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("Port"))
        port_row.addWidget(self.port_combo, stretch=1)
        port_row.addWidget(self.scan_button)
        connection_layout.addLayout(port_row)
        connection_buttons = QHBoxLayout()
        connection_buttons.addWidget(self.connect_button)
        connection_buttons.addWidget(self.disconnect_button)
        connection_layout.addLayout(connection_buttons)

        metadata_group = QGroupBox("Session Metadata")
        metadata_layout = QFormLayout(metadata_group)
        metadata_layout.addRow("Operator", self.operator_edit)
        metadata_layout.addRow("Segment Label", self.label_edit)
        metadata_layout.addRow("Target ppm", self.target_ppm_edit)

        self.record_group = QGroupBox("Recording")
        self.record_group.setObjectName("recordingGroup")
        record_layout = QVBoxLayout(self.record_group)
        record_buttons = QHBoxLayout()
        record_buttons.addWidget(self.record_button)
        record_buttons.addWidget(self.stop_button)
        record_layout.addLayout(record_buttons)
        segment_buttons = QHBoxLayout()
        segment_buttons.addWidget(self.start_segment_button)
        segment_buttons.addWidget(self.end_segment_button)
        record_layout.addLayout(segment_buttons)
        record_layout.addWidget(self.clear_plots_button)

        profile_group = QGroupBox("Profile")
        profile_layout = QVBoxLayout(profile_group)
        profile_buttons = QHBoxLayout()
        profile_buttons.addWidget(self.profile_button)
        profile_buttons.addWidget(self.reset_profile_button)
        profile_layout.addLayout(profile_buttons)
        preset_row = QHBoxLayout()
        preset_row.addWidget(self.profile_preset_combo, stretch=1)
        preset_row.addWidget(self.load_preset_button)
        preset_row.addWidget(self.save_preset_button)
        profile_layout.addLayout(preset_row)
        profile_layout.addWidget(self.profile_label)

        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        status_layout.addWidget(self.status_label)

        stability_group = QGroupBox("Stability")
        stability_layout = QVBoxLayout(stability_group)
        self.stability_summary_label.setWordWrap(True)
        stability_layout.addWidget(self.stability_summary_label)
        stability_grid = QGridLayout()
        for index in range(10):
            step_label = QLabel(f"S{index + 1}")
            step_label.setAlignment(Qt.AlignCenter)
            lamp = QLabel()
            lamp.setFixedSize(18, 18)
            lamp.setAlignment(Qt.AlignCenter)
            lamp.setToolTip(f"Step {index + 1}")
            self.stability_lamp_widgets.append(lamp)
            self._set_stability_lamp_style(lamp, "unused")
            row = (index // 5) * 2
            col = index % 5
            stability_grid.addWidget(step_label, row, col, alignment=Qt.AlignCenter)
            stability_grid.addWidget(lamp, row + 1, col, alignment=Qt.AlignCenter)
        stability_layout.addLayout(stability_grid)
        stability_layout.addWidget(self.stability_settings_button)

        controls_layout.addWidget(connection_group)
        controls_layout.addWidget(metadata_group)
        controls_layout.addWidget(self.record_group)
        controls_layout.addWidget(profile_group)
        controls_layout.addWidget(status_group)
        controls_layout.addWidget(stability_group)

        left_column.addWidget(controls, stretch=0)

        span_group = QGroupBox("Plot Span")
        span_layout = QHBoxLayout(span_group)
        self.span_buttons: Dict[str, QPushButton] = {}
        for label, seconds in SPAN_OPTIONS:
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(lambda checked, value=seconds, text=label: self.set_plot_span(text, value, checked))
            span_layout.addWidget(button)
            self.span_buttons[label] = button
        self.span_buttons["All"].setChecked(True)
        right_column.addWidget(span_group, stretch=0)

        axis_group = QGroupBox("Time Axis")
        axis_layout = QHBoxLayout(axis_group)
        self.time_axis_buttons: Dict[str, QPushButton] = {}
        for label, mode in TIME_AXIS_MODES:
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(lambda checked, value=mode, text=label: self.set_time_axis_mode(text, value, checked))
            axis_layout.addWidget(button)
            self.time_axis_buttons[mode] = button
        self.time_axis_buttons["relative"].setChecked(True)
        right_column.addWidget(axis_group, stretch=0)

        splitter = QSplitter(Qt.Vertical)
        self.environment_axis = TimeAxisItem("bottom")
        self.sensor_axis = TimeAxisItem("bottom")
        self.environment_plot = pg.PlotWidget(title="Environment", axisItems={"bottom": self.environment_axis})
        self.sensor_plot = pg.PlotWidget(title="Gas Resistance and Heater Profile", axisItems={"bottom": self.sensor_axis})
        self.sensor_plot.setXLink(self.environment_plot)
        splitter.addWidget(self.environment_plot)
        splitter.addWidget(self.sensor_plot)
        splitter.setSizes([400, 400])
        right_column.addWidget(splitter, stretch=1)

        log_group = QGroupBox("Event Log")
        log_group.setMaximumWidth(380)
        log_layout = QVBoxLayout(log_group)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.document().setMaximumBlockCount(EVENT_LOG_MAX_LINES)
        log_layout.addWidget(self.log_view)
        left_column.addWidget(log_group, stretch=1)
        root.addLayout(left_column, stretch=1)
        root.addLayout(right_column, stretch=4)

        self.setCentralWidget(central)

    def _setup_plots(self) -> None:
        pg.setConfigOptions(antialias=False)

        self.environment_plot.showGrid(x=True, y=True, alpha=0.3)
        self.sensor_plot.showGrid(x=True, y=True, alpha=0.3)

        self.environment_plot.addLegend()
        self.sensor_plot.addLegend(offset=(10, 10))
        self._update_time_axis_labels()

        self.temperature_curve = self.environment_plot.plot(pen=pg.mkPen("#b43f3f", width=2), name="Temp C")
        self.humidity_curve = self.environment_plot.plot(pen=pg.mkPen("#3f7fb4", width=2), name="Humidity %")

        env_plot_item = self.environment_plot.getPlotItem()
        self.environment_pressure_view = pg.ViewBox()
        env_plot_item.showAxis("right")
        env_plot_item.scene().addItem(self.environment_pressure_view)
        env_plot_item.getAxis("right").linkToView(self.environment_pressure_view)
        self.environment_pressure_view.setXLink(env_plot_item)
        env_plot_item.getAxis("right").setLabel("Pressure hPa")
        self.pressure_curve = pg.PlotDataItem(pen=pg.mkPen("#2f8f2f", width=2))
        self.environment_pressure_view.addItem(self.pressure_curve)
        if env_plot_item.legend is not None:
            env_plot_item.legend.addItem(self.pressure_curve, "Pressure hPa")
        env_plot_item.vb.sigResized.connect(self._sync_environment_axes)
        env_plot_item.vb.sigXRangeChanged.connect(self._handle_plot_x_range_changed)

        self.gas_curves = []
        colors = [
            "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6",
            "#ec4899", "#14b8a6", "#f97316", "#64748b", "#84cc16",
        ]
        for index, color in enumerate(colors):
            curve = self.sensor_plot.plot(pen=pg.mkPen(color, width=1.5), name=f"Gas {index}")
            curve.setClipToView(True)
            curve.setDownsampling(auto=True, method="peak")
            curve.setSkipFiniteCheck(True)
            self.gas_curves.append(curve)

        sensor_plot_item = self.sensor_plot.getPlotItem()
        self.sensor_heater_view = pg.ViewBox()
        sensor_plot_item.showAxis("right")
        sensor_plot_item.scene().addItem(self.sensor_heater_view)
        sensor_plot_item.getAxis("right").linkToView(self.sensor_heater_view)
        self.sensor_heater_view.setXLink(sensor_plot_item)
        sensor_plot_item.getAxis("right").setLabel("Heater C")
        sensor_plot_item.getAxis("right").setTextPen(pg.mkPen("#d33682"))
        self.heater_curve = pg.PlotDataItem(pen=pg.mkPen("#d33682", width=3))
        self.sensor_heater_view.addItem(self.heater_curve)
        if sensor_plot_item.legend is not None:
            sensor_plot_item.legend.addItem(self.heater_curve, "Heater C")
        sensor_plot_item.vb.sigResized.connect(self._sync_sensor_axes)
        sensor_plot_item.vb.sigXRangeChanged.connect(self._handle_plot_x_range_changed)
        sensor_plot_item.vb.sigYRangeChanged.connect(self._handle_sensor_y_range_changed)

        for curve in (self.temperature_curve, self.humidity_curve, self.pressure_curve, self.heater_curve):
            curve.setClipToView(True)
            curve.setDownsampling(auto=True, method="peak")
            curve.setSkipFiniteCheck(True)

    def _wire_events(self) -> None:
        self.scan_button.clicked.connect(self.refresh_ports)
        self.connect_button.clicked.connect(self.connect_serial)
        self.disconnect_button.clicked.connect(self.disconnect_serial)
        self.record_button.clicked.connect(self.start_recording)
        self.stop_button.clicked.connect(self.request_stop_recording)
        self.start_segment_button.clicked.connect(self.start_segment)
        self.end_segment_button.clicked.connect(self.end_segment)
        self.profile_button.clicked.connect(self.open_profile_dialog)
        self.reset_profile_button.clicked.connect(self.reset_profile)
        self.save_preset_button.clicked.connect(self.save_current_profile_as_preset)
        self.load_preset_button.clicked.connect(self.load_selected_profile_preset)
        self.stability_settings_button.clicked.connect(self.open_stability_settings)
        self.clear_plots_button.clicked.connect(self.clear_plots)

    def set_plot_span(self, label: str, seconds: Optional[float], checked: bool) -> None:
        if not checked:
            self.span_buttons[label].setChecked(True)
            return

        for other_label, button in self.span_buttons.items():
            button.setChecked(other_label == label)

        self.selected_span_label = label
        self.selected_span_seconds = seconds
        self.log(f"Plot span set to {label}")
        self._suppress_span_reset_until = time.monotonic() + 0.25
        self._apply_plot_span()
        self.refresh_plots()

    def set_time_axis_mode(self, label: str, mode: str, checked: bool) -> None:
        if not checked:
            self.time_axis_buttons[mode].setChecked(True)
            return

        for other_mode, button in self.time_axis_buttons.items():
            button.setChecked(other_mode == mode)

        self.time_axis_mode = mode
        self.environment_axis.set_mode(mode)
        self.sensor_axis.set_mode(mode)
        self._update_time_axis_labels()
        self.log(f"Time axis set to {label}")
        self.refresh_plots()

    def _sync_environment_axes(self) -> None:
        env_plot_item = self.environment_plot.getPlotItem()
        self.environment_pressure_view.setGeometry(env_plot_item.vb.sceneBoundingRect())
        self.environment_pressure_view.linkedViewChanged(env_plot_item.vb, self.environment_pressure_view.XAxis)

    def _sync_sensor_axes(self) -> None:
        sensor_plot_item = self.sensor_plot.getPlotItem()
        self.sensor_heater_view.setGeometry(sensor_plot_item.vb.sceneBoundingRect())
        self.sensor_heater_view.linkedViewChanged(sensor_plot_item.vb, self.sensor_heater_view.XAxis)

    def _current_plot_center(self) -> Optional[float]:
        environment = self.data_buffers["environment"]
        if not environment["time"]:
            return None

        x_range = self.environment_plot.getPlotItem().vb.viewRange()[0]
        if x_range and len(x_range) == 2:
            return (x_range[0] + x_range[1]) / 2.0

        return environment["time"][-1] / 2.0

    def _apply_plot_span(self) -> None:
        environment = self.data_buffers["environment"]
        if not environment["time"]:
            return

        if self.selected_span_seconds is None:
            self.environment_plot.enableAutoRange(axis="x", enable=True)
            self.sensor_plot.enableAutoRange(axis="x", enable=True)
            return

        center = self._current_plot_center()
        if center is None:
            return

        half_span = self.selected_span_seconds / 2.0
        x_min = center - half_span
        x_max = center + half_span
        self.environment_plot.enableAutoRange(axis="x", enable=False)
        self.sensor_plot.enableAutoRange(axis="x", enable=False)
        self.environment_plot.setXRange(x_min, x_max, padding=0)
        self.sensor_plot.setXRange(x_min, x_max, padding=0)

    def _update_time_axis_labels(self) -> None:
        if self.time_axis_mode == "clock":
            label = "Local Time"
        else:
            label = "Time From Latest (HH:MM:SS)"
        self.environment_plot.getPlotItem().setLabel("bottom", label)
        self.sensor_plot.getPlotItem().setLabel("bottom", label)

    def _invalidate_time_axes(self) -> None:
        for axis in (self.environment_axis, self.sensor_axis):
            axis.picture = None
            axis.update()

    def _handle_plot_x_range_changed(self, *_args) -> None:
        if time.monotonic() >= self._suppress_span_reset_until and self.selected_span_label is not None:
            for button in self.span_buttons.values():
                button.setChecked(False)
            self.selected_span_label = None
            self.selected_span_seconds = None
        self._invalidate_time_axes()

    def _handle_sensor_y_range_changed(self, *_args) -> None:
        self._update_segment_bands()

    def _refresh_plots_if_dirty(self) -> None:
        if not self.plot_dirty:
            return
        self.refresh_plots()
        self.plot_dirty = False

    def clear_plots(self) -> None:
        self.data_buffers = {
            "environment": {
                "time": [],
                "temp": [],
                "humidity": [],
                "pressure": [],
            },
            "heater": {
                "time": [],
                "value": [],
            },
            "gas": [{"time": [], "value": []} for _ in range(10)],
        }
        self.last_plot_time_ms = None
        self.session_start_epoch = None
        self.plot_dirty = False
        self.completed_segments = []
        self._clear_segment_bands()
        self.latest_stability_snapshot = StabilitySnapshot.empty(
            channel_count=10,
            required_channel_count=self.stability_config.required_channel_count,
        )

        self.temperature_curve.setData([], [])
        self.humidity_curve.setData([], [])
        self.pressure_curve.setData([], [])
        for curve in self.gas_curves:
            curve.setData([], [])
        self.heater_curve.setData([], [])

        self.environment_plot.enableAutoRange(axis="xy", enable=True)
        self.sensor_plot.enableAutoRange(axis="xy", enable=True)
        self.environment_pressure_view.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)
        self.sensor_heater_view.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)
        self.environment_axis.set_reference(0.0, None)
        self.sensor_axis.set_reference(0.0, None)
        self._invalidate_time_axes()
        self._update_stability_ui()
        self.log("Plot traces cleared")

    def _latest_elapsed(self) -> float:
        environment = self.data_buffers["environment"]
        if environment["time"]:
            return float(environment["time"][-1])
        return 0.0

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{timestamp}] {message}")

    @staticmethod
    def _port_priority(port_info) -> Tuple[int, int, str]:
        device = (port_info.device or "").lower()
        description = (port_info.description or "").lower()
        manufacturer = (port_info.manufacturer or "").lower()
        hwid = (port_info.hwid or "").lower()

        score = 0
        keywords = [
            "m5",
            "stamp",
            "esp32",
            "usb jtag",
            "cp210",
            "ch340",
            "wch",
            "silicon labs",
        ]
        for keyword in keywords:
            if keyword in description or keyword in manufacturer or keyword in hwid:
                score += 20

        if "usbmodem" in device:
            score += 15
        if "cu." in device or "com" in device:
            score += 5

        return (-score, len(device), device)

    def _choose_preferred_port(self, ports_info, current: str) -> str:
        if current and any(port.device == current for port in ports_info):
            return current
        if self.last_selected_port and any(port.device == self.last_selected_port for port in ports_info):
            return self.last_selected_port
        if not ports_info:
            return ""
        best_port = sorted(ports_info, key=self._port_priority)[0]
        return best_port.device

    def refresh_ports(self) -> None:
        current = self.port_combo.currentText()
        self.port_combo.clear()
        ports_info = list(list_ports.comports())
        ports = [port.device for port in ports_info]
        self.port_combo.addItems(ports)
        preferred_port = self._choose_preferred_port(ports_info, current)
        if preferred_port:
            self.port_combo.setCurrentText(preferred_port)
            self.last_selected_port = preferred_port
            self.log(f"Selected port: {preferred_port}")
        self.log(f"Scanned ports: {', '.join(ports) if ports else 'none'}")

    def connect_serial(self) -> None:
        port = self.port_combo.currentText().strip()
        if not port:
            QMessageBox.warning(self, "No Port", "Select a serial port first.")
            return

        self.last_selected_port = port
        self.worker = SerialWorker(port)
        self.worker.line_received.connect(self.handle_serial_line)
        self.worker.connection_changed.connect(self.handle_connection_changed)
        self.worker.error_occurred.connect(self.handle_serial_error)
        self.worker.start()
        self.log(f"Connecting to {port}")

    def disconnect_serial(self) -> None:
        if self.worker:
            worker = self.worker
            self.worker = None
            worker.stop()
            if not worker.wait(1500):
                self.log("Timed out while stopping the serial worker")
                self.handle_connection_changed(False, self.port_combo.currentText())
            return
        self.handle_connection_changed(False, self.port_combo.currentText())

    def handle_connection_changed(self, connected: bool, port: str) -> None:
        self.is_connected = connected
        self.connect_button.setEnabled(not connected)
        self.scan_button.setEnabled(not connected)
        self.port_combo.setEnabled(not connected)
        self.disconnect_button.setEnabled(connected)
        self.record_button.setEnabled(connected and not self.is_recording)
        self.clear_plots_button.setEnabled(not self.is_recording)
        self.start_segment_button.setEnabled(connected and self.is_recording and self.current_segment is None)
        self.end_segment_button.setEnabled(connected and self.is_recording and self.current_segment is not None)
        self.profile_button.setEnabled(connected and not self.is_recording)
        self.reset_profile_button.setEnabled(connected and not self.is_recording)
        self.save_preset_button.setEnabled(connected and not self.is_recording)
        self.load_preset_button.setEnabled(connected and not self.is_recording and self.profile_preset_combo.count() > 0)
        self._update_status_label(port if connected else "")
        self._update_sleep_prevention_state()
        if connected and self.worker:
            self.send_command("GET_PROFILE")
            self.send_command("PING")
        self._update_stability_ui()
        self.log(f"{'Connected' if connected else 'Disconnected'} {port}")

    def handle_serial_error(self, message: str) -> None:
        self.log(f"Serial error: {message}")
        QMessageBox.critical(self, "Serial Error", message)
        self.disconnect_serial()

    def start_recording(self) -> None:
        output_dir = self._recording_directory()
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("session_%Y%m%d_%H%M%S.csv")
        self.recording_path = output_dir / timestamp
        self.recording_temp_path = self.recording_path.with_suffix(".partial.csv")
        self.csv_file = self.recording_temp_path.open("w", newline="", encoding="utf-8")
        self._write_csv_header()
        self.csv_writer = csv.DictWriter(
            self.csv_file,
            fieldnames=[*OUTPUT_COLUMNS, "segment_id", "segment_label", "segment_target_ppm", "segment_start_iso", "segment_end_iso"],
        )
        self.csv_writer.writeheader()
        self.csv_file.flush()
        self.pending_csv_rows = 0
        self.last_csv_flush_at = time.monotonic()

        self.is_recording = True
        self.record_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.clear_plots_button.setEnabled(False)
        self.start_segment_button.setEnabled(True)
        self.profile_button.setEnabled(False)
        self.save_preset_button.setEnabled(False)
        self.load_preset_button.setEnabled(False)
        self._update_sleep_prevention_state()
        self._set_recording_indicator_active(True)
        self._update_status_label(self.port_combo.currentText())
        self.log(f"Recording started: {self.recording_path}")

    def request_stop_recording(self) -> None:
        if not self.is_recording:
            return

        answer = QMessageBox.question(
            self,
            "Stop Recording",
            "現在の記録を停止しますか？\n\n記録は現在の CSV に確定保存されます。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.stop_recording()

    def stop_recording(self) -> None:
        if self.current_segment:
            self.end_segment()

        self.is_recording = False
        self.record_button.setEnabled(self.is_connected)
        self.stop_button.setEnabled(False)
        self.clear_plots_button.setEnabled(True)
        self.start_segment_button.setEnabled(False)
        self.end_segment_button.setEnabled(False)
        self.profile_button.setEnabled(self.is_connected)
        self.reset_profile_button.setEnabled(self.is_connected)
        self.save_preset_button.setEnabled(self.is_connected)
        self.load_preset_button.setEnabled(self.is_connected and self.profile_preset_combo.count() > 0)
        self._update_sleep_prevention_state()
        self._set_recording_indicator_active(False)
        self._update_status_label(self.port_combo.currentText() if self.is_connected else "")

        self._flush_csv(force=True)
        self.csv_flush_timer.stop()
        if self.csv_file:
            self.csv_file.close()
        self.csv_file = None
        self.csv_writer = None
        self.pending_csv_rows = 0
        if self.recording_temp_path and self.recording_path:
            try:
                self.recording_temp_path.replace(self.recording_path)
            except OSError as exc:
                self.log(f"Failed to finalize recording file: {exc}")
        self.recording_temp_path = None
        self.log(f"Recording stopped: {self.recording_path}")

    def start_segment(self) -> None:
        if not self.is_recording or self.current_segment is not None:
            return

        self.segment_counter += 1
        self.current_segment = SegmentState(
            segment_id=f"seg_{self.segment_counter:03d}",
            label=self.label_edit.text().strip() or "unlabeled",
            target_ppm=self.target_ppm_edit.text().strip() or "",
            start_iso=datetime.now().isoformat(timespec="seconds"),
            start_elapsed=self._latest_elapsed(),
        )
        self.start_segment_button.setEnabled(False)
        self.end_segment_button.setEnabled(True)
        self._update_segment_bands()
        self.log(
            f"Segment started: {self.current_segment.segment_id} "
            f"label={self.current_segment.label} target_ppm={self.current_segment.target_ppm}"
        )

    def end_segment(self) -> None:
        if not self.current_segment:
            return

        self.current_segment.end_iso = datetime.now().isoformat(timespec="seconds")
        self.current_segment.end_elapsed = self._latest_elapsed()
        self.log(f"Segment ended: {self.current_segment.segment_id}")
        self.completed_segments.append(self.current_segment)
        self.current_segment = None
        self.start_segment_button.setEnabled(self.is_recording)
        self.end_segment_button.setEnabled(False)
        self._update_segment_bands()

    def open_profile_dialog(self) -> None:
        dialog = ProfileDialog(self, self.profile_state)
        if dialog.exec() != QDialog.Accepted:
            return

        self.profile_state.update(dialog.profile_state())
        self.update_profile_label()
        self.send_command(dialog.profile_command())
        self.log("Profile update command sent")

    def reset_profile(self) -> None:
        self.send_command("RESET_PROFILE")
        self.log("Profile reset command sent")

    @staticmethod
    def _normalized_profile_state(profile: Dict[str, str]) -> Dict[str, str]:
        temps = profile.get("heater_profile_temp_c", "").strip()
        durations = profile.get("heater_profile_duration_mult", "").strip()
        time_base_ms = profile.get("heater_profile_time_base_ms", "").strip()
        profile_len = profile.get("profile_len", "").strip()
        if not profile_len and temps:
            profile_len = str(len([part for part in temps.split(",") if part.strip()]))
        return {
            "heater_profile_temp_c": temps,
            "heater_profile_duration_mult": durations,
            "heater_profile_time_base_ms": time_base_ms,
            "profile_len": profile_len,
        }

    @classmethod
    def _profile_state_to_command(cls, profile: Dict[str, str]) -> str:
        normalized = cls._normalized_profile_state(profile)
        return (
            f"SET_PROFILE temp={normalized['heater_profile_temp_c']} "
            f"dur={normalized['heater_profile_duration_mult']} "
            f"base_ms={normalized['heater_profile_time_base_ms']}"
        )

    def save_current_profile_as_preset(self) -> None:
        normalized = self._normalized_profile_state(self.profile_state)
        if not normalized["heater_profile_temp_c"] or not normalized["heater_profile_duration_mult"] or not normalized["heater_profile_time_base_ms"]:
            QMessageBox.warning(self, "No Profile", "保存するヒータープロファイルがまだ取得できていません。")
            return

        name, accepted = QInputDialog.getText(
            self,
            "Save Preset",
            "プリセット名を入力してください。",
            text=self.profile_preset_combo.currentText().strip(),
        )
        if not accepted:
            return

        preset_name = name.strip()
        if not preset_name:
            QMessageBox.warning(self, "Invalid Name", "プリセット名を入力してください。")
            return

        self.profile_presets[preset_name] = normalized
        self._save_profile_presets()
        self._refresh_profile_preset_combo(selected_name=preset_name)
        self.log(f"Profile preset saved: {preset_name}")

    def load_selected_profile_preset(self) -> None:
        preset_name = self.profile_preset_combo.currentText().strip()
        if not preset_name:
            QMessageBox.warning(self, "No Preset", "読み込むプリセットを選択してください。")
            return

        preset = self.profile_presets.get(preset_name)
        if not preset:
            QMessageBox.warning(self, "Missing Preset", f"プリセット '{preset_name}' が見つかりません。")
            return

        self.profile_state.update(preset)
        self.update_profile_label()
        self.send_command(self._profile_state_to_command(preset))
        self._update_stability_ui()
        self.log(f"Profile preset loaded: {preset_name}")

    def open_stability_settings(self) -> None:
        dialog = StabilitySettingsDialog(self, self.stability_config)
        if dialog.exec() != QDialog.Accepted:
            return

        self.stability_config = dialog.config()
        self._save_stability_settings()
        self.latest_stability_snapshot = analyze_gas_stability(
            self.data_buffers["gas"],
            self.stability_config,
        )
        self._update_stability_ui()
        self.log(
            "Stability settings updated: "
            f"threshold={self.stability_config.ratio_threshold * 100:.1f}% "
            f"recent={self.stability_config.recent_window_seconds:.0f}s "
            f"history={self.stability_config.history_window_seconds:.0f}s "
            f"required={self.stability_config.required_channel_count}"
        )

    def send_command(self, command: str) -> None:
        if not self.worker:
            self.log(f"Command skipped while disconnected: {command}")
            return
        self.worker.send_command(command)

    def update_profile_label(self) -> None:
        profile_id = self.profile_state.get("heater_profile_id", "unknown")
        temp = self.profile_state.get("heater_profile_temp_c", "")
        base_ms = self.profile_state.get("heater_profile_time_base_ms", "")
        self.profile_label.setText(f"Profile: {profile_id} | base_ms={base_ms} | temp={temp}")
        self._update_stability_ui()

    def _config_directory(self) -> Path:
        config_dir = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
        if config_dir:
            return Path(config_dir)
        return Path.home() / ".bme688_logger"

    def _profile_preset_path(self) -> Path:
        return self._config_directory() / PROFILE_PRESETS_FILENAME

    def _stability_settings_path(self) -> Path:
        return self._config_directory() / STABILITY_SETTINGS_FILENAME

    def _load_stability_settings_from_disk(self) -> StabilityConfig:
        settings_path = self._stability_settings_path()
        if not settings_path.exists():
            return StabilityConfig()
        try:
            raw = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return StabilityConfig()

        try:
            return StabilityConfig(
                history_window_seconds=float(raw.get("history_window_seconds", 10 * 60.0)),
                recent_window_seconds=float(raw.get("recent_window_seconds", 30.0)),
                ratio_threshold=float(raw.get("ratio_threshold", 0.05)),
                required_channel_count=int(raw.get("required_channel_count", 10)),
            )
        except (TypeError, ValueError):
            return StabilityConfig()

    def _save_stability_settings(self) -> None:
        settings_path = self._stability_settings_path()
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": "stability_settings_v1",
            "updated_at_iso": datetime.now().astimezone().isoformat(timespec="seconds"),
            "history_window_seconds": self.stability_config.history_window_seconds,
            "recent_window_seconds": self.stability_config.recent_window_seconds,
            "ratio_threshold": self.stability_config.ratio_threshold,
            "required_channel_count": self.stability_config.required_channel_count,
        }
        temp_path = settings_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(settings_path)

    def _load_profile_presets(self) -> None:
        preset_path = self._profile_preset_path()
        if not preset_path.exists():
            self._refresh_profile_preset_combo()
            return

        try:
            raw = json.loads(preset_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            self.log(f"Failed to load profile presets: {exc}")
            self._refresh_profile_preset_combo()
            return

        presets = raw.get("presets", {})
        if not isinstance(presets, dict):
            self._refresh_profile_preset_combo()
            return

        loaded: Dict[str, Dict[str, str]] = {}
        for name, preset in presets.items():
            if not isinstance(name, str) or not isinstance(preset, dict):
                continue
            loaded[name] = self._normalized_profile_state({key: str(value) for key, value in preset.items()})

        self.profile_presets = loaded
        self._refresh_profile_preset_combo()

    def _save_profile_presets(self) -> None:
        preset_path = self._profile_preset_path()
        preset_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": "heater_profile_presets_v1",
            "updated_at_iso": datetime.now().astimezone().isoformat(timespec="seconds"),
            "presets": self.profile_presets,
        }
        temp_path = preset_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(preset_path)

    def _refresh_profile_preset_combo(self, selected_name: str = "") -> None:
        current = selected_name or self.profile_preset_combo.currentText().strip()
        self.profile_preset_combo.blockSignals(True)
        self.profile_preset_combo.clear()
        names = sorted(self.profile_presets.keys(), key=str.casefold)
        self.profile_preset_combo.addItems(names)
        if current and current in self.profile_presets:
            self.profile_preset_combo.setCurrentText(current)
        self.profile_preset_combo.blockSignals(False)
        self.load_preset_button.setEnabled(self.is_connected and not self.is_recording and bool(names))

    def _handle_status_line(self, payload: Dict[str, str], raw_line: str) -> None:
        if "pong" in payload:
            self.last_pong_iso = datetime.now().isoformat(timespec="seconds")
            self.log(f"Device ping OK at {self.last_pong_iso}")
            return

        if payload.get("set_profile") == "ok":
            self.log("Profile update accepted by firmware")
            self.send_command("GET_PROFILE")
            return

        if payload.get("set_profile") == "failed":
            self.log("Profile update rejected by firmware")
            return

        if "command_error" in payload:
            self.log(f"Firmware command error: {payload['command_error']}")
            return

        if "apply_profile_error" in payload:
            self.log(f"Firmware profile apply error: {payload['apply_profile_error']}")
            return

        if "profile_validation" in payload:
            self.log(f"Firmware profile validation: {payload['profile_validation']}")
            return

        self.log(raw_line)

    def _handle_event_line(self, payload: Dict[str, str], raw_line: str) -> None:
        if "command_received" in payload:
            self.log(f"Firmware accepted command: {payload['command_received']}")
            return

        if payload.get("profile_updated") == "1":
            self.log("Firmware switched to runtime custom profile")
            return

        if payload.get("profile_reset") == "1":
            self.log("Firmware restored the default profile")
            self.send_command("GET_PROFILE")
            return

        self.log(raw_line)

    def handle_serial_line(self, line: str) -> None:
        parsed = parse_serial_line(line)
        if parsed is None:
            return

        if parsed.line_type == "profile":
            self.profile_state.update(parsed.payload)
            self.update_profile_label()
            self.log(f"Profile update: {parsed.raw_line}")
            return

        if parsed.line_type == "status":
            self._handle_status_line(parsed.payload, parsed.raw_line)
            return

        if parsed.line_type == "event":
            self._handle_event_line(parsed.payload, parsed.raw_line)
            return

        if parsed.line_type != "csv":
            return

        row = enrich_csv_row(parsed.payload, parsed.raw_line)
        self._append_plot_data(parsed.payload)
        self.plot_dirty = True
        if self.csv_writer and self.csv_file:
            segment = self.current_segment
            export_row = {
                **row,
                "segment_id": segment.segment_id if segment else "",
                "segment_label": segment.label if segment else "",
                "segment_target_ppm": segment.target_ppm if segment else "",
                "segment_start_iso": segment.start_iso if segment else "",
                "segment_end_iso": segment.end_iso if segment else "",
            }
            self.csv_writer.writerow(export_row)
            self.pending_csv_rows += 1
            self._schedule_csv_flush()

    def _append_plot_data(self, payload: Dict[str, str]) -> None:
        host_ms = float(payload["host_ms"])
        if self.last_plot_time_ms is None:
            self.last_plot_time_ms = host_ms
        elapsed_s = (host_ms - self.last_plot_time_ms) / 1000.0
        if self.session_start_epoch is None:
            self.session_start_epoch = time.time() - elapsed_s

        environment = self.data_buffers["environment"]
        environment["time"].append(elapsed_s)
        environment["temp"].append(float(payload["temp_c"]))
        environment["humidity"].append(float(payload["humidity_pct"]))
        environment["pressure"].append(float(payload["pressure_hpa"]))

        gas_index = int(payload["gas_index"])
        if 0 <= gas_index < len(self.data_buffers["gas"]):
            gas_trace = self.data_buffers["gas"][gas_index]
            gas_trace["time"].append(elapsed_s)
            gas_trace["value"].append(float(payload["gas_kohms"]))

        heater_temp = self._heater_temp_for_step(int(payload["frame_step"]))
        heater = self.data_buffers["heater"]
        heater["time"].append(elapsed_s)
        heater["value"].append(heater_temp)

        self._prune_plot_history(elapsed_s)

    def _prune_plot_history(self, latest_elapsed: float) -> None:
        cutoff = latest_elapsed - PLOT_RETENTION_SECONDS
        if cutoff <= 0:
            return

        self._prune_series_before(self.data_buffers["environment"], cutoff, ("time", "temp", "humidity", "pressure"))
        self._prune_series_before(self.data_buffers["heater"], cutoff, ("time", "value"))
        for gas_trace in self.data_buffers["gas"]:
            self._prune_series_before(gas_trace, cutoff, ("time", "value"))

    @staticmethod
    def _prune_series_before(series: Dict[str, List[float]], cutoff: float, keys: Tuple[str, ...]) -> None:
        time_values = series["time"]
        prune_count = 0
        while prune_count < len(time_values) and time_values[prune_count] < cutoff:
            prune_count += 1

        if prune_count == 0:
            return

        for key in keys:
            del series[key][:prune_count]

    def _heater_temp_for_step(self, frame_step: int) -> float:
        temp_string = self.profile_state.get("heater_profile_temp_c", "")
        if not temp_string:
            temp_string = "320,100,100,100,200,200,200,320,320,320"
        temps = [float(part.strip()) for part in temp_string.split(",") if part.strip()]
        if 1 <= frame_step <= len(temps):
            return temps[frame_step - 1]
        return float("nan")

    def _flush_csv(self, force: bool = False) -> None:
        if not self.csv_file:
            return

        now = time.monotonic()
        should_flush = force
        should_flush = should_flush or self.pending_csv_rows >= CSV_FLUSH_ROW_THRESHOLD
        should_flush = should_flush or (self.pending_csv_rows > 0 and now - self.last_csv_flush_at >= CSV_FLUSH_INTERVAL_SECONDS)

        if not should_flush:
            if self.pending_csv_rows > 0 and not self.csv_flush_timer.isActive():
                self.csv_flush_timer.start(CSV_FLUSH_TIMER_INTERVAL_MS)
            return

        self.csv_file.flush()
        self.pending_csv_rows = 0
        self.last_csv_flush_at = now

    def _schedule_csv_flush(self) -> None:
        if not self.csv_file:
            return
        if self.pending_csv_rows >= CSV_FLUSH_ROW_THRESHOLD:
            self._flush_csv(force=True)
            return
        if self.csv_file and self.pending_csv_rows > 0 and not self.csv_flush_timer.isActive():
            self.csv_flush_timer.start(CSV_FLUSH_TIMER_INTERVAL_MS)

    def refresh_plots(self) -> None:
        environment = self.data_buffers["environment"]
        if not environment["time"]:
            return

        latest_elapsed = environment["time"][-1]
        self.environment_axis.set_reference(latest_elapsed, self.session_start_epoch)
        self.sensor_axis.set_reference(latest_elapsed, self.session_start_epoch)
        self._invalidate_time_axes()

        env_x = environment["time"]
        self.temperature_curve.setData(env_x, environment["temp"])
        self.humidity_curve.setData(env_x, environment["humidity"])
        self.pressure_curve.setData(env_x, environment["pressure"])

        for idx, curve in enumerate(self.gas_curves):
            gas_trace = self.data_buffers["gas"][idx]
            curve.setData(gas_trace["time"], gas_trace["value"])

        heater = self.data_buffers["heater"]
        self.heater_curve.setData(heater["time"], heater["value"])
        self.latest_stability_snapshot = analyze_gas_stability(
            self.data_buffers["gas"],
            self.stability_config,
        )
        self._update_stability_ui()
        self._update_segment_bands()

    def _write_csv_header(self) -> None:
        assert self.csv_file is not None
        now_iso = datetime.now().astimezone().isoformat(timespec="seconds")
        lines = [
            "# file_format=h2s_benchmark_csv_v1",
            f"# exported_at_iso={now_iso}",
            f"# gui_app_name={APP_NAME}",
            f"# gui_app_version={APP_VERSION}",
            f"# operator_id={self.operator_edit.text().strip()}",
            f"# session_id={datetime.now().strftime('%Y%m%d_%H%M%S_run01')}",
            "# gui_git_commit=working_tree",
            "# board_type=M5StampS3",
            "# sensor_type=BME688",
            f"# serial_port={self.port_combo.currentText()}",
            f"# heater_profile_id={self.profile_state.get('heater_profile_id', 'unknown')}",
            f"# heater_profile_temp_c={self.profile_state.get('heater_profile_temp_c', '')}",
            f"# heater_profile_duration_mult={self.profile_state.get('heater_profile_duration_mult', '')}",
            f"# heater_profile_time_base_ms={self.profile_state.get('heater_profile_time_base_ms', '')}",
            "# label_target_gas=H2S",
            "# label_unit=ppm",
            "# label_scope=exposure_segment",
            "# notes=",
        ]
        self.csv_file.write("\n".join(lines) + "\n")

    def _set_sleep_prevention(self, active: bool) -> None:
        if sys.platform != "win32":
            return

        flags = WINDOWS_ES_CONTINUOUS
        if active:
            flags |= WINDOWS_ES_SYSTEM_REQUIRED | WINDOWS_ES_DISPLAY_REQUIRED
        ctypes.windll.kernel32.SetThreadExecutionState(flags)

    def _update_sleep_prevention_state(self) -> None:
        self._set_sleep_prevention(self.is_connected or self.is_recording)

    def _update_status_label(self, port: str) -> None:
        if not self.is_connected:
            self.status_label.setText("Disconnected")
            return

        status = f"Connected: {port}"
        if self.is_recording:
            status += " | RECORDING"
        self.status_label.setText(status)

    def _active_profile_step_count(self) -> int:
        raw_len = self.profile_state.get("profile_len", "").strip()
        if raw_len.isdigit():
            return max(0, min(10, int(raw_len)))
        temp_values = [part.strip() for part in self.profile_state.get("heater_profile_temp_c", "").split(",") if part.strip()]
        return max(0, min(10, len(temp_values)))

    def _set_stability_lamp_style(self, lamp: QLabel, state: str) -> None:
        style_map = {
            STABILITY_STATE_STABLE: ("#22c55e", "#14532d"),
            STABILITY_STATE_UNSTABLE: ("#ef4444", "#7f1d1d"),
            STABILITY_STATE_UNKNOWN: ("#a3a3a3", "#404040"),
            "unused": ("#d6d3d1", "#78716c"),
        }
        fill, border = style_map[state]
        lamp.setStyleSheet(
            f"""
            QLabel {{
                background-color: {fill};
                border: 2px solid {border};
                border-radius: 9px;
            }}
            """
        )

    def _update_stability_ui(self) -> None:
        active_steps = self._active_profile_step_count()
        channels = self.latest_stability_snapshot.channels

        stable_count = 0
        unknown_count = 0
        for index, lamp in enumerate(self.stability_lamp_widgets):
            if index >= active_steps:
                self._set_stability_lamp_style(lamp, "unused")
                lamp.setToolTip(f"Step {index + 1}: unused")
                continue

            channel = channels[index] if index < len(channels) else None
            if channel is None:
                state = STABILITY_STATE_UNKNOWN
                tooltip = f"Step {index + 1}: no data"
            else:
                state = channel.state
                tooltip = (
                    f"Step {index + 1}: {state}\n"
                    f"history_span={channel.history_span:.4f}\n"
                    f"recent_span={channel.recent_span:.4f}\n"
                    f"ratio={channel.ratio:.4f}\n"
                    f"samples={channel.sample_count}"
                )
                if state == STABILITY_STATE_STABLE:
                    stable_count += 1
                elif state == STABILITY_STATE_UNKNOWN:
                    unknown_count += 1

            self._set_stability_lamp_style(lamp, state)
            lamp.setToolTip(tooltip)

        if not self.is_connected:
            self.stability_summary_label.setText("Disconnected")
            return

        if active_steps == 0:
            self.stability_summary_label.setText("No active heater steps")
            return

        if unknown_count == active_steps:
            self.stability_summary_label.setText("Waiting for enough history")
            return

        required_count = min(self.stability_config.required_channel_count, active_steps)
        if stable_count >= required_count:
            self.stability_summary_label.setText(f"Stable {stable_count}/{active_steps}")
            return

        self.stability_summary_label.setText(f"Stabilizing {stable_count}/{active_steps}")

    def _set_recording_indicator_active(self, active: bool) -> None:
        if active:
            if not hasattr(self, "recording_glow_effect"):
                effect = QGraphicsDropShadowEffect(self.record_group)
                effect.setOffset(0, 0)
                self.recording_glow_effect = effect
                self.record_group.setGraphicsEffect(effect)
            self.recording_glow_phase = 0.0
            self.recording_glow_timer.start()
            self._apply_recording_indicator_style(0.5)
            return

        self.recording_glow_timer.stop()
        self.record_group.setStyleSheet("")
        if hasattr(self, "recording_glow_effect"):
            self.recording_glow_effect.setBlurRadius(0)
            self.recording_glow_effect.setColor(QColor(0, 0, 0, 0))

    def _advance_recording_indicator(self) -> None:
        self.recording_glow_phase += 0.28
        intensity = (math.sin(self.recording_glow_phase) + 1.0) / 2.0
        self._apply_recording_indicator_style(intensity)

    def _apply_recording_indicator_style(self, intensity: float) -> None:
        border_alpha = int(120 + intensity * 110)
        fill_alpha = int(18 + intensity * 24)
        title_alpha = int(180 + intensity * 60)
        self.record_group.setStyleSheet(
            f"""
            QGroupBox#recordingGroup {{
                border: 2px solid rgba(255, 80, 80, {border_alpha});
                border-radius: 10px;
                margin-top: 12px;
                background-color: rgba(255, 80, 80, {fill_alpha});
            }}
            QGroupBox#recordingGroup::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: rgba(255, 96, 96, {title_alpha});
                font-weight: 700;
            }}
            """
        )
        if hasattr(self, "recording_glow_effect"):
            color = QColor(255, 80, 80, int(48 + intensity * 80))
            self.recording_glow_effect.setColor(color)
            self.recording_glow_effect.setBlurRadius(20 + intensity * 20)

    def _clear_segment_bands(self) -> None:
        for item in self.segment_band_items:
            try:
                self.sensor_plot.removeItem(item)
            except Exception:
                pass
        self.segment_band_items.clear()

    def _update_segment_bands(self) -> None:
        self._clear_segment_bands()

        y_range = self.sensor_plot.getPlotItem().vb.viewRange()[1]
        if not y_range or len(y_range) != 2:
            return

        y_min, y_max = y_range
        span = y_max - y_min
        if span <= 0:
            return

        band_height = span * 0.10
        band_y = y_max - band_height
        segments = list(self.completed_segments)
        if self.current_segment is not None:
            active_segment = SegmentState(
                segment_id=self.current_segment.segment_id,
                label=self.current_segment.label,
                target_ppm=self.current_segment.target_ppm,
                start_iso=self.current_segment.start_iso,
                start_elapsed=self.current_segment.start_elapsed,
                end_iso=self.current_segment.end_iso,
                end_elapsed=self._latest_elapsed(),
            )
            segments.append(active_segment)

        if not segments:
            return

        palette = [
            QColor(239, 68, 68, 55),
            QColor(245, 158, 11, 55),
            QColor(16, 185, 129, 55),
            QColor(59, 130, 246, 55),
            QColor(168, 85, 247, 55),
        ]

        for index, segment in enumerate(segments):
            start_x = segment.start_elapsed
            end_x = segment.end_elapsed if segment.end_elapsed is not None else self._latest_elapsed()
            width = max(0.001, end_x - start_x)
            item = QGraphicsRectItem(start_x, band_y, width, band_height)
            item.setPen(QPen(Qt.NoPen))
            item.setBrush(QBrush(palette[index % len(palette)]))
            item.setZValue(-5)
            item.setToolTip(
                f"{segment.segment_id}\nlabel={segment.label}\ntarget_ppm={segment.target_ppm or '-'}"
            )
            self.sensor_plot.addItem(item, ignoreBounds=True)
            self.segment_band_items.append(item)

    @staticmethod
    def _recording_directory() -> Path:
        return Path("data")

    def _find_partial_recordings(self) -> List[Path]:
        data_dir = self._recording_directory()
        if not data_dir.exists():
            return []
        return sorted(data_dir.glob("*.partial.csv"))

    def _notify_partial_recordings(self) -> None:
        partials = self._find_partial_recordings()
        if not partials:
            return

        preview = "\n".join(f"- {path.name}" for path in partials[:5])
        if len(partials) > 5:
            preview += f"\n- ... and {len(partials) - 5} more"

        self.log(f"Found {len(partials)} incomplete recording file(s)")
        QMessageBox.warning(
            self,
            "Recovered Partial Sessions",
            "前回の終了が正常でなかった可能性があります。未完了の記録ファイルを検出しました。\n\n"
            "これらのファイルは `data/` 配下に `.partial.csv` として残っています。\n"
            "必要に応じて内容を確認してください。\n\n"
            f"{preview}",
        )

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self.is_recording:
            message = "記録中です。記録を停止してアプリを終了しますか？"
        else:
            message = "GUI アプリを終了しますか？"

        answer = QMessageBox.question(
            self,
            "Exit Application",
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            event.ignore()
            return

        if self.is_recording:
            self.stop_recording()
        self.disconnect_serial()
        super().closeEvent(event)


def main() -> int:
    configure_qt_runtime()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_ID)
    window = create_main_window()
    window.show()
    return app.exec()


def create_main_window() -> MainWindow:
    return MainWindow()


if __name__ == "__main__":
    raise SystemExit(main())
