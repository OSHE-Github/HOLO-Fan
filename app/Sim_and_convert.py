
import math
import time

import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

import var


def convert():
    var.num_blades = int(var.blades_num.get())
    var.num_empty_leds = int(var.empty_leds_num.get())
    var.num_rpm = int(var.RPM_value.get())
    var.num_blades_sim = var.num_rpm // 100 * 4
    var.num_led = int(var.led_num.get())
    var.num_vector = int(var.vector_num.get())# - int(var.vector_num.get()) % var.num_blades
    
    var.cOptions.destroy()
    var.cOptions = None

    pixel_spacing = (var.size + 1) / var.num_led / 2
    for vector_index in range(1, var.num_vector + 1):
        angle = 360.0 / var.num_vector * vector_index
        angle_rad = math.radians(angle)

        for led_index in range(1, var.num_led + 1):
            length = pixel_spacing * led_index
            x = int(length * math.sin(angle_rad) + var.size / 2) - 1
            y = int(length * math.cos(angle_rad) + var.size / 2) - 1
            var.vector_image[vector_index][led_index] = var.cv_resized_img[x, y]

    buildSim()
    drawSim(True)

# Draws a image of all vectors created
def drawStillSim():
    var.img.put("black", to=(0, 0, var.size, var.size))
    pixel_spacing = var.size / (var.num_led + var.num_empty_leds) / 2

    for vector_index in range(1, var.num_vector + 1):
        angle = 360.0 / var.num_vector * vector_index - 90
        angle_rad = math.radians(angle)

        for led_index in range(1, var.num_led + var.num_empty_leds + 1):
            length = pixel_spacing * led_index
            x = int(length * math.sin(angle_rad) * -1 + var.size / 2)
            y = int(length * math.cos(angle_rad) + var.size / 2)

            color = var.vector_image[vector_index][led_index]
            color_hex = "#" + hex((color[2] << 16) + (color[1] << 8) + color[0])[2:]
            if led_index <= var.num_empty_leds or color_hex == "#0":
                color_hex = "#000000"

            var.img.put(
                color_hex,
                to=(x, y, int(x + pixel_spacing), int(y + pixel_spacing)),
            )


# returns numpy array of one blade in location
def drawVectors(vector_index):
    if var.num_vector <= 0 or var.num_led <= 0:
        raise RuntimeError("Convert an image before drawing vectors.")

    if not isinstance(vector_index, int) or isinstance(vector_index, bool):
        raise TypeError("vector_index must be an integer.")
    if not 0 <= vector_index <= var.num_vector:
        raise ValueError(f"Vector number must be between 0 and {var.num_vector}.")

    pixels = np.zeros((var.size, var.size, 3), dtype=np.uint8)
    pixel_spacing = var.size / (var.num_led + var.num_empty_leds) / 2

    angle = 360.0 / var.num_vector * vector_index - 90
    angle_rad = math.radians(angle)

    for led_index in range(1, var.num_led + var.num_empty_leds + 1):
        length = pixel_spacing * led_index
        x = int(length * math.sin(angle_rad) * -1 + var.size / 2)
        y = int(length * math.cos(angle_rad) + var.size / 2)
        x_end = int(x + pixel_spacing)
        y_end = int(y + pixel_spacing)

        color_rgb = var.vector_image[vector_index][led_index][::-1]
        if led_index <= var.num_empty_leds:
            color_rgb = (0, 0, 0)
        pixels[y:y_end, x:x_end] = color_rgb
        


    return pixels

# Builds the simulation images for the fan based on the current vector configuration.
def buildSim():
    if var.animation_after_id is not None:
        var.root.after_cancel(var.animation_after_id)
        var.animation_after_id = None

    progress_window = tk.Toplevel(var.root)
    progress_window.title("Building simulation")
    progress_window.resizable(False, False)
    progress_window.transient(var.root)
    progress_window.grab_set()
    progress_window.attributes("-topmost", True)

    ttk.Label(
        progress_window,
        text="Building simulation. Please wait...",
        padding=12,
    ).grid(row=0, column=0, padx=20, pady=(16, 8))
    progress_bar = ttk.Progressbar(
        progress_window,
        mode="determinate",
        length=300,
    )
    progress_bar.grid(row=1, column=0, padx=20, pady=(0, 16))
    total_frames = (var.num_vector + 1) // var.num_blades
    progress_bar["maximum"] = total_frames
    progress_window.update_idletasks()
    progress_window.update()

    try:
        var.list_of_images = []
        for vector_index in range(1, total_frames):
            image = np.zeros((var.size, var.size, 3), dtype=np.uint8)
            for blade_index in range(var.num_blades):
                for blade_offset in range(var.num_blades_sim // var.num_blades, 0, -1):
                    index = vector_index + var.num_vector // var.num_blades * blade_index + blade_offset
                    if index >= var.num_vector:
                        index -= var.num_vector
                    image = image | drawVectors(index)
            var.list_of_images.append(
                ImageTk.PhotoImage(Image.fromarray(image), master=var.root)
            )
            progress_bar["value"] = vector_index
            progress_window.update_idletasks()
    finally:
        progress_bar["value"] = total_frames
        progress_window.update_idletasks()
        progress_window.destroy()
        var.motor_angle = -1
        var.simulation_start_time = time.perf_counter()
        var.fps_window_start = var.simulation_start_time
        var.fps_frame_count = 0

# Draws the simulation on the canvas, updating the image based on the current motor angle.
# also handles drawing a still image if the Still parameter is set to True.
def drawSim(Still=False):
    if not var.list_of_images:
        return

    if Still:
        if var.animation_after_id is not None:
            var.root.after_cancel(var.animation_after_id)
            var.animation_after_id = None
        drawStillSim()
        if var.canvas is not None and var.canvas_image is not None:
            var.canvas.itemconfigure(var.canvas_image, image=var.img)
        return

    current_time = time.perf_counter()
    elapsed_time = current_time - var.simulation_start_time
    frame_index = (int(elapsed_time * var.num_rpm / 60 * var.num_vector // var.num_blades) % (var.num_vector // var.num_blades) - 1)
    if frame_index != var.motor_angle:
        var.motor_angle = frame_index
        var.canvas.itemconfigure(var.canvas_image, image=var.list_of_images[frame_index])
        var.fps_frame_count += 1

    fps_elapsed = current_time - var.fps_window_start
    if fps_elapsed >= 0.5:
        displayed_fps = var.fps_frame_count / fps_elapsed
        var.fps_label.configure(
            text=f"RPM: {var.num_rpm}    FPS: {displayed_fps:.1f}"
        )
        var.fps_frame_count = 0
        var.fps_window_start = current_time

    var.animation_after_id = var.root.after(1, drawSim)
