import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import cv2
import numpy as np
from PIL import Image, ImageDraw

import var

def setup(root):
    global drawing_image, drawing_draw
    drawing_image = Image.new("RGB", (var.size + 1, var.size + 1), "black")
    drawing_draw = ImageDraw.Draw(drawing_image)
    var.drawing_active = True

    var.image_canvas.bind("<B1-Motion>", paint)
    var.image_canvas.bind("<ButtonRelease-1>", reset)
    
    # Add a canvas control
    var.canvas_buttons = tk.Frame(root, padx=30, pady=30)
    var.canvas_buttons.grid(column=0, row=6, columnspan=1, pady=12)
    # var.canvas_buttons.configure(bg="#E3C76C")

    value_label = ttk.Label(var.canvas_buttons, text="Pen size:")
    value_label.grid(column=4, row=0)

    var.slider = tk.Scale(var.canvas_buttons, from_=1, to=100, orient="horizontal")  
    var.slider.grid(column=5, row=0, pady=5)
    var.slider.set(5)

    clear_btn = tk.Button(var.canvas_buttons, text="Clear Canvas", command=clear_canvas)
    clear_btn.grid(column=0, row=0, columnspan=2, pady=5)

    save_btn = tk.Button(var.canvas_buttons, text="Save Drawing", command=save_drawing)
    save_btn.grid(column=2, row=0, columnspan=2, pady=5)

    # color buttons
    red_btn = tk.Button(var.canvas_buttons, text="Red", relief=tk.RAISED, command=lambda: change_color(red_btn, "red"))
    red_btn.grid(column=0, row=1, pady=5)

    blue_btn = tk.Button(var.canvas_buttons, text="Blue", relief=tk.RAISED, command=lambda: change_color(blue_btn, "blue"))
    blue_btn.grid(column=1, row=1, pady=5)

    green_btn = tk.Button(var.canvas_buttons, text="Green", relief=tk.RAISED, command=lambda: change_color(green_btn, "green"))
    green_btn.grid(column=2, row=1, pady=5)

    yellow_btn = tk.Button(var.canvas_buttons, text="Yellow", relief=tk.RAISED, command=lambda: change_color(yellow_btn, "yellow"))
    yellow_btn.grid(column=3, row=1, pady=5)

    black_btn = tk.Button(var.canvas_buttons, text="Black", relief=tk.RAISED, command=lambda: change_color(black_btn, "black"))
    black_btn.grid(column=4, row=1, pady=5)

    white_btn = tk.Button(var.canvas_buttons, text="White", relief=tk.SUNKEN, command=lambda: change_color(white_btn, "white"))
    white_btn.grid(column=5, row=1, pady=5)

    var.old_color_button = white_btn
    var.current_color = "white"


def paint(event):
    # On first click, set the starting point without drawing a line
    if var.last_x is None or var.last_y is None:
        var.last_x, var.last_y = event.x, event.y
        return
        
    # Draw a line from the last tracked position to the current mouse position
    var.image_canvas.create_line(
        var.last_x, var.last_y, event.x, event.y, 
        fill=var.current_color, width=var.slider.get(), capstyle=tk.ROUND, smooth=True
    )
    drawing_draw.line((var.last_x, var.last_y, event.x, event.y),fill=var.current_color,width=var.slider.get())
    
    # Update the last coordinates to current position
    var.last_x, var.last_y = event.x, event.y

def reset(event):
    # Reset coordinates when mouse button is released to start a new line
    var.last_x = None
    var.last_y = None

def clear_canvas():
    var.image_canvas.delete("all")
    drawing_image.paste("black", (0, 0, var.size + 1, var.size + 1))

def get_cv_image():
    image = drawing_image.resize((var.size + 1, var.size + 1))
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

def save_drawing():
    path = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("PNG image", "*.png")],
    )
    if path:
        drawing_image.save(path)

def change_color(button,color):
    var.current_color = color
    button.config(relief=tk.SUNKEN)
    var.old_color_button.config(relief=tk.RAISED)
    var.old_color_button = button
