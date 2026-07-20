import os
import subprocess
import sys
import time

import httpx

from .. import config


def start_engine() -> bool:
    """Launch VOICEVOX engine if not already running."""
    if check_engine():
        return True
    engine_path = config.VOICEVOX_ENGINE
    if not os.path.exists(engine_path):
        print(f"[voicevox] Engine not found at {engine_path}", file=sys.stderr)
        return False
    try:
        subprocess.Popen(
            [engine_path],
            cwd=os.path.dirname(engine_path),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("[voicevox] Engine launched from backend", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[voicevox] Failed to start: {e}", file=sys.stderr)
        return False


def check_engine(timeout: float = 2) -> bool:
    """Check if VOICEVOX engine is reachable."""
    try:
        resp = httpx.get(f"{config.VOICEVOX_BASE_URL}/version", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def wait_ready(timeout: int = 60) -> bool:
    """Poll VOICEVOX engine until it responds, or timeout (seconds)."""
    for _ in range(timeout):
        if check_engine(timeout=1):
            return True
        time.sleep(0.5)
    return False


def stop_engine():
    """No-op in Docker mode. VOICEVOX runs as an independent container."""
    pass
