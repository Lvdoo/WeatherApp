import requests
from config import APIKEY

def get_weather(city : str, unit : str) -> dict:
    """
    Retrieve weather information for a given city
    Args:
        city (string): Name of the city for the weather
        unit (string): Unit for the temperature : Metric(Celsius) or Imperial(Fahrenheit)

    Returns:
        dict: Return a dict of all the infos about the weather
    """

    if not city or not isinstance(city, str):
        raise ValueError("City must be a non-empty string")
    if unit not in ("metric", "imperial"):
        raise ValueError("Unit must be 'metric' or 'imperial'")
    
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city.strip().capitalize()}&appid={APIKEY}&units={unit.strip().lower()}"
    response = requests.get(url)
    data = response.json()
    
    if response.status_code != 200 :  #http code = 200 : everything ok
        raise ValueError(f"API error: {data.get('message', 'Unknown error')}")
    
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
        "sunset": data["sys"]["sunset"],
        "timezone": data["timezone"]
    }
    return weather_dict
