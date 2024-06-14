import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from DtoN_GUI_troubleshooting import AnonDtoNGUI
from nnUNetGUI_woShell import nnUNetGUI4
from DCM2STLv2 import AirwaySegmenterGUI
from STLConvGUI import STLConverterGUI
from PIL import Image, ImageTk
from styles import configure_styles, BG_COLOR, FONT_FAMILY, WINDOW_HEIGHT, WINDOW_WIDTH

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    abs_path = Path(base_path) / relative_path
    return abs_path.as_posix()  # Convert to POSIX (i.e., forward-slash) format

class MainGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Airway Segmentation")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.iconbitmap(resource_path("Images/icon.ico"))
        self.configure(bg=BG_COLOR)

        self.corner_image = None  # Create an instance variable to store the corner image

        self.create_widgets()

    def create_widgets(self):
        # Main frame to hold other GUIs
        self.main_frame = tk.Frame(self, bg=BG_COLOR)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Load and place corner image
        self.load_corner_image()

        # Show home page content
        self.show_home_page()

    def load_corner_image(self):
        try:
            image_path = resource_path("Images/dent_100.ppm")
            image = Image.open(image_path)

            # Resize the image
            desired_size = (75, 75)  # Set your desired size here
            resized_image = image.resize(desired_size, Image.LANCZOS)

            # Convert to photo image
            ppm_img = ImageTk.PhotoImage(resized_image)
            self.corner_image = ppm_img  # Store the image reference

            img_label = tk.Label(self, image=ppm_img, bg=BG_COLOR)
            img_label.image = ppm_img  # Keep a reference to avoid garbage collection
            img_label.place(relx=1.0, rely=0.0, anchor="ne", x=-20, y=10)
        except Exception as e:
            print(f"Error loading corner image: {e}")

    def load_images(self):
        try:
            # Get the base directory of your Python script
            base_dir = os.path.dirname(os.path.abspath(__file__))

            # Construct the absolute paths to the image files
            nnunet_image_path = os.path.join(base_dir, "Images", "nnunet_icon2.png")
            anon_image_path = os.path.join(base_dir, "Images", "D2NConv2.png")
            stl_image_path = os.path.join(base_dir, "Images", "stl_icon2.png")
            D2S_image_path = os.path.join(base_dir, "Images", "DCM2STL.png")

            image_size = 175

            nnunet_image = Image.open(nnunet_image_path)
            nnunet_image = nnunet_image.resize((image_size, image_size), Image.LANCZOS)
            self.nnunet_photo = ImageTk.PhotoImage(nnunet_image)

            anon_image = Image.open(anon_image_path)
            anon_image = anon_image.resize((image_size, image_size), Image.LANCZOS)
            self.anon_photo = ImageTk.PhotoImage(anon_image)

            stl_image = Image.open(stl_image_path)
            stl_image = stl_image.resize((image_size, image_size), Image.LANCZOS)
            self.stl_photo = ImageTk.PhotoImage(stl_image)

            D2S_image = Image.open(D2S_image_path)
            D2S_image = D2S_image.resize((image_size, image_size), Image.LANCZOS)
            self.D2S_photo = ImageTk.PhotoImage(D2S_image)

        except Exception as e:
            print(f"Error loading images: {e}")
            self.nnunet_photo = None
            self.anon_photo = None
            self.stl_photo = None
            self.D2S_photo = None

    def create_button(self, parent, text, command, row, column, image):
        button = ttk.Button(parent, text=text, command=command, style="ButtonStyle.TButton")
        button.grid(row=row, column=column, padx=20, pady=10)
        label = ttk.Label(parent, image=image, style="ButtonLabel.TLabel")
        label.grid(row=row-1, column=column, padx=20)

    def show_home_page(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # Welcome label
        ttk.Label(self.main_frame, text="Welcome to the Home Page", background=BG_COLOR, foreground="white",
                  font=(FONT_FAMILY, 16, "bold")).pack(pady=(20, 40))

        # Frame for buttons and images
        button_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        button_frame.pack(pady=20)

        # Load images
        self.load_images()

        # AnonDtoN GUI button with image
        self.create_button(button_frame, "DICOM to NIfTI Converter", self.launch_anon_dton_gui, 1, 0, self.anon_photo)

        # nnUNet GUI button with image
        self.create_button(button_frame, "Airway Prediction", self.launch_nnunet_gui, 1, 1, self.nnunet_photo)

        # NIfTI to STL button with image
        self.create_button(button_frame, "NIfTI segmentation to STL Converter", self.launch_stl_converter_gui, 1, 2, self.stl_photo)

        # DICOM to STL button with image
        self.create_button(button_frame, "DICOM to STL Converter", self.launch_anon_dton_gui, 3, 1, self.D2S_photo)

        self.update_idletasks()  # Update idle tasks to make sure the window size is adjusted
        self.geometry('')  # Set the window size to fit the content
    
    def switch_frame(self, new_frame_class):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        new_frame_class(self.main_frame, self.show_home_page).pack(fill=tk.BOTH, expand=True)
        self.update_idletasks()  # Update idle tasks to make sure the window size is adjusted
        self.geometry('')  # Set the window size to fit the content

    def launch_anon_dton_gui(self):
        self.switch_frame(AnonDtoNGUI)

    def launch_nnunet_gui(self):
        self.switch_frame(nnUNetGUI4)

    def launch_stl_converter_gui(self):
        self.switch_frame(STLConverterGUI)

    def launch_D2S_converter_gui(self):
        self.switch_frame(AirwaySegmenterGUI)

if __name__ == "__main__":
    app = MainGUI()
    configure_styles()
    app.mainloop()
