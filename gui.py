from tkinter import *
import weather_api
import utils
from PIL import Image, ImageTk
from datetime import datetime, timezone, timedelta

def display_weather() :

    #Create a window 
    window = Tk()

    #Personalize window 
    window.title("WeatherApp")
    window.geometry("1080x720")
    window.minsize(1080,720)
    window.config(bg = "#517DCA")

    #Interface in 3 frames
    top_frame = Frame(window, bg = "#517DCA")
    main_frame = Frame(window, bg = "#517DCA")
    infos_frame = Frame(window, bg = "#517DCA")

    #Subframes
    max_min_temp_frame = Frame(main_frame, bg = "#517DCA")
    humidity_frame = Frame(infos_frame, bg = "#517DCA")
    wind_frame = Frame(infos_frame, bg = "#517DCA")
    cloud_frame = Frame(infos_frame, bg = "#517DCA")
    time_frame = Frame(infos_frame, bg = "#517DCA")
    day_frame = Frame(infos_frame, bg = "#517DCA")

    #Labels and inputs
    label_city = Label(top_frame, text = "City : ", font = ('Helvetica', 30), bg = "#517DCA", fg = "white")
    city_input = Entry(top_frame, font = ('Helvetica', 20), bg = "#7895C7", fg = "white")

    label_temperature = Label(main_frame, text = "", bg = "#517DCA", font = ('Helvetica', 60), fg = "white")
    label_temp_felt = Label(main_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")
    label_max_temp = Label(max_min_temp_frame, text = "", bg = "#517DCA", font = ('Helvetica', 15), fg = "white")
    label_min_temp = Label(max_min_temp_frame, text = "", bg = "#517DCA", font = ('Helvetica', 15), fg = "white")

    label_humidity = Label(humidity_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")
    label_wind_direction = Label(wind_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")
    label_wind_speed = Label(wind_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")
    label_clouds = Label(cloud_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")
    label_sunrise = Label(time_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")
    label_sunset = Label(time_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")
    label_time = Label(day_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")

    #Images
    max_temp_image = ImageTk.PhotoImage(Image.open("icons/fleche_haut.png").resize((20,17)))
    label_max_temp_image = Label(max_min_temp_frame, image = "", bg = "#517DCA") 
    min_temp_image = ImageTk.PhotoImage(Image.open("icons/fleche_bas.png").resize((20,17)))
    label_min_temp_image = Label(max_min_temp_frame, image = "", bg = "#517DCA")

    humidity_image = ImageTk.PhotoImage(Image.open("icons/humidity_icon.png").resize((50,50)))
    label_humidity_image = Label(humidity_frame, image = "", bg = "#517DCA")
    wind_orientation_image = ImageTk.PhotoImage(Image.open("icons/orientation_icon.png").resize((50,50)))
    label_orientation_image = Label(wind_frame, image = "", bg = "#517DCA")
    wind_icon_image = ImageTk.PhotoImage(Image.open("icons/wind_icon.png").resize((50,50)))
    label_wind_icon_image = Label(wind_frame, image = "", bg = "#517DCA")
    clouds_image = ImageTk.PhotoImage(Image.open("icons/clouds_icon.png").resize((50,50)))
    label_cloud_image = Label(cloud_frame, image = "", bg = "#517DCA")
    sunrise_image = ImageTk.PhotoImage(Image.open("icons/sunrise_icon.png").resize((50,50)))
    label_sunrise_image = Label(time_frame, image = "", bg = "#517DCA")
    sunset_image = ImageTk.PhotoImage(Image.open("icons/sunset_icon.png").resize((50,50)))
    label_sunset_image = Label(time_frame, image = "", bg = "#517DCA")

    #Error message
    label_error = Label(main_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "#DA1A30")

    def display_infos(unit : str) :
        city = city_input.get().strip().capitalize()
        symbol = ""
        wind_speed_unit = ""

        if unit == "metric" :
            symbol = "°C"
            wind_speed_unit = "km/h"
        elif unit == "imperial" :
            symbol = "°F"
            wind_speed_unit = "mph"
        try :
            infos = weather_api.get_weather(city,unit)

            #Get temperature values rounded
            temperature = round(infos['temperature'])
            temp_felt = round(infos['felt_temp'])
            max_temp = round(infos['max_temp'])
            min_temp = round(infos['min_temp'])

            #Get other infos
            humidity = infos['humidity']
            wind_direction = infos['wind_orientation']
            wind_speed = round(infos['wind_speed'])
            clouds = infos['clouds']
            timezone_offset = infos['timezone']
            sunrise = utils.to_time(infos['sunrise'], timezone_offset)
            sunset = utils.to_time(infos['sunset'], timezone_offset)
            sunrise_time = sunrise[11:16]
            sunset_time = sunset[11:16]
            time = utils.to_time(infos['time'], timezone_offset)
            time_date = time[:11]
            
            #Update labels 
            label_error.config(text = "")

            label_temperature.config(text = f"{temperature}{symbol}")
            label_temp_felt.config(text = f"Temperature felt : {temp_felt}{symbol}")
            label_max_temp.config(text = f"{max_temp}{symbol}")
            label_min_temp.config(text = f"{min_temp}{symbol}")

            label_humidity.config(text = f"Humidity : {humidity}%")
            label_wind_direction.config(text = f"Wind Direction : {utils.wind_deg_to_direction(wind_direction)}")
            label_wind_speed.config(text = f"Wind Speed : {utils.wind_speed_to_km_h(wind_speed)} {wind_speed_unit}")
            label_clouds.config(text = f"Clouds : {utils.clouds_to_text(clouds)}")
            label_sunrise.config(text = f"Sunrise : {sunrise_time}")
            label_sunset.config(text = f"Sunset : {sunset_time}")
            label_time.config(text=f"Local Day/Time : {time_date} {datetime.now().strftime('%H:%M:%S')}")
            update_time(timezone_offset)

            #Udpate images
            label_max_temp_image.config(image = max_temp_image)
            label_max_temp_image.image = max_temp_image  
            label_min_temp_image.config(image = min_temp_image)
            label_min_temp_image.image = min_temp_image

            label_humidity_image.config(image = humidity_image)
            label_humidity_image.image = humidity_image
            label_orientation_image.config(image = wind_orientation_image)
            label_orientation_image.image = wind_orientation_image
            label_wind_icon_image.config(image = wind_icon_image)
            label_wind_icon_image.image = wind_icon_image
            label_cloud_image.config(image = clouds_image)
            label_cloud_image.image = clouds_image

            label_sunrise_image.config(image = sunrise_image)
            label_sunrise_image.image = sunrise_image
            label_sunset_image.config(image = sunset_image)
            label_sunset_image.image = sunset_image
            
        except Exception as e:

            # Reset all weather info labels
            label_temperature.config(text="")
            label_temp_felt.config(text="")
            label_max_temp.config(text="")
            label_min_temp.config(text="")
            label_humidity.config(text="")
            label_wind_direction.config(text="")
            label_wind_speed.config(text="")
            label_clouds.config(text="")
            label_sunrise.config(text="")
            label_sunset.config(text="")
            label_time.config(text="")

            # Reset images
            label_max_temp_image.config(image="")
            label_min_temp_image.config(image="")
            label_humidity_image.config(image="")
            label_orientation_image.config(image="")
            label_wind_icon_image.config(image="")
            label_cloud_image.config(image="")
            label_sunrise_image.config(image="")
            label_sunset_image.config(image="")

            # Display only the error message
            label_error.config(text=f"City not found or API error!")
            label_error.grid(row=1, columnspan=2)

    def update_time(timezone_offset : int):
        """
        Get the time and update it
        
        :param timezone_offset : 
        """""
        now_local = datetime.now(timezone(timedelta(seconds=timezone_offset)))
        time_str = now_local.strftime('%Y-%m-%d %H:%M:%S')
        label_time.config(text=f"Local Day/Time : {time_str}")
        label_time.after(1000, lambda: update_time(timezone_offset))

    #Units buttons to display weather
    celsius_button = Button(top_frame, text = "Celsius", font = ('Helvetica', 20), bg = "white", fg = "#4065A4", command = lambda : display_infos("metric"), width = 12)
    fahrenheit_button = Button(top_frame, text = "Fahrenheit", font = ('Helvetica', 20), bg = "white", fg = "#4065A4", command = lambda : display_infos("imperial"), width = 12)

    #Display labels of top_frame
    label_city.grid(row = 0, column = 0, sticky = "e", padx = 5, pady = (20,5))
    city_input.grid(row = 0, column = 1, padx = 10, pady = (20,5))
    celsius_button.grid(row = 1, column = 0, columnspan = 3, pady=5, sticky = W) #columnspan permet à "search_button" de prendre 2 colonnes
    fahrenheit_button.grid(row = 1, column = 1, columnspan = 3, pady=5, sticky = E)

    #Display labels and images of main_frame
    label_temperature.grid(row = 0,column = 1, pady = (50,5))
    label_temp_felt.grid(row = 1, column = 1)
    label_max_temp_image.grid(in_ = max_min_temp_frame, row = 0, column = 0, pady = 5) #in_ permet de préciser dans quel frame on est, sans in_, comme temperature est dans top_frame programme croit que le reste est dans top_frame
    label_max_temp.grid(in_ = max_min_temp_frame, row = 0, column = 1, padx = (0,50), pady = 5)
    label_min_temp_image.grid(in_ = max_min_temp_frame, row = 0, column = 2, padx = (50,0), pady = 5)
    label_min_temp.grid(in_ = max_min_temp_frame, row = 0, column = 3, pady = 5)

    #Display labels and images of infos_frame
    label_humidity_image.grid(row = 0, column = 0, pady = (50,5))
    label_humidity.grid(row = 0, column = 1, padx = (0,40), pady = (50,5))
    label_orientation_image.grid(row = 0, column = 0, pady = (50,5))
    label_wind_direction.grid(row = 0, column = 1, padx = (0,40), pady = (50,5))
    label_wind_icon_image.grid(row = 0, column = 2, pady = (50,5))
    label_wind_speed.grid(row = 0, column = 3, padx = (0,40), pady = (50,5))
    label_cloud_image.grid(row = 0, column = 0, pady = (50,5))
    label_clouds.grid(row = 0, column = 1, padx = (0,40), pady = (50,5))
    label_sunrise_image.grid(row = 0, column = 0, pady = (50,5))
    label_sunrise.grid(row = 0, column = 1, padx = (0,40), pady = (50,5))
    label_sunset_image.grid(row = 0, column = 2, pady = (50,5))
    label_sunset.grid(row = 0, column = 3, padx = (0,40), pady = (50,5))
    label_time.grid(pady = 25)
        
    #Display frames
    top_frame.pack(pady = 10)
    main_frame.pack()
    infos_frame.pack()

    max_min_temp_frame.grid(row = 2, columnspan = 2)
    humidity_frame.grid(row = 0, column = 0)
    wind_frame.grid(row = 0, column = 1)
    cloud_frame.grid(row = 0, column = 2)
    time_frame.grid(row = 1, columnspan = 3)
    day_frame.grid(row = 2, columnspan = 3)

    #Display window
    window.mainloop()