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
        filetypes=(("Image files", "*.JPEG *.png *JPG"), ("All files", "*.*"))
    )

    original_img = Image.open(image_file_path)
    cv_image = cv2.imread(image_file_path)

    dimensions = (var.size + 1, var.size + 1)
    resized_img = original_img.resize(dimensions)
    var.cv_resized_img = cv2.resize(cv_image, dimensions)

    tk_photo = ImageTk.PhotoImage(resized_img)

    image_label = ttk.Label(var.root, image=tk_photo)
    image_label.image = tk_photo
    image_label.grid(column=10, row=4)

def convertOptions():
    var.cOptions = Tk()
    var.cOptions.geometry("600x400")
    frm = ttk.Frame(var.cOptions, padding=30)
    frm.grid()
    ttk.Button(frm, text="convert", command=Sim_and_convert.convert).grid(column=0, row=5)
    ttk.Button(frm, text="cancel", command=var.cOptions.destroy).grid(column=1, row=5)
    var.led_num = ttk.Entry(frm, width=30)
    var.led_num.grid(column=1, row=1)
    ttk.Label(frm, text="Number of pixles: ").grid(column=0, row=1)
    var.vector_num = ttk.Entry(frm, width=30)
    var.vector_num.grid(column=1, row=2)
    ttk.Label(frm, text="Number of vectors: ").grid(column=0, row=2)
    var.RPM_value = ttk.Entry(frm, width=30)
    var.RPM_value.grid(column=1, row=3)
    ttk.Label(frm, text="RPM: ").grid(column=0, row=3)

    var.cOptions.mainloop()

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


var.root = Tk()
var.root.geometry("1600x1000")
if sys.platform.startswith("win"):
    var.root.state("zoomed")
elif sys.platform.startswith("linux"):
    var.root.attributes("-zoomed", True)
else:
    var.root.attributes("-fullscreen", True)

frm = ttk.Frame(var.root, padding=30)
frm.grid()
ttk.Button(frm, text="load image", command=fileImage).grid(column=1, row=0)
ttk.Button(frm, text="convert image", command=convertOptions).grid(column=2, row=0)
ttk.Button(frm, text="Quit", command=var.root.destroy).grid(column=0, row=0)

var.sim_button = ttk.Button(frm, text="Start sim", command=lambda: moveSim(Still=False))
var.sim_button.grid(column=41, row=5)

var.canvas = tk.Canvas(var.root, width=var.size, height=var.size, bg="black")
var.canvas.grid(column=40, row=4)
var.fps_label = ttk.Label(var.root, text=f"RPM: {var.num_rpm}    FPS: 0.0")
var.fps_label.grid(column=41, row=4, sticky=tk.N, padx=(12, 0))

var.img = tk.PhotoImage(width=var.size, height=var.size)
var.canvas_image = var.canvas.create_image((0, 0), image=var.img, anchor=tk.NW)

var.root.mainloop()
