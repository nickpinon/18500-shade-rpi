#!/usr/bin/env python3
"""
Tracking pipeline latency (MoveNet + camera one frame).

Metric: time from start of get_user_errors() until return (proxy for
"user detection → control signal", not including motor thread).

Run on Raspberry Pi with camera and model installed:

  cd 18500-shade-rpi && python3 sensor_motor/bench/bench_tracking_latency.py --samples 30

Target from test plan: < 250 ms (interpret as one-frame perception latency).
"""
from __future__ import annotations

import argparse
import statistics
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
    ap.add_argument("--samples", type=int, default=40, help="Timed frames after warmup")
    ap.add_argument("--warmup", type=int, default=5, help="Untimed frames first")
    args = ap.parse_args()

    init_user_detection()
    for _ in range(args.warmup):
        get_user_errors()

    times_ms: list[float] = []
    for _ in range(args.samples):
        t0 = time.perf_counter()
        get_user_errors()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        times_ms.append(dt_ms)

    shutdown_user_detection()

    mean = statistics.mean(times_ms)
    p50 = statistics.median(times_ms)
    try:
        p95 = statistics.quantiles(times_ms, n=20)[18]
    except statistics.StatisticsError:
        p95 = max(times_ms)
    worst = max(times_ms)

    budget = 250.0
    print(f"Samples: {args.samples}  (warmup {args.warmup})")
    print(f"Latency ms — mean={mean:.1f}  p50={p50:.1f}  p95={p95:.1f}  max={worst:.1f}")
    print(f"Budget (test plan): < {budget:.0f} ms per frame")
    print("PASS" if p95 < budget else "REVIEW (p95 over budget)")


if __name__ == "__main__":
    main()
