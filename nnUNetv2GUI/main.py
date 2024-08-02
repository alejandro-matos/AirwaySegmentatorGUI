import os
import sys
from pathlib import Path
import customtkinter as ctk
from D2N_GUI import AnonDtoNGUI
from nnUNetGUIv3 import nnUNetScript
from DCM2STLv2 import AirwaySegmenterGUI
from STLConvGUI import STLConverterGUI
from PIL import Image
from styles import FONT_FAMILY, WINDOW_HEIGHT, WINDOW_WIDTH

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    abs_path = Path(base_path) / relative_path
    return abs_path.as_posix()  # Convert to POSIX (i.e., forward-slash) format

class MainGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Airway Segmentation")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")  # Set fixed geometry
        self.resizable(True, True) 
        # Set the color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.corner_image = None  # Create an instance variable to store the corner image

        self.create_widgets()

    def create_widgets(self):
        # Main frame to hold other GUIs
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True)

        # Load and place corner image
        self.load_corner_image()

        # Show home page content
        self.show_home_page()

    def load_corner_image(self):
        try:
            image_path = resource_path("Images/dent_100.ppm")
            image = Image.open(image_path)

            # Resize the image
            desired_size = (70, 70)  # Set your desired size here
            resized_image = image.resize(desired_size, Image.LANCZOS)

            # Convert to photo image
            self.corner_image = ctk.CTkImage(resized_image, size=desired_size)

            img_label = ctk.CTkLabel(self, image=self.corner_image, text="", pady=10)
            img_label.place(relx=1.0, rely=0.0, anchor="ne", x=-40, y=10)
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

            image_size = (200, 200)

            self.nnunet_photo = ctk.CTkImage(Image.open(nnunet_image_path), size=image_size)
            self.anon_photo = ctk.CTkImage(Image.open(anon_image_path), size=image_size)
            self.stl_photo = ctk.CTkImage(Image.open(stl_image_path), size=image_size)
            self.D2S_photo = ctk.CTkImage(Image.open(D2S_image_path), size=image_size)

        except Exception as e:
            print(f"Error loading images: {e}")
            self.nnunet_photo = None
            self.anon_photo = None
            self.stl_photo = None
            self.D2S_photo = None

    def create_button(self, parent, text, command, row, column, image):
        button_frame = ctk.CTkFrame(parent)
        button_frame.grid(row=row, column=column, padx=20, pady=10)

        label = ctk.CTkLabel(button_frame, image=image, text="")
        label.pack(pady=(0, 10))

        button = ctk.CTkButton(button_frame, text=text, command=command,font=(FONT_FAMILY, 18))
        button.pack(pady=(0, 10), padx=10)

    def show_home_page(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # Welcome label
        ctk.CTkLabel(self.main_frame, text="Airway Segmentator Home Page", font=(FONT_FAMILY, 20)).pack(pady=(20, 40))

        # Frame for buttons and images
        button_frame = ctk.CTkFrame(self.main_frame)
        button_frame.pack(pady=20)

        # Load images
        self.load_images()

        # AnonDtoN GUI button with image
        self.create_button(button_frame, "DICOM to NIfTI Converter", self.launch_anon_dton_gui, 0, 0, self.anon_photo)

        # nnUNet GUI button with image
        self.create_button(button_frame, "Airway Prediction", self.launch_nnunet_gui, 0, 1, self.nnunet_photo)

        # NIfTI to STL button with image
        self.create_button(button_frame, "Prediction to STL Converter", self.launch_stl_converter_gui, 0, 2, self.stl_photo)

        # DICOM to STL button with image
        self.create_button(button_frame, "DICOM to STL Converter", self.launch_D2S_converter_gui, 1, 1, self.D2S_photo)

    def switch_frame(self, new_frame_class):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        new_frame = new_frame_class(self.main_frame, self.show_home_page)
        new_frame.pack(fill="both", expand=True)

    def launch_anon_dton_gui(self):
        self.switch_frame(AnonDtoNGUI)

    def launch_nnunet_gui(self):
        self.switch_frame(nnUNetScript)

    def launch_stl_converter_gui(self):
        self.switch_frame(STLConverterGUI)

    def launch_D2S_converter_gui(self):
        self.switch_frame(AirwaySegmenterGUI)

if __name__ == "__main__":
    app = MainGUI()
    app.mainloop()
