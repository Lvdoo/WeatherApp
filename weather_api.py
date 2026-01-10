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

def geolocalisation(city : str) -> str : 
    """
    Get latitude and logitude of a city

    Args:
        city (str): Name of the city

    Returns:
        str: Latitude and logitude of the city
    """

    if not city or not isinstance(city, str):
        raise ValueError("City must be a non-empty string")
    url = f"https://api.openweathermap.org/geo/1.0/direct?q={city}&appid={APIKEY}"
    response = requests.get(url)
    data = response.json()

    if response.status_code != 200 :  #http code = 200 : everything ok
        raise ValueError(f"API error: {data.get('message', 'Unknown error')}")
    
    latitude = data[0]["lat"]
    longitude = data[0]["lon"]

    return latitude, longitude

def get_previsional_weather(city : str) -> dict :
    """
    Get the weather for the next 3 days
    Args:
        latitude (str): latitude of the city for the weather
        longitude (str): longitude of the city for the weather

    Returns:
        dict: Return a dictionnary of infos about weather of a city
    """
    latitude, longitude = geolocalisation(city)
    
    if not latitude is None or longitude is None:
        raise ValueError("City must be a non-empty string")
    
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={latitude}&lon=2.{longitude}&appid={APIKEY}"
    response = requests.get(url)
    data = response.json()

    if response.status_code != 200 :  #http code = 200 : everything ok
        raise ValueError(f"API error: {data.get('message', 'Unknown error')}")
    
    hourly_weather = {}

    for forecast in data["list"]:
        hour = forecast["dt_txt"] 

        hourly_weather[hour] = {
            "temp": forecast["main"]["temp"],
            "temp_min": forecast["main"]["temp_min"],
            "temp_max": forecast["main"]["temp_max"],
            "weather": forecast["weather"][0]["main"],
            "icon": forecast["weather"][0]["icon"],
            "wind": forecast["wind"]["speed"],
        }

    return hourly_weather

