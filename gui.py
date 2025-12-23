from tkinter import *
import weather_api
import utils

def display_weather() :

    #Create a window 
    window = Tk()

    #Personlize window 
    window.title("WeatherApp")
    window.geometry("1080x720")
    window.minsize(1080,720)
    window.iconbitmap("icons/weather_icon.ico")
    window.config(bg = "#517DCA")

    frame = Frame(window, bg = "#4065A4")

    city_input = Entry(frame, font = ('Helvetica', 20), bg = "#7895C7", fg = "white")
    unit_input = Entry(frame, font = ('Helvetica', 20), bg = "#7895C7", fg = "white")

    def display_infos() :
        city = city_input.get().strip().capitalize()
        unit = unit_input.get().strip().lower()
        infos = weather_api.get_weather(city,unit)
        label = Label(frame, text = f" Temperature : {infos['temperature']}", bg = "#7895C7", font = ('Helvetica', 15), relief = SUNKEN)
        label.pack()

    search_button = Button(frame, text = "Search", font = ('Helvetica', 20), bg = "white", fg = "#4065A4", command = display_infos)

    city_input.pack()
    unit_input.pack()
    search_button.pack(fill = X)
    frame.pack()

    #Display window
    window.mainloop()