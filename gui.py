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
    humidity_frame = Frame(infos_frame, bg = "#517DCA")
    wind_frame = Frame(infos_frame, bg = "#517DCA")
    cloud_frame = Frame(infos_frame, bg = "#517DCA")
    time_frame = Frame(infos_frame, bg = "#517DCA")
    day_frame = Frame(infos_frame, bg = "#517DCA")

    #Labels and inputs
    label_city = Label(top_frame, text = "City : ", font = ('Helvetica', 20), bg = "#517DCA", fg = "white")
    label_unit = Label(top_frame, text = "Unit : ", font = ('Helvetica', 20), bg = "#517DCA", fg = "white")
    city_input = Entry(top_frame, font = ('Helvetica', 20), bg = "#7895C7", fg = "white")
    unit_input = Entry(top_frame, font = ('Helvetica', 20), bg = "#7895C7", fg = "white")

    label_temperature = Label(main_frame, text = "", bg = "#517DCA", font = ('Helvetica', 60), fg = "white")
    label_temp_felt = Label(main_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")
    label_max_temp = Label(main_frame, text = "", bg = "#517DCA", font = ('Helvetica', 15), fg = "white")
    label_min_temp = Label(main_frame, text = "", bg = "#517DCA", font = ('Helvetica', 15), fg = "white")

    label_humidity = Label(humidity_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")
    label_wind_direction = Label(wind_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")
    label_wind_speed = Label(wind_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")
    label_clouds = Label(cloud_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")
    label_sunrise = Label(time_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")
    label_sunset = Label(time_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")
    label_time = Label(day_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")

    #Images
    max_temp_image = ImageTk.PhotoImage(Image.open("icons/fleche_haut.png").resize((20,17)))
    label_max_temp_image = Label(main_frame, image = "", bg = "#517DCA") 
    min_temp_image = ImageTk.PhotoImage(Image.open("icons/fleche_bas.png").resize((20,17)))
    label_min_temp_image = Label(main_frame, image = "", bg = "#517DCA")

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

    def display_infos() :
        city = city_input.get().strip().capitalize()
        unit = unit_input.get().strip().lower()
        symbol = ""

        if unit == "celsius" or unit == "metric":
            unit = "metric"
            symbol = "°"
        elif unit == "fahrenheit" or unit == "imperial":
            unit = "imperial"
            symbol = "F"

        infos = weather_api.get_weather(city,unit)

        #This is to place the icon better
        if abs(round(infos['max_temp']) > 10) :
            padx_fleche_haut = (0,180)
        else : 
            padx_fleche_haut = (0,170)

        if abs(round(infos['min_temp'])) > 10 :
            padx_fleche_bas = (60,0)
        else :
            padx_fleche_bas = (70,0)

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
        sunrise = utils.to_time(infos['sunrise'], timezone)
        sunset = utils.to_time(infos['sunset'], timezone)
        sunrise_time = sunrise[11:16]
        sunset_time = sunset[11:16]
        time = utils.to_time(infos['time'], timezone)
        time_date = time[:12]

        #Get actual time
        now_local = datetime.now(timezone(timedelta(seconds=timezone_offset)))

        #Update labels 
        label_temperature.config(text = f"{temperature}{symbol}")
        label_temp_felt.config(text = f"Temperature felt : {temp_felt}{symbol}")
        label_max_temp.config(text = f"{max_temp}{symbol}")
        label_min_temp.config(text = f"{min_temp}{symbol}")

        label_humidity.config(text = f"Humidity : {humidity}%")
        label_wind_direction.config(text = f"Wind Direction : {utils.wind_deg_to_direction(wind_direction)}")
        label_wind_speed.config(text = f"Wind Speed : {utils.wind_speed_to_km_h(wind_speed)}")
        label_clouds.config(text = f"Clouds : {utils.clouds_to_text(clouds)}")
        label_sunrise.config(text = f"Sunrise : {sunrise_time}")
        label_sunset.config(text = f"Sunset : {sunset_time}")
        label_time.config(text=f"Local time : {time_date} {now_local.strftime('%H:%M')}")

        #Udpate images
        label_max_temp_image.config(image = max_temp_image)
        label_max_temp_image.image = max_temp_image
        label_max_temp_image.grid(row = 2, column = 1, padx = padx_fleche_haut, pady = 5) 
        label_min_temp_image.config(image = min_temp_image)
        label_min_temp_image.image = min_temp_image
        label_min_temp_image.grid(row = 2, column = 1, padx = padx_fleche_bas, pady = 5) 

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
        
        
    #Search button to display weather
    search_button = Button(top_frame, text = "Search", font = ('Helvetica', 20), bg = "white", fg = "#4065A4", command = display_infos)

    #Display labels of top_frame
    label_city.grid(row = 0, column = 0, sticky = "e", padx = 5, pady = (20,5))
    city_input.grid(row = 0, column = 1, padx = 10, pady = (20,5))
    label_unit.grid(row = 1, column = 0, sticky = "e", padx = 5, pady = 5)
    unit_input.grid(row = 1, column = 1, padx=10, pady = 5)
    search_button.grid(row = 2, column = 0, columnspan = 2, pady=5, sticky = EW) #columnspan permet à "search_button" de prendre 2 colonnes

    #Display labels and images of main_frame
    label_temperature.grid(row = 0,column = 1, pady = (50,5))
    label_temp_felt.grid(row = 1, column = 1)
    label_max_temp.grid(row = 2, column = 1, padx = (0,120), pady = 5)
    label_min_temp.grid(row = 2, column = 1, padx = (120,0), pady = 5)

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

    humidity_frame.grid(row = 0, column = 0)
    wind_frame.grid(row = 0, column = 1)
    cloud_frame.grid(row = 0, column = 2)
    time_frame.grid(row = 1, columnspan = 3)
    day_frame.grid(row = 2, columnspan = 3)

    #Display window
    window.mainloop()