#!/usr/bin/env python3
"""
Pi-side latency from "manual command applied" to first motor step call.

This does NOT include iOS radio time — only the control path you own on the Pi:
set manual direction → one integrator-style tick → send_motor_commands.

Run anywhere (motor sim if no GPIO):

  cd 18500-shade-rpi && python3 sensor_motor/bench/bench_command_to_motor_latency.py --trials 50

For full "app latency" including BLE, add phone→Pi timing with logs or
instruments; this script bounds the software stack after the command is known.
Target from test plan: < 200 ms (use as lower bound; add radio + loop slack).
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

SM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SM))

import motor as motor_mod  # noqa: E402


def send_motor_commands(error_x, error_y):
    """Same logic as integrator.send_motor_commands (trimmed)."""
    m = motor_mod.motor
    moved = False
    if error_x is not None and error_x != 0:
        steps = min(max(abs(error_x) // 10, 1), 50)
        if error_x > 0:
            m.step_axis("horizontal", True, steps=steps)
        else:
            m.step_axis("horizontal", False, steps=steps)
        moved = True
    if error_y is not None and error_y != 0:
        steps = min(max(abs(error_y) // 10, 1), 50)
        if error_y > 0:
            m.step_axis("vertical", True, steps=steps)
        else:
            m.step_axis("vertical", False, steps=steps)
        moved = True
    if not moved:
        m.stop_all()


def one_tick(direction: str):
    if direction == "left":
        return -5, 0
    if direction == "right":
        return 5, 0
    if direction == "up":
        return 0, 5
    if direction == "down":
        return 0, -5
    return 0, 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=100)
    args = ap.parse_args()

    recorded: list[float] = []
    first_call: list[float | None] = []

    def make_hook():
        def step_axis(axis, forward, steps=12800):
            now = time.perf_counter()
            if first_call[0] is None:
                first_call[0] = now
            # Do not call orig_step here — avoids spawning threads and log spam during bench.

        return step_axis

    orig_step = motor_mod.motor.step_axis
    budget_ms = 200.0

    for _ in range(args.trials):
        first_call = [None]
        motor_mod.motor.step_axis = make_hook()  # type: ignore[method-assign]

        t_cmd = time.perf_counter()
        direction = "left"
        ex, ey = one_tick(direction)
        send_motor_commands(ex, ey)

        if first_call[0] is not None:
            recorded.append((first_call[0] - t_cmd) * 1000.0)

        motor_mod.motor.step_axis = orig_step  # type: ignore[method-assign]

    if not recorded:
        print("No motor calls recorded (unexpected).")
        return

    p50 = statistics.median(recorded)
    mean = statistics.mean(recorded)
    worst = max(recorded)
    print(f"Trials: {args.trials}  (first horizontal/vertical step_axis after send)")
    print(f"Latency ms — mean={mean:.3f}  p50={p50:.3f}  max={worst:.3f}")
    print(f"Note: this is in-process only; BLE + 10 Hz loop add real user latency.")
    print(f"Sanity check vs {budget_ms:.0f} ms budget: PASS (Pi stack tiny)" if p50 < budget_ms else "REVIEW")


if __name__ == "__main__":
    main()
