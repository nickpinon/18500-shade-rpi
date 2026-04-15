"""
Sun direction calculator on Raspberry Pi.

Uses latitude/longitude (and optional timestamp) received from iOS over BLE,
then computes the Sun's elevation and azimuth on the Pi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math


DEFAULT_LATITUDE = 40.4406
DEFAULT_LONGITUDE = -79.9959


@dataclass(frozen=True)
class SunDirection:
    elevation_deg: float
    azimuth_deg: float
    source: str


def _parse_timestamp(timestamp_str: str | None) -> datetime:
    """Parse ISO-8601 timestamp from iOS; fallback to current UTC time."""
    if not timestamp_str:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def _julian_day(dt_utc: datetime) -> float:
    """Convert UTC datetime to Julian Day."""
    year = dt_utc.year
    month = dt_utc.month
    day = dt_utc.day + (
        dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600
    ) / 24

    if month <= 2:
        year -= 1
        month += 12

    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)
    return (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day
        + b
        - 1524.5
    )


def calculate_sun_direction(
    latitude: float | None,
    longitude: float | None,
    timestamp_str: str | None = None,
) -> SunDirection:
    """
    Calculate Sun elevation and azimuth using NOAA-style solar position math.

    Returns:
      - elevation_deg: angle above horizon
      - azimuth_deg: compass angle (0=N, 90=E, 180=S, 270=W)
      - source: "ble_location" or "default_location"
    """
    if latitude is None or longitude is None:
        latitude = DEFAULT_LATITUDE
        longitude = DEFAULT_LONGITUDE
        source = "default_location"
    else:
        source = "ble_location"

    dt_utc = _parse_timestamp(timestamp_str).astimezone(timezone.utc)
    jd = _julian_day(dt_utc)
    t = (jd - 2451545.0) / 36525.0

    # Geometric mean longitude and anomaly of the sun (degrees)
    l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360
    m = 357.52911 + t * (35999.05029 - 0.0001537 * t)

    # Eccentricity of Earth's orbit
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)

    # Sun equation of center
    c = (
        math.sin(math.radians(m)) * (1.914602 - t * (0.004817 + 0.000014 * t))
        + math.sin(math.radians(2 * m)) * (0.019993 - 0.000101 * t)
        + math.sin(math.radians(3 * m)) * 0.000289
    )
    true_long = l0 + c

    # Apparent longitude
    omega = 125.04 - 1934.136 * t
    lambda_sun = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))

    # Mean and corrected obliquity
    eps0 = (
        23
        + (26 + ((21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60)) / 60
    )
    eps = eps0 + 0.00256 * math.cos(math.radians(omega))

    # Solar declination
    decl = math.degrees(
        math.asin(math.sin(math.radians(eps)) * math.sin(math.radians(lambda_sun)))
    )

    # Equation of time (minutes)
    y = math.tan(math.radians(eps / 2)) ** 2
    eq_time = 4 * math.degrees(
        y * math.sin(2 * math.radians(l0))
        - 2 * e * math.sin(math.radians(m))
        + 4 * e * y * math.sin(math.radians(m)) * math.cos(2 * math.radians(l0))
        - 0.5 * y * y * math.sin(4 * math.radians(l0))
        - 1.25 * e * e * math.sin(2 * math.radians(m))
    )

    # True solar time and hour angle
    minutes = dt_utc.hour * 60 + dt_utc.minute + dt_utc.second / 60
    true_solar_minutes = (minutes + eq_time + 4 * longitude) % 1440
    hour_angle = true_solar_minutes / 4 - 180

    # Solar zenith / elevation
    lat_rad = math.radians(latitude)
    decl_rad = math.radians(decl)
    ha_rad = math.radians(hour_angle)
    cos_zenith = (
        math.sin(lat_rad) * math.sin(decl_rad)
        + math.cos(lat_rad) * math.cos(decl_rad) * math.cos(ha_rad)
    )
    cos_zenith = min(1.0, max(-1.0, cos_zenith))
    zenith = math.degrees(math.acos(cos_zenith))
    elevation = 90 - zenith

    # Azimuth (0=N, clockwise)
    azimuth = (
        math.degrees(
            math.atan2(
                math.sin(ha_rad),
                math.cos(ha_rad) * math.sin(lat_rad)
                - math.tan(decl_rad) * math.cos(lat_rad),
            )
        )
        + 180
    ) % 360

    return SunDirection(
        elevation_deg=elevation,
        azimuth_deg=azimuth,
        source=source,
    )
