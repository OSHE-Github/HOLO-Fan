import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageTk

import colorpicker
import var

def setup(root):
    global drawing_image, drawing_draw
    drawing_image = Image.new("RGB", (var.size + 1, var.size + 1), "black")
    drawing_draw = ImageDraw.Draw(drawing_image)
    var.drawing_active = True
    dead_zone()

    var.image_canvas.bind("<Button-1>", start_paint)
    var.image_canvas.bind("<B1-Motion>", paint)
    var.image_canvas.bind("<ButtonRelease-1>", reset)
    
    # Add a canvas control
    var.canvas_buttons = tk.Frame(root, padx=30, pady=30)
    var.canvas_buttons.grid(column=0, row=6, columnspan=1, pady=12)

    value_label = ttk.Label(var.canvas_buttons, text="Pen Size:")
    value_label.grid(column=4, row=0)

    var.slider = tk.Scale(var.canvas_buttons, from_=1, to=100, orient="horizontal")  
    var.slider.grid(column=5, row=0, pady=5)
    var.slider.set(30)

    clear_btn = tk.Button(var.canvas_buttons, text="Clear Canvas", command=clear_canvas)
    clear_btn.grid(column=0, row=0, columnspan=2, pady=5)

    save_btn = tk.Button(var.canvas_buttons, text="Save Drawing", command=save_drawing)
    save_btn.grid(column=2, row=0, columnspan=2, pady=5)

    color_buttons = []
    var.color_names = ["#ff0000", "#0000ff", "#00ff00", "#ffff00", "#000000", "#ffffff"]
    for i in range(6):
        color=var.color_names[i]
        color_buttons.append(tk.Button(
            var.canvas_buttons,
            text="Color",
            relief=tk.RAISED,
            command=lambda i=i: change_color(color_buttons[i], var.color_names[i],i),
            bg=color,
            activebackground=color,
            fg=color,
            activeforeground=color,
            borderwidth=0 if color != var.color_names[5] else 5,
        ))
        
        color_buttons[i].grid(column=i, row=1, pady=5)

    var.old_color_button = color_buttons[5]  # Set the initial old color button to white
    var.current_color = var.color_names[5]


def start_paint(event):
    var.last_x, var.last_y = event.x, event.y
    pen_size = var.slider.get()
    radius = pen_size / 2
    var.image_canvas.create_oval(
        event.x - radius,
        event.y - radius,
        event.x + radius,
        event.y + radius,
        fill=var.current_color,
        outline=var.current_color,
        tags=("drawing",),
    )
    var.image_canvas.tag_raise("mask")
    drawing_draw.ellipse(
        (event.x - radius, event.y - radius, event.x + radius, event.y + radius),
        fill=var.current_color,
    )


def paint(event):
    if var.last_x is None or var.last_y is None:
        return

    # Draw a line from the last tracked position to the current mouse position
    var.image_canvas.create_line(
        var.last_x, var.last_y, event.x, event.y,
        fill=var.current_color, width=var.slider.get(), capstyle=tk.ROUND, smooth=True,
        tags=("drawing",),
    )
    var.image_canvas.tag_raise("mask")
    drawing_draw.line(
        (var.last_x, var.last_y, event.x, event.y),
        fill=var.current_color,
        width=var.slider.get(),
    )
    
    # Update the last coordinates to current position
    var.last_x, var.last_y = event.x, event.y

def reset(event):
    # Reset coordinates when mouse button is released to start a new line
    var.last_x = None
    var.last_y = None

def clear_canvas():
    global drawing_image, drawing_draw
    var.image_canvas.delete("drawing")
    drawing_image = Image.new("RGB", (var.size + 1, var.size + 1), "black")
    drawing_draw = ImageDraw.Draw(drawing_image)
    dead_zone()

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

def dead_zone():
    var.image_canvas.delete("mask")
    stepSize = var.size / (var.num_empty_leds + var.num_led) * var.num_empty_leds/2
    mask_img = Image.new("RGBA", (var.size+1, var.size+1), "#D9D9D9FF")
    draw = ImageDraw.Draw(mask_img)
    draw.ellipse((0, 0, var.size, var.size), fill=(0, 0, 0, 0))
    draw.ellipse((var.size/2 - stepSize, var.size/2 - stepSize, var.size/2 + stepSize, var.size/2 + stepSize), fill="#D9D9D9FF")
    tk_mask = ImageTk.PhotoImage(mask_img, master=var.root)
    var.image_canvas.create_image(0, 0, image=tk_mask, anchor="nw", state="disabled", tags=("mask",))
    var.image_canvas.image = tk_mask

def change_color(button,color,index):
    if var.old_color_button == button:
        var.current_color = colorpicker.color_picker(color, parent=var.root)
        var.color_names[index] = var.current_color
        button.config(bg=var.current_color, activebackground=var.current_color, fg=var.current_color, activeforeground=var.current_color)
    else:
        var.current_color = color
        button.config(relief=tk.SUNKEN, borderwidth=5)
        var.old_color_button.config(relief=tk.RAISED, borderwidth=0)
        var.old_color_button = button
