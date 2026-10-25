import os
import sys
import time

import cv2
import tkinter as tk
from tkinter import Tk, filedialog, ttk
from PIL import Image, ImageTk

import Sim_and_convert
import var


def fileImage():
    image_file_path = filedialog.askopenfilename(
        initialdir=os.path.expanduser("~"),
        title="Select a File", 
        filetypes=(("Image files", "*.JPEG *.png *.JPG *.jpeg *.PNG *.jpg"), ("All files", "*.*"))
    )

    original_img = Image.open(image_file_path)
    cv_image = cv2.imread(image_file_path)

    dimensions = (var.size + 1, var.size + 1)
    resized_img = original_img.resize(dimensions)
    var.cv_resized_img = cv2.resize(cv_image, dimensions)

    tk_photo = ImageTk.PhotoImage(resized_img)

    image_label = ttk.Label(var.root, image=tk_photo)
    image_label.image = tk_photo
    image_label.grid(column=0, row=4)

def convertOptions():
    var.cOptions = tk.Toplevel(var.root)
    var.cOptions.geometry("800x200")
    var.cOptions.title("Convert Options")
    frm = ttk.Frame(var.cOptions, padding=30)
    frm.grid()
    ttk.Button(frm, text="convert", command=Sim_and_convert.convert).grid(column=0, row=6)
    ttk.Button(frm, text="cancel", command=var.cOptions.destroy).grid(column=1, row=6)
    var.vector_num = ttk.Entry(frm, width=30)
    var.vector_num.grid(column=1, row=4)
    var.vector_num.insert(0, str(var.num_vector))
    ttk.Label(frm, text="Number of vectors: ").grid(column=0, row=4)
    var.RPM_value = ttk.Entry(frm, width=30)
    var.RPM_value.grid(column=1, row=5)
    var.RPM_value.insert(0, str(var.num_rpm))
    ttk.Label(frm, text="RPM: ").grid(column=0, row=5)

def FanSettings():
    var.fan_settings_popup = tk.Toplevel(var.root)
    var.fan_settings_popup.geometry("800x300")
    var.fan_settings_popup.title("Fan Settings")

    frm = ttk.Frame(var.fan_settings_popup, padding=30)
    frm.grid()

    button_frame = ttk.Frame(frm)
    button_frame.grid(column=0, row=6, columnspan=2, pady=(12, 0))
    ttk.Button(button_frame, text="Save", command=Sim_and_convert.saveSettings).grid(column=0, row=0)
    ttk.Button(button_frame, text="Cancel", command=var.fan_settings_popup.destroy).grid(column=1, row=0)
    ttk.Button(button_frame, text="Pull settings from fan", command=getFanInfo).grid(column=2, row=0)

    
    var.led_num = ttk.Entry(frm, width=30)
    var.led_num.grid(column=1, row=1)
    var.led_num.insert(0, str(var.num_led))
    ttk.Label(frm, text="Number of pixels: ").grid(column=0, row=1)
    var.blades_num = ttk.Entry(frm, width=30)
    var.blades_num.grid(column=1, row=2)
    var.blades_num.insert(0, str(var.num_blades))
    ttk.Label(frm, text="Number of blades: ").grid(column=0, row=2)
    var.empty_leds_num = ttk.Entry(frm, width=30)
    var.empty_leds_num.grid(column=1, row=3)
    var.empty_leds_num.insert(0, str(var.num_empty_leds))
    ttk.Label(frm, text="Size of empty center: ").grid(column=0, row=3)
    var.ip_address_input = ttk.Entry(frm, width=30)
    var.ip_address_input.grid(column=1, row=4)
    var.ip_address_input.insert(0, str(var.IP_address))
    ttk.Label(frm, text="IP Address: ").grid(column=0, row=4)



