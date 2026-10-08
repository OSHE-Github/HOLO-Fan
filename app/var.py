
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
img = None
cOptions = None
size = 1000
sim_button = None

# image
vector_image = np.zeros((size, size, 3), dtype=int)
cv_resized_img = None

# objects
led_num = None
vector_num = None
blades_num = None

# simulation
num_vector = 0
num_led = 0
num_rpm = 0
num_blades = 4
num_blades_sim = 0
motor_angle = 0
list_of_images = []
canvas_image = None
simulation_start_time = 0.0
fps_window_start = 0.0
fps_frame_count = 0
animation_after_id = None
num_empty_leds = 0
