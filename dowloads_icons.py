import requests

icons = ["01d","01n","02d","02n","03d","03n","04d","04n",
         "09d","09n","10d","10n","11d","11n","13d","13n","50d","50n"]

for icon in icons:
    url = f"http://openweathermap.org/img/wn/{icon}@2x.png"
    r = requests.get(url)
    if r.status_code == 200:
        with open(f"icons/{icon}.png", "wb") as f:
            f.write(r.content)
    else:
        print(f"Failed to download {icon}")
