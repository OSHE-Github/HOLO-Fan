import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageTk

import colorpicker
import var

class Drawing():
    def __init__(self, root):

        self.root = root
        self.size = var.size
        self.num_led = var.num_led
        self.num_empty_leds = var.num_empty_leds
        self.image_canvas = var.image_canvas
        self.last_x = None
        self.last_y = None
        self.old_color_button = None
        self.canvas_buttons = None
        self.slider = None

        self.color_names = None
        self.color_names = ["#ff0000", "#0000ff", "#00ff00", "#ffff00", "#000000", "#ffffff"]
        self.current_color = self.color_names[5]  # Set the initial current color to white




        self.setup(root)


    def setup(self, root):
        global drawing_image, drawing_draw
        drawing_image = Image.new("RGB", (self.size + 1, self.size + 1), "black")
        drawing_draw = ImageDraw.Draw(drawing_image)
        var.drawing_active = True
        self.dead_zone()

        self.image_canvas.bind("<Button-1>", self.start_paint)
        self.image_canvas.bind("<B1-Motion>", self.paint)
        self.image_canvas.bind("<ButtonRelease-1>", self.reset)
        
        # Add a canvas control
        self.canvas_buttons = tk.Frame(root, padx=30, pady=30)
        self.canvas_buttons.grid(column=0, row=6, columnspan=1, pady=12)

        value_label = ttk.Label(self.canvas_buttons, text="Pen Size:")
        value_label.grid(column=4, row=0)

        self.slider = tk.Scale(self.canvas_buttons, from_=1, to=100, orient="horizontal")  
        self.slider.grid(column=5, row=0, pady=5)
        self.slider.set(30)

        clear_btn = tk.Button(self.canvas_buttons, text="Clear Canvas", command=self.clear_canvas)
        clear_btn.grid(column=0, row=0, columnspan=2, pady=5)

        save_btn = tk.Button(self.canvas_buttons, text="Save Drawing", command=self.save_drawing)
        save_btn.grid(column=2, row=0, columnspan=2, pady=5)

        color_buttons = []
        self.color_names = ["#ff0000", "#0000ff", "#00ff00", "#ffff00", "#000000", "#ffffff"]
        for i in range(6):
            color=self.color_names[i]
            color_buttons.append(tk.Button(
                self.canvas_buttons,
                text="Color",
                relief=tk.RAISED,
                command=lambda i=i: self.change_color(color_buttons[i], self.color_names[i], i),
                bg=color,
                activebackground=color,
                fg=color,
                activeforeground=color,
                borderwidth=0 if color != self.color_names[5] else 5,
            ))
            
            color_buttons[i].grid(column=i, row=1, pady=5)

        self.old_color_button = color_buttons[5]  # Set the initial old color button to white
        self.current_color = self.color_names[5]


    def start_paint(self, event):
        self.last_x, self.last_y = event.x, event.y
        pen_size = self.slider.get()
        radius = pen_size / 2
        self.image_canvas.create_oval(
            event.x - radius,
            event.y - radius,
            event.x + radius,
            event.y + radius,
            fill=self.current_color,
            outline=self.current_color,
            tags=("drawing",),
        )
        self.image_canvas.tag_raise("mask")
        drawing_draw.ellipse(
            (event.x - radius, event.y - radius, event.x + radius, event.y + radius),
            fill=self.current_color,
        )


    def paint(self, event):
        if self.last_x is None or self.last_y is None:
            return

        # Draw a line from the last tracked position to the current mouse position
        self.image_canvas.create_line(
            self.last_x, self.last_y, event.x, event.y,
            fill=self.current_color, width=self.slider.get(), capstyle=tk.ROUND, smooth=True,
            tags=("drawing",),
        )
        self.image_canvas.tag_raise("mask")
        drawing_draw.line(
            (self.last_x, self.last_y, event.x, event.y),
            fill=self.current_color,
            width=self.slider.get(),
        )
        
        # Update the last coordinates to current position
        self.last_x, self.last_y = event.x, event.y

    def reset(self, event):
        # Reset coordinates when mouse button is released to start a new line
        self.last_x = None
        self.last_y = None

    def clear_canvas(self):
        global drawing_image, drawing_draw
        self.image_canvas.delete("drawing")
        drawing_image = Image.new("RGB", (self.size + 1, self.size + 1), "black")
        drawing_draw = ImageDraw.Draw(drawing_image)
        self.dead_zone()

    def get_cv_image(self):
        image = drawing_image.resize((self.size + 1, self.size + 1))
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    def save_drawing(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png")],
        )
        if path:
            drawing_image.save(path)

    def dead_zone(self):
        self.image_canvas.delete("mask")
        stepSize = self.size / (self.num_empty_leds + self.num_led) * self.num_empty_leds/2
        mask_img = Image.new("RGBA", (self.size+1, self.size+1), "#D9D9D9FF")
        draw = ImageDraw.Draw(mask_img)
        draw.ellipse((0, 0, self.size, self.size), fill=(0, 0, 0, 0))
        draw.ellipse((self.size/2 - stepSize, self.size/2 - stepSize, self.size/2 + stepSize, self.size/2 + stepSize), fill="#D9D9D9FF")
        tk_mask = ImageTk.PhotoImage(mask_img, master=self.root)
        self.image_canvas.create_image(0, 0, image=tk_mask, anchor="nw", state="disabled", tags=("mask",))
        self.image_canvas.image = tk_mask

    def change_color(self, button, color, index):
        if self.old_color_button == button:
            self.current_color = colorpicker.color_picker(color, parent=self.root)
            self.color_names[index] = self.current_color
            button.config(bg=self.current_color, activebackground=self.current_color, fg=self.current_color, activeforeground=self.current_color)
        else:
            self.current_color = color
            button.config(relief=tk.SUNKEN, borderwidth=5)
            self.old_color_button.config(relief=tk.RAISED, borderwidth=0)
            self.old_color_button = button
    
