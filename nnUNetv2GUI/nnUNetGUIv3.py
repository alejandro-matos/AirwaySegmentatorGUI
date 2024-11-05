import customtkinter as ctk
from tkinter import messagebox, filedialog, Text
import webbrowser
from tkinter.ttk import Progressbar
import subprocess
import threading
import os
from pathlib import Path
import sys
import logging
import styles
from STLConvGUI import STLConverterGUI
import csv
import nibabel as nib
import numpy as np



# Set up logging with a detailed format
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class nnUNetScript(ctk.CTkFrame):
    def __init__(self, parent, home_callback):
        super().__init__(parent)
        self.parent = parent
        self.home_callback = home_callback

        # Path setup for nnUNet data
        self.parent_dir = Path(os.getcwd()).parent
        self.parent_of_parent_dir = self.parent_dir.parent
        self.Path1 = self.parent_of_parent_dir / 'Airways_v2' / 'nnUNet_raw'
        self.Path2 = self.parent_of_parent_dir / 'Airways_v2' / 'nnUNet_results'
        self.Path3 = self.parent_of_parent_dir / 'Airways_v2' / 'nnUNet_preprocessed'

        # Variables for paths
        self.input_path = ctk.StringVar()
        self.output_path = ctk.StringVar()
        self.stl_output_path = ctk.StringVar()  # For STL export folder

        self.create_widgets()
        self.grid_columnconfigure(0, weight=1)

    def browse_input_path(self):
        selected_path = filedialog.askdirectory()
        if selected_path:
            self.input_path.set(selected_path)

    def browse_output_path(self):
        selected_path = filedialog.askdirectory()
        if selected_path:
            self.output_path.set(selected_path)

    def setup_paths(self):
        nnUNet_IN = self.input_path.get()
        nnUNet_OUT = self.output_path.get()

        # Validate paths
        if not Path(nnUNet_IN).exists() or not Path(nnUNet_OUT).exists():
            logging.error("Invalid input or output path.")
            return None, None

        return nnUNet_IN, nnUNet_OUT

    def suffix_files(self, nnUNet_IN):
        nifti_files = [f for f in os.scandir(nnUNet_IN) if f.name.endswith(('.nii', '.nii.gz'))]
        for nifti_file in nifti_files:
            base_name, ext = os.path.splitext(nifti_file.name)
            if ext == ".gz":
                base_name, ext2 = os.path.splitext(base_name)
                ext = ext2 + ext
            if not base_name.endswith('_0000'):
                new_name = f"{base_name}_0000{ext}"
                new_path = Path(nnUNet_IN) / new_name
                if not new_path.exists():
                    logging.info(f"Renaming NIfTI file {nifti_file.name} to {new_name}")
                    os.rename(nifti_file.path, new_path)

    def open_folder(self, path):
        path = Path(path).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open the directory: {str(e)}")

    def run_script(self):
        # Set up the loading dialog with a progress bar
        loading = ctk.CTkToplevel(self.parent)
        loading.title('Processing')
        label_font = ("Arial", 20)
        ctk.CTkLabel(loading, text='Prediction is running, please wait...', font=label_font).pack(pady=10, padx=10)
        
        progress = Progressbar(loading, orient='horizontal', length=300, mode='indeterminate')
        progress.pack(pady=10)
        progress.start()

        loading.grab_set()

        def script_execution():
            nnUNet_IN, nnUNet_OUT = self.setup_paths()
            if not nnUNet_IN or not nnUNet_OUT:
                messagebox.showerror("Error", "Path to CBCT files in NIfTI format and/or Predictions folder not selected/valid")
                loading.destroy()
                return

            logging.info('nnUNet_IN: %s', nnUNet_IN)
            logging.info('nnUNet_OUT: %s', nnUNet_OUT)

            # Set environment variables, if not already set
            os.environ.setdefault('nnUNet_raw', str(self.Path1))
            os.environ.setdefault('nnUNet_results', str(self.Path2))
            os.environ.setdefault('nnUNet_preprocessed', str(self.Path3))

            self.suffix_files(nnUNet_IN)

            try:
                result = subprocess.run([
                    'nnUNetv2_predict', '-i', nnUNet_IN, '-o', nnUNet_OUT,
                    '-d', '13', '-c', '3d_fullres',
                ], capture_output=True, text=True)

                logging.info('stdout: %s', result.stdout)
                logging.error('stderr: %s', result.stderr)

                result.check_returncode()

                messagebox.showinfo('Notification', 'Prediction has been completed!')
            except subprocess.CalledProcessError as e:
                logging.error("Error: %s", e.stderr)
                messagebox.showerror("Error", f"Failed to run nnUNet prediction: {e.stderr}")
            except Exception as e:
                logging.error("Unexpected error: %s", str(e))
                messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")
            finally:
                progress.stop()
                loading.destroy()

        threading.Thread(target=script_execution).start()

    def rename_output_files(self, output_path):
        for file in os.listdir(output_path):
            if file.endswith('.nii.gz') and not file.endswith('_seg.nii.gz'):
                old_path = os.path.join(output_path, file)
                new_name = f"{os.path.splitext(os.path.splitext(file)[0])[0]}_seg.nii.gz"
                new_path = os.path.join(output_path, new_name)
                
                if not os.path.exists(new_path):
                    os.rename(old_path, new_path)
                    logging.info(f"Renamed {file} to {new_name}")
                else:
                    logging.info(f"Skipped renaming {file} as {new_name} already exists")
    
    def calculate_volume(self, file_format="txt"):
        output_path = self.output_path.get()

        if not output_path:
            messagebox.showwarning("Input Error", "Please select a Predictions output directory.")
            return

        try:
            # Collect volume results for each file
            volume_results = []
            for file in Path(output_path).glob("*.nii.gz"):
                volume = self.calculate_volume_from_file(file)  # Calculate the volume for each file
                volume_results.append((file.name, volume))  # Append filename and volume in ml

            # Define file path based on selected format
            if file_format == "txt":
                file_path = Path(output_path) / "predicted_airways_volume.txt"
                with open(file_path, "w") as f:
                    f.write("Filename\tVolume (mm^3)\n")  # Add header for clarity
                    for filename, volume in volume_results:
                        f.write(f"{filename}\t{volume:.2f}\n")

            elif file_format == "csv":
                file_path = Path(output_path) / "predicted_airways_volume.csv"
                with open(file_path, mode="w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Filename", "Volume (mm^3)"])  # Header
                    writer.writerows(volume_results)

            messagebox.showinfo("Volume Calculation", f"Volume calculation completed! Results saved to {file_path}")

        except Exception as e:
            logging.error("Error calculating volume: %s", str(e))
            messagebox.showerror("Error", f"An error occurred while calculating volume: {str(e)}")

    def calculate_volume_from_file(self, file_path, airway_label=1):
        """
        Calculate the volume of the airway from a NIfTI file.

        Parameters:
        - file_path (Path): Path to the .nii.gz file
        - airway_label (int): Label used for the airway segmentation in the mask (default is 1)

        Returns:
        - total_volume (float): Volume in cubic millimeters
        """
        try:
            # Load the NIfTI file
            nifti_img = nib.load(file_path)
            data = nifti_img.get_fdata()

            # Log the affine matrix and zooms for debugging
            affine = nifti_img.affine
            voxel_sizes = nifti_img.header.get_zooms()  # Voxel dimensions in mm
            logging.info(f"File: {file_path}")
            logging.info(f"Affine matrix: \n{affine}")
            logging.info(f"Voxel dimensions (in mm): {voxel_sizes}")

            # Calculate the volume of a single voxel
            voxel_volume = np.prod(voxel_sizes)  # Voxel volume in mm³
            logging.info(f"Voxel volume: {voxel_volume:.2f} mm³")

            # Count the number of voxels in the airway region
            airway_voxel_count = np.sum(data == airway_label)
            logging.info(f"Total airway voxel count for label {airway_label}: {airway_voxel_count}")

            # Calculate total volume in mm³
            total_volume_mm3 = airway_voxel_count * voxel_volume
            logging.info(f"Calculated airway volume: {total_volume_mm3:.2f} mm³")

            return total_volume_mm3

        except Exception as e:
            logging.error(f"Failed to calculate volume for {file_path}: {e}")
            return 0  # Return 0 if there was an error
    
    # Function to open URL
    def open_nnunet_link(event):
        webbrowser.open_new("https://github.com/MIC-DKFZ/nnUNet")
    
    def create_widgets(self):
        # Main content frame
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=1, column=0, sticky="", padx=20, pady=10)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        text_frame = ctk.CTkFrame(content_frame)
        text_frame.grid(row=0, column=0, sticky="ew")
        text_frame.grid_columnconfigure(0, weight=1)

        # Adjust the text widget width here
        text_widget = ctk.CTkTextbox(text_frame, wrap='word', height=styles.TEXTBOX_HEIGHT, width=styles.TEXTBOX_WIDTH)  # Width adjusted to match D2N_GUI
        text_widget.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        text_widget.insert("1.0", 
            "WELCOME TO THE NNUNET SEGMENTATION TOOL\n\n"
            "1. PREPARE YOUR IMAGES\n"
            "    - Ensure your images are in NIfTI format (.nii or .nii.gz).\n"
            "    - If they are in DICOM format, use the DICOM to NIfTI Converter module first.\n"
            "    - For other formats, you can use 3D Slicer to convert them to NIfTI.\n\n"
            
            "2. RUN AUTOMATIC SEGMENTATION\n"
            "    - Under CBCT Folder, click 'Browse' to select the folder with the CBCT images you want to segment.\n"
            "    - Under Predictions Folder, click 'Browse' to choose the folder where the segmented results will be saved.\n"
            "    - Click 'Run Prediction' to start the segmentation process.\n"
            "    - A notification will confirm when the prediction is complete.\n"
            "    - Note: Each image takes from 3 to 10 minutes to process, depending on the file dimensions.\n\n"
            
            "3. CALCULATE AIRWAY VOLUMES\n"
            "    - In the Volume Calculation section, choose the format for your volume list: TXT file or CSV file.\n"
            "    - Click the corresponding button to calculate the volumes of the segmented airways and save them in the selected format in your Predictions Folder.\n"
            "    - A notification will confirm when the volume calculation is complete, and the file will be ready for viewing.\n\n"
            
            "4. EXPORT SEGMENTED MODELS AS 3D STL FILES\n"
            "    - In the 3D Model Output Folder section, click 'Browse' to select the folder where you want to save the STL files.\n"
            "    - Click 'Generate 3D Models' to convert the segmented predictions into STL files, which can be used for 3D viewing or printing.\n"
            "    - To view the STL files, click 'Open 3D Model Folder'.\n\n"
            
            # "*For further details, please visit the nnUNet GitHub page.*"
        )
        text_widget.configure(state='disabled') # Make the text widget read-only

        # Prediction frame
        prediction_frame = ctk.CTkFrame(text_frame)
        prediction_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        prediction_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(prediction_frame, text="Prediction Options", font=(styles.FONT_FAMILY, styles.FONT_SIZE + 2, 'bold')).grid(row=1, column=0, columnspan=4, pady=(5, 5))

        ctk.CTkLabel(prediction_frame, text="CBCT Folder:", font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold')).grid(row=2, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(prediction_frame, textvariable=self.input_path).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(prediction_frame, text="Browse", command=self.browse_input_path, font=(styles.FONT_FAMILY, styles.FONT_SIZE)).grid(row=2, column=2, padx=5, pady=5)
        ctk.CTkButton(prediction_frame, text="Open CBCT Folder", command=lambda: self.open_folder(self.input_path.get()), fg_color='#BA562E', text_color='white').grid(row=2, column=3, padx=5, pady=5)

        ctk.CTkLabel(prediction_frame, text="Predictions Folder:", font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold')).grid(row=3, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(prediction_frame, textvariable=self.output_path).grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(prediction_frame, text="Browse", command=self.browse_output_path, font=(styles.FONT_FAMILY, styles.FONT_SIZE)).grid(row=3, column=2, padx=5, pady=5)
        ctk.CTkButton(prediction_frame, text="Open Predictions Folder", command=lambda: self.open_folder(self.output_path.get()), fg_color='#BA562E', text_color='white').grid(row=3, column=3, padx=5, pady=5)

        # Run prediction button
        ctk.CTkButton(prediction_frame, text="Run Prediction", command=self.run_script, fg_color='#2196F3', text_color='white', font=(styles.FONT_FAMILY, styles.FONT_SIZE+2, 'bold'), width=120).grid(row=4, columnspan=4, pady=(10,10),sticky="")

        # --- New Volume Calculation Section ---
        volume_frame = ctk.CTkFrame(text_frame)
        volume_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        # Configure column 1 to take up extra space, helping center the title but keeping buttons close
        volume_frame.grid_columnconfigure(0, weight=1)
        volume_frame.grid_columnconfigure(1, weight=0)  # Button columns remain fixed in width
        volume_frame.grid_columnconfigure(2, weight=0)
        volume_frame.grid_columnconfigure(3, weight=1)

        # Centering the title by placing it in the middle column with a high columnspan
        ctk.CTkLabel(volume_frame, text="Airway Volume Calculation", 
                    font=(styles.FONT_FAMILY, styles.FONT_SIZE + 2, 'bold')).grid(row=0, column=1, columnspan=2, pady=(5, 5), sticky="ew")

        # Export options label
        ctk.CTkLabel(volume_frame, text="Export Volume list as:", 
                    font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold')).grid(row=1, column=0, padx=5, pady=5, sticky="w")

        # Calculate Volume buttons
        ctk.CTkButton(volume_frame, text=".txt file", command=self.calculate_volume, 
                    fg_color='#2196F3', text_color='white', font=(styles.FONT_FAMILY, styles.FONT_SIZE + 2, 'bold')).grid(row=1, column=1, padx=5, pady=(10, 10), sticky="w")
        ctk.CTkButton(volume_frame, text=".csv file", command=lambda: self.calculate_volume(file_format="csv"), 
              fg_color='#2196F3', text_color='white', font=(styles.FONT_FAMILY, styles.FONT_SIZE + 2, 'bold')).grid(row=1, column=2, padx=5, pady=(10, 10), sticky="w")
        ctk.CTkButton(volume_frame, text="Open Predictions Folder", command=lambda: self.open_folder(self.output_path.get()), fg_color='#BA562E', text_color='white').grid(row=1, column=3, padx=5, pady=5, sticky='e')

        # --- STL Export Section ---
        stl_frame = ctk.CTkFrame(text_frame)  # Place `stl_frame` inside `text_frame` to match width
        stl_frame.grid(row=4, column=0, padx=10, pady=(10, 20), sticky="ew")
        stl_frame.grid_columnconfigure(1, weight=1)

        # Section label
        ctk.CTkLabel(stl_frame, text="Save Airway Predictions as 3D Models", font=(styles.FONT_FAMILY, styles.FONT_SIZE + 2, 'bold')).grid(row=0, column=0, columnspan=3, pady=(5, 5))

        # STL output folder
        ctk.CTkLabel(stl_frame, text="3D Model Output Folder:", font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold')).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        ctk.CTkEntry(stl_frame, textvariable=self.stl_output_path).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(stl_frame, text="Browse", command=self.browse_stl_output_path, font=(styles.FONT_FAMILY, styles.FONT_SIZE), width=100).grid(row=1, column=2, padx=5, pady=5)

        # Convert to STL button
        ctk.CTkButton(stl_frame, text="Generate 3D Models", command=self.convert_files_to_stl, fg_color='#2196F3', text_color='white', font=(styles.FONT_FAMILY, styles.FONT_SIZE + 2, 'bold')).grid(row=2, columnspan=3, pady=(10, 10), sticky="")

        # Open STL folder button
        ctk.CTkButton(stl_frame, text="Open 3D Model Folder", command=lambda: self.open_folder(self.stl_output_path.get()), fg_color='#BA562E', font=(styles.FONT_FAMILY, styles.FONT_SIZE), width=100).grid(row=2, column=2, pady=5, padx=10)

    # Helper functions for STL path browsing and conversion
    def browse_stl_output_path(self):
        selected_path = filedialog.askdirectory()
        if selected_path:
            self.stl_output_path.set(selected_path)

    def convert_files_to_stl(self):
        # Convert all predictions in the output folder to STL
        input_path = self.output_path.get()  # Use predictions output path as input for STL conversion
        output_path = self.stl_output_path.get()

        if not input_path or not output_path:
            messagebox.showwarning("Input Error", "Please select both predictions and STL output directories.")
            return

        stl_converter = STLConverterGUI(self, self.home_callback)
        stl_converter.input_path.set(input_path)
        stl_converter.output_path.set(output_path)
        stl_converter.convert_files()  # Convert predictions to STL

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("nnUNet GUI")
    root.geometry("900x00")  # Adjusted initial geometry for better display
    root.resizable(True, True)  # Allow window resizing

    app = nnUNetScript(root, root.destroy)
    app.pack(fill="both", expand=True)

    root.mainloop()