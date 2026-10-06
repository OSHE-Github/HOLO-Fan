
import math
import time

import cv2
import numpy as np
from PIL import Image, ImageTk

import var


def convert():
    var.num_rpm = int(var.RPM_value.get())
    var.num_blades = var.num_rpm // 100 * 4
    var.num_led = int(var.led_num.get())
    var.num_vector = int(var.vector_num.get()) - int(var.vector_num.get()) % var.num_blades

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


def drawStillSim():
    var.img.put("black", to=(0, 0, var.size, var.size))
    pixel_spacing = var.size / var.num_led / 2

    for vector_index in range(1, var.num_vector + 1):
        angle = 360.0 / var.num_vector * vector_index - 90
        angle_rad = math.radians(angle)

        for led_index in range(1, var.num_led + 1):
            length = pixel_spacing * led_index
            x = int(length * math.sin(angle_rad) * -1 + var.size / 2)
            y = int(length * math.cos(angle_rad) + var.size / 2)

            color = var.vector_image[vector_index][led_index]
            color_hex = "#" + hex(
                (color[2] << 16) + (color[1] << 8) + color[0]
            )[2:]
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
    pixel_spacing = var.size / var.num_led / 2

    angle = 360.0 / var.num_vector * vector_index - 90
    angle_rad = math.radians(angle)

    for led_index in range(1, var.num_led + 1):
        length = pixel_spacing * led_index
        x = int(length * math.sin(angle_rad) * -1 + var.size / 2)
        y = int(length * math.cos(angle_rad) + var.size / 2)
        x_end = int(x + pixel_spacing)
        y_end = int(y + pixel_spacing)

        color_rgb = var.vector_image[vector_index][led_index][::-1]
        pixels[y:y_end, x:x_end] = color_rgb

    return pixels


def buildSim():
    if var.animation_after_id is not None:
        var.root.after_cancel(var.animation_after_id)
        var.animation_after_id = None

    var.list_of_images = []
    for vector_index in range(1, (var.num_vector + 1) // var.num_blades):
        image = np.zeros((var.size, var.size, 3), dtype=np.uint8)
        for blade_index in range(var.num_blades):
            image = image | drawVectors(
                vector_index + var.num_vector // var.num_blades * blade_index
            )
        var.list_of_images.append(
            ImageTk.PhotoImage(Image.fromarray(image), master=var.root)
        )
    var.motor_angle = -1
    var.simulation_start_time = time.perf_counter()
    var.fps_window_start = var.simulation_start_time
    var.fps_frame_count = 0


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
    frame_index = (
        int(elapsed_time * var.num_rpm / 60 * var.num_vector // var.num_blades)
        % (var.num_vector // var.num_blades)
        - 1
    )

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
