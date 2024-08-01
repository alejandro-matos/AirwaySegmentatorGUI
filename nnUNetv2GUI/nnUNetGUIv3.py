import customtkinter as ctk
from tkinter import messagebox, filedialog
import subprocess
import threading
import os
from pathlib import Path
import sys
import logging

# This code is an iteration to see if we can do faster than 12 min.

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class nnUNetGUI4(ctk.CTkFrame):
    def __init__(self, parent, home_callback):
        super().__init__(parent)
        self.parent = parent
        self.home_callback = home_callback

        self.parent_dir = Path(os.getcwd()).parent
        self.Path1 = self.parent_dir / 'Airways_v2' / 'nnUNet_raw'
        self.Path2 = self.parent_dir / 'Airways_v2' / 'nnUNet_results'
        self.Path3 = self.parent_dir / 'Airways_v2' / 'nnUNet_preprocessed'
        self.input_path = ctk.StringVar()
        self.output_path = ctk.StringVar()

        self.create_widgets()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

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
        loading = ctk.CTkToplevel(self.parent)
        loading.title('Processing')
        label_font = ("Arial", 20)
        ctk.CTkLabel(loading, text='Prediction is running, please wait...', font=label_font).pack(pady=100, padx=100)
        loading.grab_set()

        def script_execution():
            nnUNet_IN, nnUNet_OUT = self.setup_paths()
            if not nnUNet_IN or not nnUNet_OUT:
                messagebox.showerror("Error", "Path to NIfTI and/or Predictions folder(s) not selected/valid")
                loading.destroy()
                return

            logging.info('nnUNet_IN: %s', nnUNet_IN)
            logging.info('nnUNet_OUT: %s', nnUNet_OUT)

            os.environ['nnUNet_raw'] = str(self.Path1)
            os.environ['nnUNet_results'] = str(self.Path2)
            os.environ['nnUNet_preprocessed'] = str(self.Path3)

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
                loading.destroy()

        threading.Thread(target=script_execution).start()
    
    def create_widgets(self):
        # Home button
        home_button = ctk.CTkButton(self, text="Home", command=self.home_callback, fg_color='#FF9800', text_color='white',
                                    font=(styles.FONT_FAMILY, styles.BUTTON_FONT_SIZE))
        home_button.grid(row=0, column=0, padx=(10, 20), pady=(10, 20), sticky="w")

        # Main content frame
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        # Scrollable frame for text and inputs
        scrollable_frame = ctk.CTkScrollableFrame(content_frame)
        scrollable_frame.grid(row=0, column=0, sticky="nsew")
        scrollable_frame.grid_columnconfigure(0, weight=1)

        # Text widget
        text_widget = ctk.CTkTextbox(scrollable_frame, wrap='word', height=300)
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
        text_widget.configure(state='disabled')

        # Input frame
        input_frame = ctk.CTkFrame(scrollable_frame)
        input_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        input_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(input_frame, text="CBCT folder:", font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold')).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(input_frame, textvariable=self.input_path).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(input_frame, text="Browse", command=self.browse_input_path, font=(styles.FONT_FAMILY, styles.FONT_SIZE)).grid(row=0, column=2, padx=5, pady=5)
        ctk.CTkButton(input_frame, text="Open CBCT Folder", command=lambda: self.open_folder(self.input_path.get()), fg_color='#BA562E', text_color='white').grid(row=0, column=3, padx=5, pady=5)

        # Output frame
        output_frame = ctk.CTkFrame(scrollable_frame)
        output_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        output_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(output_frame, text="Predictions folder:", font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold')).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(output_frame, textvariable=self.output_path).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(output_frame, text="Browse", command=self.browse_output_path, font=(styles.FONT_FAMILY, styles.FONT_SIZE)).grid(row=0, column=2, padx=5, pady=5)
        ctk.CTkButton(output_frame, text="Open Predictions Folder", command=lambda: self.open_folder(self.output_path.get()), fg_color='#BA562E', text_color='white').grid(row=0, column=3, padx=5, pady=5)

        # Run prediction button
        ctk.CTkButton(scrollable_frame, text="Run Prediction", command=self.run_script, fg_color='#2196F3', text_color='white').grid(row=3, column=0, pady=20)

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("nnUNet GUI")
    root.geometry("1000x800")
    root.minsize(800, 600)

    app = nnUNetGUI4(root, root.destroy)
    app.pack(fill="both", expand=True)

    root.mainloop()