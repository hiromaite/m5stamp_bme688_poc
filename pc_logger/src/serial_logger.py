from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import serial

from serial_protocol import OUTPUT_COLUMNS, enrich_csv_row, parse_serial_line


@dataclass
class LoggerConfig:
    port: str
    baudrate: int
    output: Path
    raw_log: Optional[Path]
    timeout: float


def parse_args() -> LoggerConfig:
    parser = argparse.ArgumentParser(
        description="Minimal serial logger for the M5StampS3 BME688 parallel-mode PoC."
    )
    parser.add_argument("--port", required=True, help="Serial port, for example /dev/cu.usbmodem4101")
    parser.add_argument("--baudrate", type=int, default=115200, help="Serial baud rate")
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output_path(),
        help="Parsed CSV destination",
    )
    parser.add_argument(
        "--raw-log",
        type=Path,
        default=None,
        help="Optional raw text log destination",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=1.0,
        help="Serial read timeout in seconds",
    )
    args = parser.parse_args()
    return LoggerConfig(
        port=args.port,
        baudrate=args.baudrate,
        output=args.output,
        raw_log=args.raw_log,
        timeout=args.timeout,
    )


def default_output_path() -> Path:
    from datetime import datetime

    timestamp = datetime.now().strftime("session_%Y%m%d_%H%M%S.csv")
    return Path("data") / timestamp


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def print_startup(config: LoggerConfig) -> None:
    print("Starting serial logger")
    print(f"  port: {config.port}")
    print(f"  baudrate: {config.baudrate}")
    print(f"  parsed CSV: {config.output}")
    if config.raw_log:
        print(f"  raw log: {config.raw_log}")


def summarize_frame(frame_id: str, rows: List[Dict[str, str]]) -> None:
    steps = [row["frame_step"] for row in rows]
    gas_indices = [row["gas_index"] for row in rows]
    print(
        f"frame {frame_id}: rows={len(rows)} "
        f"steps={steps[0]}..{steps[-1]} gas_index={gas_indices[0]}..{gas_indices[-1]}"
    )


def run_logger(config: LoggerConfig) -> None:
    ensure_parent(config.output)
    if config.raw_log:
        ensure_parent(config.raw_log)

    frame_rows: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    with serial.Serial(config.port, config.baudrate, timeout=config.timeout) as ser, \
        config.output.open("w", newline="", encoding="utf-8") as csv_file:
        raw_file = None
        try:
            if config.raw_log:
                raw_file = config.raw_log.open("a", encoding="utf-8")

            writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            csv_file.flush()

            print_startup(config)
            print("Press Ctrl+C to stop.")

            while True:
                line_bytes = ser.readline()
                if not line_bytes:
                    continue

                line = line_bytes.decode("utf-8", errors="replace").strip()
                if raw_file:
                    raw_file.write(line + "\n")
                    raw_file.flush()

                parsed_line = parse_serial_line(line)
                if parsed_line is None or parsed_line.line_type != "csv":
                    continue

                parsed = parsed_line.payload
                row = enrich_csv_row(parsed, line)
                writer.writerow(row)
                csv_file.flush()

                frame_id = parsed["frame_id"]
                frame_rows[frame_id].append(parsed)
                if len(frame_rows[frame_id]) == 10:
                    summarize_frame(frame_id, frame_rows[frame_id])
                    del frame_rows[frame_id]
        finally:
            if raw_file:
                raw_file.close()


def main() -> int:
    config = parse_args()
    try:
        run_logger(config)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    except serial.SerialException as exc:
        print(f"Serial error: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