def moveSim(Still = False):
    
    if Still:
        var.sim_button.configure(text="Start sim", command=lambda: moveSim(Still = False))
        Sim_and_convert.drawSim(Still)
        return

    var.sim_button.configure(text="Stop sim", command=lambda: moveSim(Still=True))
    var.simulation_start_time = time.perf_counter()
    var.fps_window_start = var.simulation_start_time
    var.fps_frame_count = 0
    var.motor_angle = -1
    Sim_and_convert.drawSim(Still)

def sendToFan():
    print("Sending to fan...")
    print("not implemented yet")
    var.fan_popup = tk.Toplevel(var.root)
    var.fan_popup.geometry("400x200")
    var.fan_popup.title("")
    var.fan_popup.columnconfigure(0, weight=1)
    var.fan_popup.rowconfigure(0, weight=1)
    frm = ttk.Frame(var.fan_popup, padding=20)
    frm.grid(row=0, column=0, sticky="nsew")
    frm.columnconfigure(0, weight=1)
    frm.rowconfigure(0, weight=1)
    var.fan_popup.resizable(False, False)
    var.fan_popup.transient(var.root)
    var.fan_popup.attributes("-topmost", True)

    ttk.Label(
        frm,
        text="Image sent to fan.",
        padding=12,
    ).grid(row=0, column=0, sticky="nsew")

    ttk.Button(frm, text="Close", command=var.fan_popup.destroy).grid(row=1, column=0, pady=(12, 0))

def getFanInfo():
    # pull from fan API
    var.blades_num.delete(0, tk.END)
    var.led_num.delete(0, tk.END)
    var.empty_leds_num.delete(0, tk.END)
    var.blades_num.insert(0, str(4))
    var.led_num.insert(0, str(25))
    var.empty_leds_num.insert(0, str(0))

def updateFanInfo():
    # pull from fan API
    var.fan_info.configure(text=f"Fan RPM: {var.fan_rpm}   IP Address: {var.IP_address}")
    var.fan_pull = var.root.after(100, updateFanInfo) # update every 0.1 seconds

var.root = Tk()
var.root.geometry("1600x1000")
var.root.title("HOLO Fan Desktop")
if sys.platform.startswith("win"):
    var.root.state("zoomed")
elif sys.platform.startswith("linux"):
    var.root.attributes("-zoomed", True)
else:
    var.root.attributes("-fullscreen", True)

frm = ttk.Frame(var.root, padding=30)
frm.grid()
ttk.Button(frm, text="load image", command=fileImage).grid(column=1, row=0)
ttk.Button(frm, text="convert image", command=convertOptions).grid(column=3, row=0)
ttk.Button(frm, text="Quit", command=var.root.destroy).grid(column=0, row=0)
ttk.Button(frm, text="Send to Fan", command=sendToFan).grid(column=4, row=0)
ttk.Button(frm, text="Fan Settings", command=FanSettings).grid(column=2, row=0)


tk.Canvas(var.root, width=var.size, height=var.size, bg="black").grid(column=0, row=4)
var.canvas = tk.Canvas(var.root, width=var.size, height=var.size, bg="black")
var.canvas.grid(column=1, row=4)
status_frame = ttk.Frame(var.root)
status_frame.grid(column=6, row=4, sticky=tk.N, padx=(12, 0))
var.fps_label = ttk.Label(status_frame, text=f"Simulation RPM: {var.num_rpm}   Simulation FPS: 0.0")
var.fps_label.grid(column=0, row=0, sticky=tk.W)

var.fan_info = ttk.Label(status_frame, text=f"Fan RPM: {var.fan_rpm}   IP Address: {var.IP_address}")
var.fan_info.grid(column=0, row=1, sticky=tk.W, pady=(6, 0))

var.sim_button = ttk.Button(frm, text="Start sim", command=lambda: moveSim(Still=False))
var.sim_button.grid(column=5, row=0)

var.img = tk.PhotoImage(width=var.size, height=var.size)
var.canvas_image = var.canvas.create_image((0, 0), image=var.img, anchor=tk.NW)
updateFanInfo()

var.root.mainloop()
