import requests
from config import APIKEY

# for the wind :
# 0° = nord
# 90° = est
# 180° = sud
# 270° = ouest

# for clouds :
# 0 → ciel totalement dégagé
# 100 → ciel complètement couvert

# metric = celsius
# imperial = fahrenheit

def get_weather(city, unit) -> dict:
    """
    Args:
        city (string): Name of the xity for the weather
        unit (string): Unit for the temperature : Celsius or Fahrenheit

    Returns:
        dict: Return a dict of all the infos about the weather
    """

    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={APIKEY}&units={unit}"
    response = requests.get(url)
    data = response.json()
    weather_dict = {
        "description": data["weather"][0]["description"],
        "temperature": data["main"]["temp"],
        "felt_temp": data["main"]["feels_like"],
        "min_temp": data["main"]["temp_min"],
        "max_temp": data["main"]["temp_max"],
        "pressure": data["main"]["pressure"],
        "humidity": data["main"]["humidity"],
        "wind_speed": data["wind"]["speed"],
        "wind_orientation": data["wind"]["deg"],
        "clouds": data["clouds"]["all"],
        "time": data["dt"],
        "sunrise": data["sys"]["sunrise"],
        "sunset": data["sys"]["sunset"]
    }
    return weather_dict
