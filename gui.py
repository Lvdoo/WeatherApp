from tkinter import *
import weather_api
import utils
from PIL import Image, ImageTk

def display_weather() :

    #Create a window 
    window = Tk()

    #Personalize window 
    window.title("WeatherApp")
    window.geometry("1080x720")
    window.minsize(1080,720)
    window.config(bg = "#517DCA")

    #Interdace in 3 frames
    top_frame = Frame(window, bg = "#517DCA")
    main_frame = Frame(window, bg = "#517DCA")
    infos_frame = Frame(window, bg = "#517DCA")

    #Labels and inputs
    label_city = Label(top_frame, text = "City : ", font = ('Helvetica', 20), bg = "#517DCA", fg = "white")
    label_unit = Label(top_frame, text = "Unit : ", font = ('Helvetica', 20), bg = "#517DCA", fg = "white")
    city_input = Entry(top_frame, font = ('Helvetica', 20), bg = "#7895C7", fg = "white")
    unit_input = Entry(top_frame, font = ('Helvetica', 20), bg = "#7895C7", fg = "white")
    label_temperature = Label(main_frame, text = "", bg = "#517DCA", font = ('Helvetica', 60), fg = "white")
    label_temp_felt = Label(main_frame, text = "", bg = "#517DCA", font = ('Helvetica', 20), fg = "white")
    label_max_temp = Label(main_frame, text = "", bg = "#517DCA", font = ('Helvetica', 15), fg = "white")
    label_min_temp = Label(main_frame, text = "", bg = "#517DCA", font = ('Helvetica', 15), fg = "white")
    label_humidity = Label(infos_frame, text = "", bg = "#517DCA", font = ('Helvetica', 15), fg = "white")
    label_wind_direction = Label(infos_frame, text = "", bg = "#517DCA", font = ('Helvetica', 15), fg = "white")
    label_wind_speed = Label(infos_frame, text = "", bg = "#517DCA", font = ('Helvetica', 15), fg = "white")
    label_clouds = Label(infos_frame, text = "", bg = "#517DCA", font = ('Helvetica', 15), fg = "white")

    #Images
    max_temp_img = Image.open("icons/fleche_haut.png").resize((20,17))
    max_temp_image = ImageTk.PhotoImage(max_temp_img)
    label_max_temp_image = Label(main_frame, image = "", bg = "#517DCA")
    min_temp_img = Image.open("icons/fleche_bas.png").resize((20,17))
    min_temp_image = ImageTk.PhotoImage(min_temp_img)
    label_min_temp_image = Label(main_frame, image = "", bg = "#517DCA")

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
        wind_speed = infos['wind_speed']
        clouds = infos['clouds']

        #Update labels 
        label_temperature.config(text = f"{temperature}{symbol}")
        label_temp_felt.config(text = f"Temperature felt : {temp_felt}{symbol}")
        label_max_temp.config(text = f"{max_temp}{symbol}")
        label_min_temp.config(text = f"{min_temp}{symbol}")
        label_humidity.config(text = f"Humidity : {humidity}%")
        label_wind_direction.config(text = f"Wind Direction : {wind_direction}")
        label_wind_speed.config(text = f"Wind Speed : {wind_speed}")
        label_clouds.config(text = f"Clouds : {clouds}")

        #Udpate images
        label_max_temp_image.config(image = max_temp_image)
        label_max_temp_image.image = max_temp_image
        label_max_temp_image.grid(row = 2, column = 1, padx = padx_fleche_haut, pady = 5) 
        label_min_temp_image.config(image = min_temp_image)
        label_min_temp_image.image = min_temp_image
        label_min_temp_image.grid(row = 2, column = 1, padx = padx_fleche_bas, pady = 5) 
        
        
    #Search button to display weather
    search_button = Button(top_frame, text = "Search", font = ('Helvetica', 20), bg = "white", fg = "#4065A4", command = display_infos)

    #Labels of top_frame
    label_city.grid(row = 0, column = 0, sticky = "e", padx = 5, pady = (20,5))
    city_input.grid(row = 0, column = 1, padx = 10, pady = (20,5))
    label_unit.grid(row = 1, column = 0, sticky = "e", padx = 5, pady = 5)
    unit_input.grid(row = 1, column = 1, padx=10, pady = 5)
    search_button.grid(row = 2, column = 0, columnspan = 2, pady=5, sticky = EW) #columnspan permet à "search_button" de prendre 2 colonnes

    #Labels and images of main_frame
    label_temperature.grid(row = 0,column = 1, pady = (50,5))
    label_temp_felt.grid(row = 1, column = 1)
    label_max_temp.grid(row = 2, column = 1, padx = (0,120), pady = 5)
    label_min_temp.grid(row = 2, column = 1, padx = (120,0), pady = 5)

    #Labels and images of infos_frame
        
    #Display frames
    top_frame.pack()
    main_frame.pack()

    #Display window
    window.mainloop()