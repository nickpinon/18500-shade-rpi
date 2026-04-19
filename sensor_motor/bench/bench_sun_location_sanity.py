#!/usr/bin/env python3
"""
Sun math sanity check (no Pi hardware). Run from repo root:

  cd 18500-shade-rpi && python3 sensor_motor/bench/bench_sun_location_sanity.py

Supports the "sun alignment" prep: verify elevation/azimuth are finite and
change reasonably with time for a fixed site.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sensor_motor"))

from sun_location import calculate_sun_direction  # noqa: E402


def main() -> None:
    lat, lon = 40.4406, -79.9959
    noon = "2026-06-21T16:00:00+00:00"  # ~noon EDT summer solstice
    s = calculate_sun_direction(lat, lon, noon)
    print(f"Pittsburgh {noon}")
    print(f"  elevation_deg={s.elevation_deg:.2f}  azimuth_deg={s.azimuth_deg:.2f}  source={s.source}")
    assert math.isfinite(s.elevation_deg) and math.isfinite(s.azimuth_deg)
    assert -90 <= s.elevation_deg <= 90
    assert 0 <= s.azimuth_deg < 360
    print("OK: sun_location sanity checks passed.")


if __name__ == "__main__":
    main()
