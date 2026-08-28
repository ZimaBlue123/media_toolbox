"""Allow running as ``python -m video_repair``."""
from __future__ import annotations

from .cli import main

raise SystemExit(main())
