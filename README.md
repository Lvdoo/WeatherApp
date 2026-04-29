# 🌤 Weather App (Python)

A simple desktop weather application built with Python.  
The app allows users to check real-time weather information for a given city using a weather API and the weather for the 5 next days (general conditions, minimum and maximum temperatures)
Warning : the graphical interface might not be optimal depending on the dimensions of your computer.

---

## 🚀 Features

- Search weather by city name  
- Real-time weather data  
- Display:
  - Temperature  
  - Weather condition (clear, rain, clouds…)  
  - Humidity  
  - Wind speed  
- Simple and user-friendly interface  
- Error handling (invalid city, API issues)  

---

## 🛠 Technologies Used

- Python 3
- Tkinter (GUI)
- Requests (API calls)
- Weather API (e.g. OpenWeatherMap)

---

## 📁 Project Structure

```bash
weather_app/
│── main.py # Application entry point
│── gui.py # GUI interface
│── weather_api.py # API requests and data handling
│── utils.py # Utility functions (conversions, formatting)
│── requirements.txt
│── .gitignore
│── README.md
```
---

## ⚙️ Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/Lvdoo/WeatherApp
cd WeatherApp
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate it:

Windows :

```bash
.venv\Scripts\activate
```

macOS / Linux :

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```
---

## Configure the API key

You need an API key to run the project.

- Create an account on OpenWeather : You can get a free API key from: [OpenWeather](https://openweathermap.org/)
- Get your API key
- Add it in your project:

Example:

Create a file named `config.py` inside the folder:

```python
APIKEY = "YOUR_API_KEY_HERE"
```

⚠️ Never share your API key publicly.

---

## ▶️ How to Run

```bash
python main.py
```

---

## 🔍 How It Works

- User enters a city name
- The app sends a request to the weather API
- The API returns JSON data
- The app extracts key information
- Data is displayed to the user

---

## ⚠️ Limitations

- Requires internet connection
- API rate limits may apply
- Errors if city name is invalid
- Weather precision depends on the API

---

## 📈 Possible Improvements

- Add geolocation
- Improve UI design
- Handle errors more gracefully
- - Integrate a more detailed or reliable weather API

---

## 🧑‍💻 Author

Created by Lvdoo

---

## ⭐ Notes

This project is a good introduction to:

- API integration
- Data parsing (JSON)
- Building simple interactive apps
