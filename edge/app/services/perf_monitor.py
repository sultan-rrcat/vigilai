# edge/app/services/perf_monitor.py
import time
import json
import logging
import os
import psutil
from contextlib import contextmanager
from app.core.config import settings

logger = logging.getLogger(__name__)

PERF_LOG_PATH = os.path.join(settings.LOG_DIR, "perf.jsonl")


class PerfMonitor:
    def __init__(self):
        self._stage_times: dict[str, float] = {}
        self._frame_start: float = 0.0
        self._process = psutil.Process()
        self._config_snapshot = {
            "frame_stride":       settings.FRAME_STRIDE,
            "model_path":         settings.MODEL_PATH,
            "min_dwell_seconds":  settings.MIN_DWELL_SECONDS,
            "track_ttl_seconds":  settings.TRACK_TTL_SECONDS,
            "camera_id":          settings.CAMERA_ID,
        }
        # Open in append mode so each run appends to the same file
        self._log_file = open(PERF_LOG_PATH, "a", buffering=1)  # line-buffered
        logger.info(f"PerfMonitor writing to {PERF_LOG_PATH}")

    @contextmanager
    def stage(self, name: str):
        """Times a single pipeline stage. Use as: with monitor.stage('inference'): ..."""
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self._stage_times[name] = round((time.perf_counter() - t0) * 1000, 2)  # ms

    def begin_frame(self):
        """Call at the very start of each frame iteration."""
        self._frame_start = time.perf_counter()
        self._stage_times = {}

    def flush(self, fps: float, active_tracks: int):
        """
        Call at the end of each frame. Writes one JSONL record with:
        - wall-clock timestamp
        - per-stage latencies (ms)
        - total frame time (ms)
        - live FPS
        - CPU %, RAM usage
        - active track count
        - full config snapshot for easy comparison across runs
        """
        total_ms = round((time.perf_counter() - self._frame_start) * 1000, 2)

        record = {
            "ts":            time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "fps":           round(fps, 2),
            "frame_ms":      total_ms,
            "stages_ms":     self._stage_times,
            "active_tracks": active_tracks,
            "cpu_pct":       self._process.cpu_percent(),        # % since last call
            "ram_mb":        round(self._process.memory_info().rss / 1_048_576, 1),
            "config":        self._config_snapshot,
        }

        self._log_file.write(json.dumps(record) + "\n")

    def close(self):
        self._log_file.close()