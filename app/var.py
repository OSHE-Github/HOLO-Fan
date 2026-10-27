
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


# Shared application state
root = None
canvas = None
image_canvas = None
img = None
cOptions = None
fan_popup = None
fan_settings_popup = None
size = 1000
sim_button = None

# image
vector_image = np.zeros((size, size, 3), dtype=int)
cv_resized_img = None

# objects
led_num = None
vector_num = None
blades_num = None
ip_address_input = None

# simulation
num_vector = 100
num_rpm = 1000
num_blades_sim = 0
motor_angle = 0
list_of_images = []
still_image = None
canvas_image = None
simulation_start_time = 0.0
fps_window_start = 0.0
fps_frame_count = 0
animation_after_id = None


# fan comunication
fan_info = None
fan_rpm = 0
fan_pull = None

# fan settings
num_led = 25
num_empty_leds = 0
num_blades = 4
IP_address = "0.0.0.0"

# drawing
last_x = None
last_y = None
current_color = "white"
old_color_button = None
canvas_buttons = None
slider = None
drawing_active = False