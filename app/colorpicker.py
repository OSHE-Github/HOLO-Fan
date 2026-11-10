import tkinter as tk
import colorsys
import re
from PIL import Image, ImageTk

class ColorSquarePicker(tk.Frame):
    def __init__(self, parent, size=300, callback=None):
        super().__init__(parent)
        self.size = size
        self.callback = callback
        
        self.canvas = tk.Canvas(self, width=size, height=size, highlightthickness=0)
        self.canvas.pack()
        
        self.color_img = self.generate_color_map()
        self.tk_img = ImageTk.PhotoImage(self.color_img, master=self.canvas)
        
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_click)

    def generate_color_map(self):
        """Generates a square image where X represents Hue and Y represents Saturation/Value"""
        img = Image.new("RGB", (self.size, self.size))
        pixels = img.load()
        
        for x in range(self.size):
            for y in range(self.size):
                hue = x / self.size

                saturation = 1.0
                value = 1.0 - (y / self.size)

                r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
                pixels[x, y] = (int(r * 255), int(g * 255), int(b * 255))
        return img

    def on_click(self, event):
        x = max(0, min(event.x, self.size - 1))
        y = max(0, min(event.y, self.size - 1))
        
        r, g, b = self.color_img.getpixel((x, y))
        hex_code = f"#{r:02x}{g:02x}{b:02x}"
        
        if self.callback:
            self.callback(hex_code)

def color_picker(color, parent=None):
    root = tk.Toplevel(parent) if parent is not None else tk.Tk()
    root.title("Color Picker")
    root.geometry("400x500")
    selected_color = color.lower()

    def update_background(hex_color):
        nonlocal selected_color
        selected_color = hex_color.lower()
        root.config(bg=selected_color)
        if color_entry.get() != selected_color:
            color_entry.delete(0, tk.END)
            color_entry.insert(0, selected_color)

    def apply_entry_color(event=None):
        entered_color = color_entry.get().strip()
        if not re.fullmatch(r"#?[0-9a-fA-F]{6}", entered_color):
            return

        hex_color = entered_color if entered_color.startswith("#") else f"#{entered_color}"
        update_background(hex_color.lower())

    color_label = tk.Label(root, text="Selected color:", font=("Arial", 12), pady=10, bg="white", fg="black")
    color_label.pack()

    color_entry = tk.Entry(root, width=12, justify="center", font=("Arial", 12))
    color_entry.insert(0, color)
    color_entry.pack()
    color_entry.bind("<KeyRelease>", apply_entry_color)
    color_entry.bind("<Return>", apply_entry_color)
    update_background(color)

    picker = ColorSquarePicker(root, size=300, callback=update_background)
    picker.pack(pady=10)

    tk.Button(root, text="Done", command=root.destroy).pack(pady=(0, 10))

    root.wait_window()
    return selected_color
