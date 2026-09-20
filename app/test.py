import cv2
import math
import time
import os
import sys
import numpy as np
from tkinter import *
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from PIL import Image, ImageTk

# windos
cOptions = None

#image
vector_image = np.zeros((1000, 1000, 3), dtype=int)
cv_resized_img = None

#objects
led_num = None
vector_num = None
num_vector = 0
num_led = 0

def fileImage():

    global cv_resized_img

    image_file_path = filedialog.askopenfilename(
        initialdir=os.path.expanduser("~"),
        title="Select a File", 
        filetypes=(("Image files", "*.JPEG *.png *JPG"), ("All files", "*.*"))
    )

    original_img = Image.open(image_file_path) 
    cv_image = cv2.imread(image_file_path)

    dimensions = (1001, 1001)
    resized_img = original_img.resize(dimensions) 
    cv_resized_img = cv2.resize(cv_image, dimensions)

    tk_photo = ImageTk.PhotoImage(resized_img)

    image_label = ttk.Label(root, image=tk_photo)
    image_label.image = tk_photo 
    
    image_label.grid(column= 10, row=4)


def convertOptions():

    global cOptions 
    global led_num
    global vector_num
    cOptions = Tk()
    cOptions.geometry("600x400")
    frm = ttk.Frame(cOptions, padding=30)
    frm.grid()
    ttk.Button(frm, text = "convert", command=convert).grid(column = 0, row = 5)
    ttk.Button(frm, text = "cancel", command=cOptions.destroy).grid(column = 1, row = 5)
    led_num = ttk.Entry(frm, width=30)
    led_num.grid(column = 1, row = 1)
    ttk.Label(frm, text="Number of pixles: ").grid(column = 0, row = 1)
    vector_num = ttk.Entry(frm, width=30)
    vector_num.grid(column = 1, row = 2)
    ttk.Label(frm, text="Number of vectors: ").grid(column = 0, row = 2)

    cOptions.mainloop()

def convert():
    global cOptions
    global led_num
    global vector_num
    global cv_resized_img
    global vector_image
    global num_led
    global num_vector

    num_led = int(led_num.get())
    num_vector = int(vector_num.get())
    cOptions.destroy()
    cOptions = None

    # prosessing?

    pix_spasing = 1001 / num_led / 2

    for i in range(1, num_vector + 1):
        angle = 360.0/num_vector*i
        # Convert degrees to radians
        angle_rad = math.radians(angle)   

        for j in range(1, num_led + 1):

            # Calculate coordinates (0° = Up, clockwise)
            lenght = pix_spasing * j
            x = int(lenght * math.sin(angle_rad)) + 500
            y = int(lenght * math.cos(angle_rad)) + 500
            # print(f"{x}, {y}")
            vector_image[i][j] = getpixel(x, y)
            # print(vector_image[i][j])
    drawSim()

def getpixel(x, y):

    global cv_resized_img

    return cv_resized_img[x,y]


def drawSim():
    img.put("black", to=(0, 0, 1000, 1000))
    global led_num
    global vector_num
    global vector_image

    pix_spasing = 1000 / num_led / 2
    for i in range(1, num_vector + 1):
        angle = 360.0/num_vector*i - 90
        # Convert degrees to radians
        angle_rad = math.radians(angle)

        for j in range(1, num_led + 1):

            # Calculate coordinates (0° = Up, clockwise)

            lenght = pix_spasing * j
            x = int(lenght * math.sin(angle_rad)) * -1 + 500
            y = int(lenght * math.cos(angle_rad)) + 500

            color = '#' + hex((vector_image[i][j][2] << 16) + (vector_image[i][j][1] << 8) + vector_image[i][j][0])[2:]
            img.put(color, to=(x, y, int(x+pix_spasing), int(y+pix_spasing)))
            


    # img.put("#FF0000", to=(10,10, 990, 990))  # Red pixel at center


root = Tk()
root.geometry("1600x1000")
if sys.platform.startswith("win"):
    root.state("zoomed")  # Windows maximized
elif sys.platform.startswith("linux"):
    root.attributes("-zoomed", True)  # Linux maximized
else:
    # macOS / general fallback (fullscreen)
    root.attributes("-fullscreen", True)

frm = ttk.Frame(root, padding=30)
frm.grid()
ttk.Button(frm, text = "load image", command=fileImage).grid(column = 1, row = 0)
ttk.Button(frm, text = "convert image", command=convertOptions).grid(column = 2, row = 0)
ttk.Button(frm, text="Quit", command=root.destroy).grid(column=0, row=0)

# simulation 
canvas = tk.Canvas(root, width=1000, height=1000, bg="black")
canvas.grid(column=40, row=4)

# Create a PhotoImage buffer
img = tk.PhotoImage(width=1000, height=1000)
canvas.create_image((0, 0), image=img, anchor=tk.NW)

# drawSim()


root.mainloop()
