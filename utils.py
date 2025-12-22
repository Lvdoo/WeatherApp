from datetime import datetime 
import pytz

def to_time(timestamp : int, timezone : int) -> int :
    return datetime.fromtimestamp(timestamp)