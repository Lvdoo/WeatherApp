from datetime import datetime 

def to_time(timestamp : int, timezone : int) -> datetime :
    if timestamp is not None and timezone is not None :
        dt = datetime.fromtimestamp(timestamp + timezone)
        return dt
    else :
        raise ValueError("timestamp and timezone must be integers")

def wind_deg_to_direction(wind_deg : float) -> str :
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
        raise ValueError("wind_deg must be a positive integer.")