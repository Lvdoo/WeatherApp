# 🌤 Weather App (Python)

A simple desktop weather application built with Python.  
The app allows users to check real-time weather information for a given city using a weather API.

---

## 📌 Features

- Get current weather data by city name
- Display temperature, humidity, and weather conditions
- Simple and clean graphical user interface (GUI)
- Weather icons based on conditions
- Modular and easy-to-read code structure

---

## 🛠 Technologies Used

- Python 3
- Tkinter (GUI)
- Requests (API calls)
- Weather API (e.g. OpenWeatherMap)

---

## 📁 Project Structure
weather_app/
│── main.py # Application entry point
│── gui.py # GUI interface
│── weather_api.py # API requests and data handling
│── utils.py # Utility functions (conversions, formatting)
│── config.py # API key configuration (ignored)
│── icons/ # Weather icons
│── pycache/ # Python cache (ignored)
│── .venv/ # Virtual environment (ignored)
│
requirements.txt
.gitignore
README.md

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository
```bash
git clone https://github.com/your-username/weather-app.git
cd weather-app

python -m venv .venv

2️⃣ Create a virtual environment

python -m venv .venv

Activate it:

Windows

.venv\Scripts\activate

macOS / Linux

source .venv/bin/activate

3️⃣ Install dependencies
pip install -r requirements.txt

4️⃣ Configure the API key

Create a file named config.py inside the weather_app/ folder:

API_KEY = "YOUR_API_KEY_HERE"


You can get a free API key from:
https://openweathermap.org/