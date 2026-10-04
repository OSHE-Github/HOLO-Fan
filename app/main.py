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
size = 500
#image
vector_image = np.zeros((size, size, 3), dtype=int)
cv_resized_img = None

#objects
led_num = None
vector_num = None
RPM_value = None
num_vector = 0
num_led = 0
num_rpm = 0
# simulation
num_blades = 4
motor_angle = 0
list_of_images = []
canvas_image = None
simulation_start_time = 0.0
fps_window_start = 0.0
fps_frame_count = 0
animation_after_id = None

def fileImage():

    global cv_resized_img, size

    image_file_path = filedialog.askopenfilename(
        initialdir=os.path.expanduser("~"),
        title="Select a File", 
        filetypes=(("Image files", "*.JPEG *.png *JPG"), ("All files", "*.*"))
    )

    original_img = Image.open(image_file_path) 
    cv_image = cv2.imread(image_file_path)

    dimensions = (size+1, size+1)
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
    global RPM_value, size
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
    RPM_value = ttk.Entry(frm, width=30)
    RPM_value.grid(column = 1, row = 3)
    ttk.Label(frm, text="RPM: ").grid(column = 0, row = 3)


    cOptions.mainloop()

def convert():
    global cOptions
    global led_num
    global vector_num
    global cv_resized_img
    global vector_image
    global num_led
    global num_vector, num_blades, num_rpm, num_blades, size

    num_rpm = int(RPM_value.get())
    num_blades = num_rpm // 100 * 4
    num_led = int(led_num.get())
    num_vector = int(vector_num.get()) - int(vector_num.get()) % num_blades
    
    cOptions.destroy()
    cOptions = None

    # prosessing?

    pix_spasing = (size+1) / num_led / 2

    for i in range(1, num_vector + 1):
        angle = 360.0/num_vector*i
        # Convert degrees to radians
        angle_rad = math.radians(angle)   

        for j in range(1, num_led + 1):

            lenght = pix_spasing * j
            x = int(lenght * math.sin(angle_rad) + size/2) -1
            y = int(lenght * math.cos(angle_rad) + size/2) -1
            # print(f"{x}, {y}")
            vector_image[i][j] = getpixel(x, y)
            # print(vector_image[i][j])
    # drawStillSim()
    buildSim()
    drawSim()

def getpixel(x, y):

    global cv_resized_img

    return cv_resized_img[x,y]


def drawStillSim():
    global vector_image, size
    img.put("black", to=(0, 0, size, size))
    global led_num
    global vector_num
    

    pix_spasing = size / num_led / 2
    for i in range(1, num_vector + 1):
        angle = 360.0/num_vector*i - 90
        # Convert degrees to radians
        angle_rad = math.radians(angle)

        for j in range(1, num_led + 1):

            # Calculate coordinates (0° = Up, clockwise)

            lenght = pix_spasing * j
            x = int(lenght * math.sin(angle_rad) * -1 + size/2)
            y = int(lenght * math.cos(angle_rad) + size/2)

            color = '#' + hex((vector_image[i][j][2] << 16) + (vector_image[i][j][1] << 8) + vector_image[i][j][0])[2:]
            img.put(color, to=(x, y, int(x+pix_spasing), int(y+pix_spasing)))

# returns numpy array of one blade in location
def drawVectors(vector_index):
    global size
    if num_vector <= 0 or num_led <= 0:
        raise RuntimeError("Convert an image before drawing vectors.")

    if not isinstance(vector_index, int) or isinstance(vector_index, bool):
        raise TypeError("vector_index must be an integer.")
    if not 0 <= vector_index <= num_vector:
        raise ValueError(f"Vector number must be between 0 and {num_vector}.")

    pixels = np.zeros((size, size, 3), dtype=np.uint8)
    pixel_spacing = size / num_led / 2

    angle = 360.0 / num_vector * vector_index - 90
    angle_rad = math.radians(angle)

    for led_index in range(1, num_led + 1):
        length = pixel_spacing * led_index
        x = int(length * math.sin(angle_rad) * -1 + size/2)
        y = int(length * math.cos(angle_rad) + size/2)
        x_end = int(x + pixel_spacing)
        y_end = int(y + pixel_spacing)

        color_rgb = vector_image[vector_index][led_index][::-1]
        pixels[y:y_end, x:x_end] = color_rgb

    return pixels

def buildSim():
    global list_of_images, motor_angle, simulation_start_time, size
    global fps_window_start, fps_frame_count, animation_after_id, num_blades

    if animation_after_id is not None:
        root.after_cancel(animation_after_id)
        animation_after_id = None

    list_of_images = []
    for i in range(1, (num_vector + 1) // num_blades):
        image = np.zeros((size, size, 3), dtype=np.uint8)
        for j in range(num_blades):
            image = image | drawVectors(i + num_vector // num_blades * j)
        list_of_images.append(ImageTk.PhotoImage(Image.fromarray(image), master=root))
    motor_angle = -1
    simulation_start_time = time.perf_counter()
    fps_window_start = simulation_start_time
    fps_frame_count = 0

def drawSim():
    global motor_angle, fps_window_start, fps_frame_count, animation_after_id, num_blades,size

    if not list_of_images:
        return

    current_time = time.perf_counter()
    elapsed_time = current_time - simulation_start_time
    frame_index = int(elapsed_time * num_rpm / 60 * num_vector // num_blades) % (num_vector // num_blades) - 1
    # if frame_index >= len(list_of_images):
    #     frame_index = len(list_of_images)-1
    if frame_index != motor_angle:
        motor_angle = frame_index
        canvas.itemconfigure(canvas_image, image=list_of_images[frame_index])
        fps_frame_count += 1

    fps_elapsed = current_time - fps_window_start
    if fps_elapsed >= 0.5:
        displayed_fps = fps_frame_count / fps_elapsed
        fps_label.configure(text=f"RPM: {num_rpm}    FPS: {displayed_fps:.1f}")
        fps_frame_count = 0
        fps_window_start = current_time

    animation_after_id = root.after(1, drawSim)

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
canvas = tk.Canvas(root, width=size, height=size, bg="black")
canvas.grid(column=40, row=4)
fps_label = ttk.Label(root, text=f"RPM: {num_rpm}    FPS: 0.0")
fps_label.grid(column=41, row=4, sticky=tk.N, padx=(12, 0))

# Create a PhotoImage buffer
img = tk.PhotoImage(width=size, height=size)
canvas_image = canvas.create_image((0, 0), image=img, anchor=tk.NW)

# drawSim()


root.mainloop()
