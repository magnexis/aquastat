from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

# Keep the test suite isolated from any local production-oriented .env file.
os.environ.setdefault("AQUASTAT_ENVIRONMENT", "test")
os.environ.setdefault("AQUASTAT_API_KEY_HASHES", "[]")
os.environ.setdefault("AQUASTAT_ADMIN_API_KEY_HASHES", "[]")
os.environ.setdefault("AQUASTAT_REDIS_ENABLED", "false")
os.environ.setdefault("AQUASTAT_BOOTSTRAP_DATABASE_ON_STARTUP", "false")
