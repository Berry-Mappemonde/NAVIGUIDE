import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Hermetic tests: never reach the live Blue Intelligence API by accident.
# Port 9 (discard) refuses at once, so the atlas / BI clients fall back
# immediately instead of making hundreds of real HTTPS calls (CI froze for
# 45 min on /recompute before this). A test that wants the live default
# deletes the variable itself (see test_bi_base_defaults_to_live).
os.environ.setdefault("BI_API_URL", "http://127.0.0.1:9/api")
