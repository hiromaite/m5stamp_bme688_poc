# Windows Build Notes

This document describes the current plan for producing a Windows executable for
the PC logger GUI.

## Packaging Strategy

Primary path:

- `pyside6-deploy`
- deploy mode: `standalone` first

Fallback path:

- `PyInstaller`

The project currently uses `PySide6` and `pyqtgraph`, so the first packaging
attempt should follow the official Qt for Python deployment flow.

## Expected Windows Build Environment

- `Windows 11`
- Python `3.12`
- a fresh virtual environment inside `pc_logger/.venv`
- Visual Studio Build Tools or a Visual Studio installation with MSVC tools
- `dumpbin` available in `PATH`

## Project Files Prepared For Packaging

- `pc_logger/main.py`
  - GUI entry point for packaging
- `pc_logger/pc_logger.pyproject`
  - Qt project description
- `pc_logger/pysidedeploy.spec`
  - deployment configuration generated or maintained for `pyside6-deploy`

## First Packaging Attempt

From `pc_logger/` on Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pyside6-deploy -c pysidedeploy.spec -f --mode standalone
```

## Windows Smoke Test Checklist

- application starts without Python installed globally
- serial ports are listed
- the device connects successfully
- live plots update
- `Record` / `Stop` works
- `Start Segment` / `End Segment` works
- profile update works with a 3-step profile
- profile reset restores the default profile
- CSV output is written successfully

## Open Questions

- whether `standalone` output is sufficient for distribution or whether a
  single-file format is required later
- whether an application icon should be added before `v01.00`
- whether a Windows code-signing step is required in the release process
