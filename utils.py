from datetime import datetime,timezone,timedelta

def to_time(timestamp : int, tz_offset : int) -> str :
    """
    Convert a UTC timestamp + timezone offset to a local datetime.
    Args:
        timestamp (int): timestamp of time 
        timezone (int): timestamp of time difference

    Raises:
        ValueError: message of error if values are wrong

    Returns:
        str: time in format Y-m-d H:M:S
    """
    if timestamp is None or tz_offset is None:
        raise ValueError("timestamp and tz_offset must be integers")
    dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    dt_local = dt_utc.astimezone(timezone(timedelta(seconds=tz_offset)))
    return dt_local.strftime("%Y-%m-%d %H:%M:%S")

def wind_deg_to_direction(wind_deg : float) -> str :
    """
    Convert wind degree to cardinal direction.
    Args:
        wind_deg (float): degree of wind

    Raises:
        ValueError: message of error if value is wrong

    Returns:
        str: return wind in form "N","NE","NW","S","SE","Sw","E",W"
    """
    if wind_deg < 22.5 or (wind_deg > 337.5 and wind_deg <= 360) :
        return "N"
    elif wind_deg >= 22.5 and wind_deg < 67.5 :
        return "NE"
    elif wind_deg >= 67.5 and wind_deg < 112.5 : 
        return "E"
    elif wind_deg >= 112.5 and wind_deg < 157.5 :
        return "SE"
    elif wind_deg >= 157.5 and wind_deg < 202.5 :
        return "S"
    elif wind_deg >= 202.5 and wind_deg < 247.5 :
        return "SW"
    elif wind_deg >= 247.5 and wind_deg < 292.5 :
        return "W"
    elif wind_deg >= 292.5 and wind_deg < 337.5 :
        return "NW"
    else : 
        raise ValueError("wind_deg must be a positive integer between 0 and 360.")
    
def clouds_to_text(clouds : int) -> str :
    """
    Convert cloud percentage to human-readable text.

    Args:
        clouds (int): Cloud coverage percentage (0–100)

    Returns:
        str: Description of cloud coverage
    """

    if not isinstance(clouds, int) or not 0 <= clouds <= 100:
        raise ValueError("clouds must be between 0 and 100")

    if clouds == 0:
        return "Clear sky"
    elif clouds < 25:
        return "Mostly clear"
    elif clouds < 50:
        return "Partly cloudy"
    elif clouds < 75:
        return "Mostly cloudy"
    else:
        return "Overcast"
    
def wind_speed_to_km_h(wind_speed : int) -> int :
    """
    Convert wind speed to km/h
    Args:
        wind_speed (int): Speed of the winf$d

    Returns:
        int: Wind speed in km/h
    """
    return wind_speed * 3.6