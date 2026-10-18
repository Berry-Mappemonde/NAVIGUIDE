"""Le délai du poste tue tout le groupe, pas seulement le bash."""
import os
import signal

import run_lots


def test_timeout_kills_the_grandchild(tmp_path):
    pidfile = tmp_path / "child.pid"
    code, out = run_lots.run_process_group(
        ["bash", "-c", f"sleep 60 & echo $! > {pidfile}; wait"],
        cwd=str(tmp_path),
        env=os.environ.copy(),
        timeout=2,
    )
    assert code is None
    child = int(pidfile.read_text().strip())
    try:
        os.kill(child, 0)
        alive = True
    except ProcessLookupError:
        alive = False
    if alive:
        os.kill(child, signal.SIGKILL)
    assert not alive
