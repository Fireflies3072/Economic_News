from datetime import datetime, timedelta
import time
import pytz
import re

def parse_time_to_utc(time_str):
    """
    Parses a time string with timezone (e.g., "8:31 PM EDT, Sat March 15, 2025") and converts it to UTC.
    
    This function handles timezone abbreviations like EST, EDT, PST, etc. by mapping them
    to their corresponding IANA timezone names.

    Args:
        time_str: The time string to parse.

    Returns:
        A datetime object representing the time in UTC, or None if parsing fails.
    """
    # Dictionary mapping common timezone abbreviations to IANA timezone names
    timezone_map = {
        'EST': 'US/Eastern',  # Eastern Standard Time
        'EDT': 'US/Eastern',  # Eastern Daylight Time
        'CST': 'US/Central',  # Central Standard Time
        'CDT': 'US/Central',  # Central Daylight Time
        'MST': 'US/Mountain', # Mountain Standard Time
        'MDT': 'US/Mountain', # Mountain Daylight Time
        'PST': 'US/Pacific',  # Pacific Standard Time
        'PDT': 'US/Pacific',  # Pacific Daylight Time
        'GMT': 'GMT',         # Greenwich Mean Time
        'UTC': 'UTC',         # Coordinated Universal Time
    }
    
    # Extract timezone abbreviation
    match = re.search(r'\d+:\d+ [AP]M (\w+)', time_str)
    if not match:
        return None
    tz_abbr = match.group(1)
    # Remove timezone abbreviation for initial parsing
    time_str_no_tz = time_str.replace(tz_abbr, '').replace(',', '').replace('  ', ' ')
    
    # Parse the datetime without timezone
    dt = datetime.strptime(time_str_no_tz, "%I:%M %p %a %B %d %Y")
    
    # Apply the timezone
    if not tz_abbr in timezone_map:
        return None
    tz = pytz.timezone(timezone_map[tz_abbr])
    # Check if we need to adjust for DST
    is_dst = 'D' in tz_abbr  # True for EDT, CDT, etc.
    dt = tz.localize(dt, is_dst=is_dst)
        
    # Convert to UTC
    utc_dt = dt.astimezone(pytz.utc)
    return utc_dt

def convert_timezone(utc_dt, target_timezone):
    """
    Converts a datetime object to the specified timezone.

    Args:
        dt: The datetime object to convert.
        target_timezone: The target timezone (IANA timezone string, e.g., 'US/Eastern', 'Europe/London').

    Returns:
        A datetime object representing the time in the target timezone, or None if input is invalid.
    """
    if not isinstance(utc_dt, datetime):
        return None
        
    # Ensure the datetime is timezone-aware
    if utc_dt.tzinfo is None or utc_dt.tzinfo.utcoffset(utc_dt) is None:
        utc_dt = pytz.utc.localize(utc_dt)
    
    target_tz = pytz.timezone(target_timezone)
    converted_dt = utc_dt.astimezone(target_tz)
    return converted_dt

def convert_utc_to_eastern(utc_dt):
    """
    Converts a UTC datetime object to Eastern Time (US/Eastern).

    Args:
        utc_dt: The UTC datetime object.

    Returns:
        A datetime object representing the time in Eastern Time, or None if input is invalid.
    """
    return convert_timezone(utc_dt, "US/Eastern")

# Example usage
if __name__ == "__main__":
    time_str = "8:31 PM EDT, Sat March 15, 2025"
    utc_time = parse_time_to_utc(time_str)

    if utc_time:
        print(f"UTC Time: {utc_time}")
        # Convert to various timezones
        east_time = convert_timezone(utc_time, "US/Eastern")
        pacific_time = convert_timezone(utc_time, "US/Pacific")
        london_time = convert_timezone(utc_time, "Europe/London")
        tokyo_time = convert_timezone(utc_time, "Asia/Tokyo")
        
        print(f"Eastern Time: {east_time}")
        print(f"Pacific Time: {pacific_time}")
        print(f"London Time: {london_time}")
        print(f"Tokyo Time: {tokyo_time}")
    else:
        print("Failed to parse the time string.")

    time_str2 = "8:31 PM EST, Sat March 15, 2025"
    utc_time2 = parse_time_to_utc(time_str2)

    if utc_time2:
        print(f"UTC Time: {utc_time2}")
        eastern_time2 = convert_utc_to_eastern(utc_time2)
        if eastern_time2:
            print(f"Eastern Time: {eastern_time2}")
    else:
        print("Failed to parse the second time string.")

    # Current time
    current_utc = datetime.now(pytz.utc)
    print(f"Current UTC time: {current_utc}")
    print(f"Current local time: {datetime.fromtimestamp(time.time())}")