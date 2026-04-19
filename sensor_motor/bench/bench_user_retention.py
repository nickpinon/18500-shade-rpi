#!/usr/bin/env python3
"""
User detection retention over a window.

Metric: fraction of frames where torso center is found (not None, None).

Run on Raspberry Pi with camera:

  cd 18500-shade-rpi && python3 sensor_motor/bench/bench_user_retention.py --seconds 60

Target from test plan: >= 95% while a person is in frame (stand in view;
background-only runs will score low — use as intended).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

SM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SM))

from user_detection.userDetection import (  # noqa: E402
    get_user_errors,
    init_user_detection,
    shutdown_user_detection,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=30.0, help="Collection duration")
    args = ap.parse_args()

    init_user_detection()
    end = time.perf_counter() + args.seconds
    total = 0
    hits = 0
    while time.perf_counter() < end:
        ex, ey = get_user_errors()
        total += 1
        if ex is not None and ey is not None:
            hits += 1

    shutdown_user_detection()

    if total == 0:
        print("No samples collected.")
        return

    pct = 100.0 * hits / total
    print(f"Frames: {total}  detected: {hits}  retention={pct:.1f}%")
    print("Target: >= 95% (with subject in frame)")
    print("PASS" if pct >= 95.0 else "REVIEW (below 95%)")


if __name__ == "__main__":
    main()
