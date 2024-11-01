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
import logging

# Setup logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    abs_path = Path(base_path) / relative_path
    return abs_path.as_posix()  # Convert to POSIX (i.e., forward-slash) format

class MainGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Airway Segmentation")
        self.resizable(True, True)
        
        # Set the color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.corner_image = None  # Create an instance variable to store the corner image

        # Set the application icon
        self.set_window_icon()

        self.create_widgets()

        # Set a minimum window size
        min_width = 900
        min_height = 700
        self.minsize(min_width, min_height)

        # Resize window based on content
        self.update_idletasks()

    def set_window_icon(self):
        try:
            icon_path = resource_path("Images/icon.ico")  # Path to your .ico file
            self.iconbitmap(icon_path)
        except Exception as e:
            logging.error(f"Error setting window icon: {e}")

    def create_widgets(self):
        # Create Tab View
        self.tab_view = ctk.CTkTabView(self.main_frame)
        self.tab_view.pack(fill="both", expand=True, pady=(5, 0))

        # Adding tabs
        self.tab_view.add("DICOM Handling")
        self.tab_view.add("Prediction")
        self.tab_view.add("3D Visualization")

        # Load and place corner image
        self.load_corner_image()

        # Initialize each tab’s content
        self.setup_dicom_handling_tab()
        self.setup_prediction_tab()
        self.setup_visualization_tab()

    def load_corner_image(self):
        try:
            image_path = resource_path("Images/dent_100.ppm")
            image = Image.open(image_path)

            # Resize the image
            desired_size = (80, 80)  # Set your desired size here
            resized_image = image.resize(desired_size, Image.LANCZOS)

            # Convert to photo image
            self.corner_image = ctk.CTkImage(resized_image, size=desired_size)

            img_label = ctk.CTkLabel(self, image=self.corner_image, text="", pady=5)
            img_label.place(relx=1.0, rely=0.0, anchor="ne", x=-30, y=15)
        except Exception as e:
            logging.error(f"Error loading corner image: {e}")

    def load_images(self):
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            image_names = {
                "nnunet": "nnunet_icon2.png",
                "anon": "D2NConv2.png",
                "stl": "stl_icon2.png",
                "D2S": "DCM2STL.png"
            }
            
            self.images = {}
            for key, file_name in image_names.items():
                img_path = os.path.join(base_dir, "Images", file_name)
                self.images[key] = ctk.CTkImage(Image.open(img_path), size=(200, 200))
        except Exception as e:
            logging.error(f"Error loading images: {e}")
            self.images = {key: None for key in image_names}

    def create_button(self, parent, text, command, row, column, image):
        button_frame = ctk.CTkFrame(parent)
        button_frame.grid(row=row, column=column, padx=20, pady=10)

        label = ctk.CTkLabel(button_frame, image=image, text="")
        label.pack(pady=(0, 10))

        button = ctk.CTkButton(button_frame, text=text, command=command, font=(FONT_FAMILY, 18))
        button.pack(pady=(0, 10), padx=10)

    def show_home_page(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # Welcome label
        ctk.CTkLabel(self.main_frame, text="Upper Airway Segmentation Tools Overview", font=(FONT_FAMILY, 20)).pack(pady=(25, 5))

        # Frame for buttons and images
        button_frame = ctk.CTkFrame(self.main_frame)
        button_frame.pack(pady=20)

        # Load images
        self.load_images()

        # Tool configuration
        self.tools = [
            {"name": "DICOM to NIfTI Converter", "command": self.launch_anon_dton_gui, "image": self.images.get("anon")},
            {"name": "Airway Prediction", "command": self.launch_nnunet_gui, "image": self.images.get("nnunet")},
            {"name": "Prediction to STL Converter", "command": self.launch_stl_converter_gui, "image": self.images.get("stl")},
            {"name": "DICOM to STL Converter", "command": self.launch_D2S_converter_gui, "image": self.images.get("D2S")}
        ]

        # Create buttons dynamically from tools configuration (2 buttons on top row, 2 buttons on bottom row)
        for i, tool in enumerate(self.tools):
            row = 0 if i < 2 else 1
            column = i % 2
            self.create_button(button_frame, tool["name"], tool["command"], row, column, tool["image"])

    def switch_frame(self, new_frame_class):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        new_frame = new_frame_class(self.main_frame, self.show_home_page)
        new_frame.pack(fill="both", expand=True)
        # Reset window size to a fixed default value to prevent continuous expansion
        self.update_idletasks()
        self.update_idletasks()
        window_width = 900
        window_height = 650

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
    app.update_idletasks()
    window_width = 900
    window_height = 650
    app.mainloop()