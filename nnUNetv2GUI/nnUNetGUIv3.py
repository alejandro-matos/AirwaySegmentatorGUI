import customtkinter as ctk
from tkinter import messagebox, filedialog
import subprocess
import threading
import os
from pathlib import Path
import sys
import logging
import styles
from STLConvGUI import STLConverterGUI

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
        text_widget.insert("1.0", "Welcome to the nnUNet GUI\n\n"
                            "    - Ensure your images are in NIfTI format.\n"
                            "    - If your images are in DICOM format, convert them to NIfTI first using the DICOM to NIfTI Converter module.\n"
                            "    - For other medical image formats, use 3D Slicer to convert to NIfTI: 3D SLICER\n\n"
                            "Steps to start automatic segmentation:\n"
                            "    - In the CBCT Folder line, click on 'Browse' and select the folder containing the CBCT images to be segmented.\n"
                            "    - In the Predictions Folder line, click on 'Browse' and select the folder where the resulting segmentations are to be stored.\n"
                            "    - Click on 'Run Prediction' to initialize automatic segmentation process. \n"
                            "    - Wait for the notification \"Prediction has been completed!\" to signal the end of the prediction process\n"
                            "       - Prediction time is roughly 12 minutes per CBCT.\n"
                            "       - Total estimated time for completion = 12 minutes x (number of CBCTs). \n"
                            "    - Click 'Open Predictions Folder' to see the segmented files.\n"
                            "*For more information, visit the nnUNet GitHub page.*"
                            )
        text_widget.configure(state='disabled') # Make the text widget read-only

        # Prediction frame
        prediction_frame = ctk.CTkFrame(text_frame)
        prediction_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        prediction_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(prediction_frame, text="Prediction Options", font=(styles.FONT_FAMILY, styles.FONT_SIZE + 2, 'bold')).grid(row=1, column=0, columnspan=3, pady=(10, 10))

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

        # --- Start of STL Export Section ---
        stl_frame = ctk.CTkFrame(text_frame)  # Place `stl_frame` inside `text_frame` to match width
        stl_frame.grid(row=4, column=0, padx=10, pady=(10, 30), sticky="ew")
        stl_frame.grid_columnconfigure(1, weight=1)

        # Section label
        ctk.CTkLabel(stl_frame, text="Save Airway Predictions as 3D Models", font=(styles.FONT_FAMILY, styles.FONT_SIZE + 2, 'bold')).grid(row=0, column=0, columnspan=3, pady=(10, 10))

        # STL output folder
        ctk.CTkLabel(stl_frame, text="3D Model Output Folder:", font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold')).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        ctk.CTkEntry(stl_frame, textvariable=self.stl_output_path).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(stl_frame, text="Browse", command=self.browse_stl_output_path, font=(styles.FONT_FAMILY, styles.FONT_SIZE), width=100).grid(row=1, column=2, padx=5, pady=5)

        # Convert to STL button
        ctk.CTkButton(stl_frame, text="Generate 3D Models", command=self.convert_files_to_stl, fg_color='#2196F3', text_color='white',font=(styles.FONT_FAMILY, styles.FONT_SIZE+2, 'bold')).grid(row=2, columnspan=3, pady=(10, 10), sticky="")

        # Open STL folder button with same width and alignment as Browse button
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