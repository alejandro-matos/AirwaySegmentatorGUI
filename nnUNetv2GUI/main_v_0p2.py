import os
import sys
from pathlib import Path
import customtkinter as ctk
from D2N_GUI import AnonDtoNGUI  # Importing the DICOM handling submenu
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
        min_height = 750
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
        # Frame to hold buttons for simulating tabs
        tab_button_frame = ctk.CTkFrame(self)
        tab_button_frame.pack(fill="x", pady=(4, 2))

        # Tab buttons
        dicom_button = ctk.CTkButton(tab_button_frame, text="DICOM Handling", command=self.show_dicom_handling_tab)
        dicom_button.pack(side="left", padx=10, pady=10)

        prediction_button = ctk.CTkButton(tab_button_frame, text="Airway Prediction & Export", command=self.show_prediction_tab)
        prediction_button.pack(side="left", padx=10, pady=10)

        visualization_button = ctk.CTkButton(tab_button_frame, text="DICOM to STL", command=self.show_visualization_tab)
        visualization_button.pack(side="left", padx=10, pady=10)

        # Main frames for each "tab"
        self.dicom_handling_frame = ctk.CTkFrame(self)
        self.prediction_frame = ctk.CTkFrame(self)
        self.visualization_frame = ctk.CTkFrame(self)

        # Initialize each tab’s content
        self.setup_prediction_tab()
        self.setup_visualization_tab()

        # Load and place corner image
        self.load_corner_image()

        # Show the initial tab
        self.show_dicom_handling_tab()

    def load_corner_image(self):
        try:
            image_path = resource_path("Images/dent_100.ppm")
            image = Image.open(image_path)

            # Resize the image
            desired_size = (50, 50)  # Set your desired size here
            resized_image = image.resize(desired_size, Image.LANCZOS)

            # Convert to photo image
            self.corner_image = ctk.CTkImage(resized_image, size=desired_size)

            img_label = ctk.CTkLabel(self, image=self.corner_image, text="", pady=5)
            img_label.place(relx=1.0, rely=0.0, anchor="ne", x=-20, y=2)
        except Exception as e:
            logging.error(f"Error loading corner image: {e}")

    def setup_prediction_tab(self):
        # Prediction Tab Contents
        nnunet_button = ctk.CTkButton(self.prediction_frame, text="Run Prediction", command=self.launch_nnunet_gui)
        nnunet_button.pack(pady=10)

    def setup_visualization_tab(self):
        # 3D Visualization Tab Contents
        convert_stl_button = ctk.CTkButton(self.visualization_frame, text="Convert Prediction to STL", command=self.launch_stl_converter_gui)
        convert_stl_button.pack(pady=10)

        dicom_to_stl_button = ctk.CTkButton(self.visualization_frame, text="Convert DICOM to STL", command=self.launch_D2S_converter_gui)
        dicom_to_stl_button.pack(pady=10)

    def show_dicom_handling_tab(self):
        # Clear other frames and add DICOM handling frame
        self.prediction_frame.pack_forget()
        self.visualization_frame.pack_forget()
        
        # Use AnonDtoNGUI for DICOM Handling frame
        self.dicom_handling_frame.pack_forget()  # Clear previous instance if any
        self.dicom_handling_frame = AnonDtoNGUI(self, self.show_dicom_handling_tab)
        self.dicom_handling_frame.pack(fill="both", expand=True)

    def show_prediction_tab(self):
        self.dicom_handling_frame.pack_forget()
        self.visualization_frame.pack_forget()

        # Use nnUNetScript for Prediction frame
        self.prediction_frame.pack_forget()  # Clear previous instance if any
        self.prediction_frame = nnUNetScript(self, self.show_prediction_tab)
        self.prediction_frame.pack(fill="both", expand=True)

    def show_visualization_tab(self):
        self.dicom_handling_frame.pack_forget()
        self.prediction_frame.pack_forget()

        # Use AirwaySegmenterGUI (from DCM2STLv2) for 3D Visualization frame
        self.visualization_frame.pack_forget()  # Clear previous instance if any
        self.visualization_frame = AirwaySegmenterGUI(self, self.show_prediction_tab)
        self.visualization_frame.pack(fill="both", expand=True)

    def launch_nnunet_gui(self):
        self.switch_frame(nnUNetScript)

    def launch_stl_converter_gui(self):
        self.switch_frame(STLConverterGUI)

    def launch_D2S_converter_gui(self):
        self.switch_frame(AirwaySegmenterGUI)

    def switch_frame(self, new_frame_class):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        new_frame = new_frame_class(self.main_frame, self.show_home_page)
        new_frame.pack(fill="both", expand=True)

if __name__ == "__main__":
    app = MainGUI()
    app.update_idletasks()
    window_width = 900
    window_height = 650
    app.mainloop()
