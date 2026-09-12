import os
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from PIL import Image, ImageTk



def fileImage():
    print("test")

    image_file_path = filedialog.askopenfilename(
        initialdir=os.path.expanduser("~"),
        title="Select a File", 
        filetypes=(("Image files", "*.JPEG *.png *JPG"), ("All files", "*.*"))
    )


    original_img = Image.open(image_file_path) 
    
    # Resize the image to fit your layout (Width, Height)
    resized_img = original_img.resize((800, 600)) 
    
    # Convert the Pillow image into a Tkinter-compatible PhotoImage object
    tk_photo = ImageTk.PhotoImage(resized_img)

    # 3. Display the image in a Label widget
    image_label = ttk.Label(root, image=tk_photo)
    
    # CRITICAL: Keep a reference to the image object to prevent garbage collection
    image_label.image = tk_photo 
    
    image_label.grid(column= 10, row=4)


root = Tk()
# root.attributes("-fullscreen", True) # Full screen
root.state("zoomed")  # Windows expannded view
frm = ttk.Frame(root, padding=30)
frm.grid()
ttk.Button(frm, text = "load image", command=fileImage).grid(column = 1, row = 0)
ttk.Button(frm, text="Quit", command=root.destroy).grid(column=0, row=0)
root.mainloop()
