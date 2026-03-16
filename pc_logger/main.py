from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from gui_app import configure_qt_runtime, main

if __name__ == "__main__":
    configure_qt_runtime()
    raise SystemExit(main())
