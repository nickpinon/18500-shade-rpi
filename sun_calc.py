#!/usr/bin/env python3
from pysolar.solar import get_altitude, get_azimuth
import datetime

# Default to Pittsburgh, PA for testing
PGH_LAT = 40.4406
PGH_LON = -79.9959

def get_sun_position(latitude=PGH_LAT, longitude=PGH_LON):
    """
    Returns the Sun's Pitch (Altitude) and Yaw (Azimuth) based on GPS.
    Defaults to Pittsburgh, PA if no coordinates are provided.
    """
    if latitude is None or longitude is None:
        # Fallback just in case BLE sends None instead of an empty payload
        latitude, longitude = PGH_LAT, PGH_LON
        
    # Get current time with timezone awareness (UTC)
    date = datetime.datetime.now(datetime.timezone.utc)
    
    # Pitch (Altitude in degrees above horizon)
    altitude = get_altitude(latitude, longitude, date)
    
    # Yaw (Azimuth in degrees, True North = 0)
    azimuth = get_azimuth(latitude, longitude, date)
    
    return altitude, azimuth

if __name__ == "__main__":
    # Quick standalone test if you run `python3 sun_calculator.py` directly
    alt, az = get_sun_position()
    print("--- Sun Calculator Test (Pittsburgh, PA) ---")
    print(f"Current UTC Time: {datetime.datetime.now(datetime.timezone.utc)}")
    print(f"Sun Altitude (Pitch): {alt:.2f}°")
    print(f"Sun Azimuth (Yaw):    {az:.2f}°")