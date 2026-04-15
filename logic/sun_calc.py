#!/usr/bin/env python3
from pysolar.solar import get_altitude, get_azimuth
import datetime

# Default to Pittsburgh, PA for testing
PGH_LAT = 40.4406
PGH_LON = -79.9959

def get_sun_position(latitude=PGH_LAT, longitude=PGH_LON, phone_timestamp_str=None):
    """
    Returns the Sun's Pitch (Altitude) and Yaw (Azimuth) based on GPS and time.
    """
    # Fallback just in case BLE sends None instead of an empty payload
    if latitude is None or longitude is None:
        latitude, longitude = PGH_LAT, PGH_LON
        
    # 1. Try to use the exact time provided by the phone app
    if phone_timestamp_str:
        try:
            # Assumes the phone sends standard ISO 8601 format (e.g., "2026-04-15T13:14:00Z")
            # Replace Z to ensure Python 3.11- parses it as UTC correctly
            date = datetime.datetime.fromisoformat(phone_timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            print("[Warning] Time parse error. Falling back to Pi clock.")
            date = datetime.datetime.now(datetime.timezone.utc)
    else:
        # 2. Fallback to Pi's internal clock if no phone time is available
        date = datetime.datetime.now(datetime.timezone.utc)
    
    # Calculate solar position
    altitude = get_altitude(latitude, longitude, date)
    azimuth = get_azimuth(latitude, longitude, date)
    
    return altitude, azimuth

if __name__ == "__main__":
    print("=== Sun Calculator Tests (Pittsburgh, PA) ===")
    
    # Test 1: Using the Pi's internal real-time clock
    alt1, az1 = get_sun_position()
    print("\nTest 1: Live Pi Clock (Current Time)")
    print(f"  Pitch (Altitude): {alt1:.2f}°")
    print(f"  Yaw (Azimuth):    {az1:.2f}°")

    # Test 2: Simulating a timestamp sent from the phone app via BLE
    # This simulates a high-sun summer day (June 21, 2026 at 16:00 UTC / 12:00 PM EDT)
    simulated_phone_time = "2026-06-21T16:00:00Z" 
    alt2, az2 = get_sun_position(phone_timestamp_str=simulated_phone_time)
    print(f"\nTest 2: Simulated Phone BLE Time ({simulated_phone_time})")
    print(f"  Pitch (Altitude): {alt2:.2f}°")
    print(f"  Yaw (Azimuth):    {az2:.2f}°")
    
    # Test 3: Simulating a malformed string sent from the app
    print("\nTest 3: Malformed App Data (Should print warning and fallback to Pi clock)")
    alt3, az3 = get_sun_position(phone_timestamp_str="BadTimeData123")
    print(f"  Pitch (Altitude): {alt3:.2f}°")
    print(f"  Yaw (Azimuth):    {az3:.2f}°")