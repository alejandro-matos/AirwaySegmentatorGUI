import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
import threading
from pathlib import Path
import logging
import subprocess
import nibabel as nib
import SimpleITK as sitk
import pydicom
from nnUNetGUIv3 import nnUNetScript
from D2N_GUI import AnonDtoNGUI
from STLConvGUI import STLConverterGUI

# Set up logging for detailed feedback
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class UnifiedAirwaySegmentationGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("UpperAirway Segmentator Tool")
        self.geometry("950x750")

        # Variables for paths and options
        self.input_path = ctk.StringVar()
        self.output_path = ctk.StringVar()
        self.file_type = ctk.StringVar(value="DICOM")
        self.anonymize = ctk.BooleanVar()
        self.convert_to_nifti = ctk.BooleanVar()
        self.rename_files = ctk.BooleanVar()
        self.run_prediction = ctk.BooleanVar()
        self.calculate_volume = ctk.BooleanVar()
        self.export_stl = ctk.BooleanVar()
        self.data_nickname = ctk.StringVar(value='UA')  # Nickname for renaming
        self.starting_number = ctk.IntVar(value=1)  # Starting number for renaming
        self.renamed_folders = {}  # Initialize the dictionary to store renamed folders

        # Set the color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Build the interface
        self.create_widgets()
        # Adjust grid configuration for vertical centering
        self.grid_columnconfigure(0, weight=1)

        # Set a minimum window size
        min_width = 950
        min_height = 750
        self.minsize(min_width, min_height)

    def toggle_rename_fields(self):
        """Enable or disable nickname and starting number fields based on Rename Files checkbox."""
        if self.rename_files.get():
            self.nick_label_entry.configure(state="normal")
            self.start_number_entry.configure(state="normal")
        else:
            self.nick_label_entry.configure(state="disabled")
            self.start_number_entry.configure(state="disabled")

    def update_task_options(self, selected_file_type):
        """Enable/Disable options based on the file type selected."""
        if selected_file_type == "NIfTI":
            # Disable anonymize checkboxes
            self.convert_switch.configure(state="disabled")
            self.convert_to_nifti.set(False)  # Uncheck if already checked
            self.anonymize_rename_switch.configure(state="disabled")
            self.rename_files.set(False)
        else:
            # Enable anonymize checkboxes for DICOM
            self.convert_switch.configure(state="normal")
            self.anonymize_rename_switch.configure(state="normal")

    def browse_input_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.input_path.set(folder)

    def start_processing(self):
        input_folder = self.input_path.get()
        if not os.path.isdir(input_folder):
            messagebox.showerror("Error", "Invalid input folder.")
            return

        # Create the output folder in the parent directory with a "_Processed" suffix
        parent_dir = Path(input_folder).parent
        output_folder = os.path.join(parent_dir, f"{Path(input_folder).stem}_Processed")
        os.makedirs(output_folder, exist_ok=True)

        if self.rename_files.get():
            self.rename_files_in_folder(output_folder)  
            
        # Run nnUNet prediction if selected
        if self.run_prediction.get():
            # Determine nnUNet_IN based on file type and conversion setting
            if self.file_type.get() == "NIfTI":
                # If already in NIfTI, use the input folder directly
                nnUNet_IN = input_folder
            elif self.file_type.get() == "DICOM":
                # Enforce conversion to NIfTI for prediction if the files are in DICOM format
                if not self.convert_to_nifti.get():
                    messagebox.showerror("Error", "Conversion to NIfTI is required for DICOM files when running predictions. Please enable the conversion option.")
                    return

                # Convert DICOM to NIfTI
                nifti_folder = os.path.join(output_folder, "NIfTI_Converted")
                os.makedirs(nifti_folder, exist_ok=True)
                self.convert_dicom_to_nifti(input_folder, nifti_folder)
                nnUNet_IN = nifti_folder  # Use the converted NIfTI folder as input
            else:
                messagebox.showerror("Error", "Files must be either in NIfTI format or converted to NIfTI from DICOM.")
                return

            # Set prediction output folder
            prediction_folder = os.path.join(output_folder, "Predictions")
            os.makedirs(prediction_folder, exist_ok=True)
            self.run_nnunet_prediction(nnUNet_IN, prediction_folder)

        if self.calculate_volume.get():
            volume_folder = os.path.join(output_folder, "Volume_Calculations")
            os.makedirs(volume_folder, exist_ok=True)
            self.calculate_airway_volumes(volume_folder)

        if self.export_stl.get():
            stl_folder = os.path.join(output_folder, "STL_Exports")
            os.makedirs(stl_folder, exist_ok=True)
            self.export_predictions_to_stl(stl_folder)

        messagebox.showinfo("Processing Complete", "All selected tasks have been completed.")

    def anonymize_and_rename_dicom_structure(self, source_dir, destination_dir):
        start_number = self.starting_number.get()
        self.renamed_folders = {}  # Reset dictionary for each processing session

        for patient_index, patient_folder in enumerate(os.listdir(source_dir), start=start_number):
            patient_path = os.path.join(source_dir, patient_folder)
            if os.path.isdir(patient_path):
                patient_nickname = f"{self.data_nickname.get()}_{patient_index}"
                self.renamed_folders[patient_folder] = patient_nickname  # Store original to new name mapping

                contains_subdirs = any(os.path.isdir(os.path.join(patient_path, item)) for item in os.listdir(patient_path))
                if contains_subdirs:
                    for time_point in os.listdir(patient_path):
                        time_point_path = os.path.join(patient_path, time_point)
                        if os.path.isdir(time_point_path):
                            time_point_nickname = f"{patient_nickname}_{time_point}"
                            self.renamed_folders[os.path.join(patient_folder, time_point)] = time_point_nickname
                            new_folder_path = os.path.join(destination_dir, time_point_nickname)
                            os.makedirs(new_folder_path, exist_ok=True)
                            self.process_dicom_files(time_point_path, new_folder_path, time_point_nickname)
                else:
                    new_folder_path = os.path.join(destination_dir, patient_nickname)
                    os.makedirs(new_folder_path, exist_ok=True)
                    self.process_dicom_files(patient_path, new_folder_path, patient_nickname)

    def process_dicom_files(self, input_folder, output_folder, patient_name):
        """
        Anonymize and rename DICOM files in a specified folder.
        """
        for i, file_name in enumerate(os.listdir(input_folder)):
            if file_name.lower().endswith(".dcm"):
                input_file_path = os.path.join(input_folder, file_name)
                anonymized_file_name = f"{patient_name}_{i + 1}.dcm"
                output_file_path = os.path.join(output_folder, anonymized_file_name)
                
                # Anonymize and rename each DICOM file
                self.anonymize_dicom(input_file_path, output_file_path, patient_name)

    def anonymize_dicom(self, input_file, output_file, patient_name):
        """
        Anonymize DICOM file fields based on provided patient name.
        """
        dataset = pydicom.dcmread(input_file, force=True)
        tags_to_anonymize = [
            ("PatientName", patient_name),
            ("PatientID", "ANON"),
            ("PatientBirthDate", "N/A"),
            ("PatientSex", "N/A"),
        ]
        for tag, value in tags_to_anonymize:
            if tag in dataset:
                dataset.data_element(tag).value = value
        dataset.save_as(output_file)

    def convert_dicom_to_nifti(self, input_folder, output_folder):
        try:
            nifti_folder = output_folder
            os.makedirs(nifti_folder, exist_ok=True)

            def process_dicom_series(dicom_folder, patient_name, time_point=None):
                reader = sitk.ImageSeriesReader()
                series_ids = reader.GetGDCMSeriesIDs(dicom_folder)
                if not series_ids:
                    logging.warning(f"No DICOM series found in {dicom_folder}. Skipping.")
                    return

                for series_id in series_ids:
                    dicom_names = reader.GetGDCMSeriesFileNames(dicom_folder, series_id)
                    reader.SetFileNames(dicom_names)
                    image = reader.Execute()
                    direction = image.GetDirection()
                    if direction[8] < 0:
                        image = sitk.Flip(image, [False, False, True])

                    # Choose filename based on whether renaming is enabled
                    if self.rename_files.get():
                        if time_point:
                            nifti_filename = f"{patient_name}_{time_point}.nii.gz"
                        else:
                            nifti_filename = f"{patient_name}.nii.gz"
                    else:
                        # Use original folder names when renaming is disabled
                        if time_point:
                            nifti_filename = f"{patient_name}_{time_point}.nii.gz"
                        else:
                            nifti_filename = f"{patient_name}.nii.gz"
                        
                    nifti_path = os.path.join(nifti_folder, nifti_filename)
                    sitk.WriteImage(image, nifti_path)
                    logging.info(f"NIfTI file saved at: {nifti_path}")

            # Main conversion loop
            for patient_folder in os.listdir(input_folder):
                patient_path = os.path.join(input_folder, patient_folder)
                if os.path.isdir(patient_path):
                    # Use renamed name only if renaming is enabled
                    if self.rename_files.get():
                        patient_name = self.renamed_folders.get(patient_folder, patient_folder)
                        if '_T' in patient_name:  # If the renamed folder already contains time point info
                            patient_name = patient_name.split('_T')[0]  # Remove the time point part
                    else:
                        patient_name = patient_folder  # Use original folder name
                    
                    contains_subdirs = any(
                        os.path.isdir(os.path.join(patient_path, item))
                        for item in os.listdir(patient_path)
                    )

                    if contains_subdirs:
                        for time_point in os.listdir(patient_path):
                            time_point_path = os.path.join(patient_path, time_point)
                            if os.path.isdir(time_point_path):
                                # Use appropriate time point name based on renaming setting
                                if self.rename_files.get():
                                    if '_T' in time_point:
                                        time_point = 'T' + time_point.split('_T')[1]
                                process_dicom_series(time_point_path, patient_name, time_point=time_point)
                    else:
                        process_dicom_series(patient_path, patient_name)

            messagebox.showinfo("Conversion Complete", f"NIfTI files saved in: {nifti_folder}")

        except Exception as e:
            logging.error(f"Error converting DICOM to NIfTI: {e}")
            messagebox.showerror("Conversion Error", f"Failed to convert DICOM to NIfTI. Error: {e}")

    def get_nifti_filename(self, patient_name, time_point=None, rename_enabled=False):
        """
        Constructs the NIfTI filename based on the provided patient name and time point.
        Avoids duplicating time_point if already included in patient_name.
        """
        if rename_enabled:
            # If renaming, avoid appending if time_point is already part of patient_name
            if time_point and time_point not in patient_name:
                return f"{patient_name}_{time_point}.nii.gz"
            return f"{patient_name}.nii.gz"
        else:
            # Standard naming without renaming
            if time_point:
                return f"{patient_name}_{time_point}.nii.gz"
            return f"{patient_name}.nii.gz"

    def rename_files_in_folder(self, folder):
        """Renames files and logs original to new names in a text file."""
        rename_log_path = os.path.join(folder, "rename_log.txt")
        with open(rename_log_path, 'w') as log_file:
            log_file.write("Original Name\tNew Name\n")  # Header for clarity
            for i, file in enumerate(os.listdir(folder), start=self.starting_number.get()):
                base, ext = os.path.splitext(file)
                new_name = f"{self.data_nickname.get()}_{i}{ext}"
                original_path = os.path.join(folder, file)
                new_path = os.path.join(folder, new_name)
                
                # Rename file
                os.rename(original_path, new_path)
                
                # Log the rename operation
                log_file.write(f"{file}\t{new_name}\n")
                logging.info(f"Renamed {file} to {new_name}")


    def run_nnunet_prediction(self, nnUNet_IN, nnUNet_OUT):
        # Check if input and output paths exist before running nnUNet
        if not os.path.isdir(nnUNet_IN) or not os.path.isdir(nnUNet_OUT):
            messagebox.showerror("Error", "Invalid nnUNet input or output path.")
            return

        nnUNet_gui = nnUNetScript(self)  # Initialize nnUNet GUI component
        nnUNet_gui.input_path.set(nnUNet_IN)  # Set input path for nnUNet
        nnUNet_gui.output_path.set(nnUNet_OUT)  # Set output path for nnUNet
        nnUNet_gui.run_script()  # Run nnUNet prediction

    def calculate_airway_volumes(self, folder):
        """Calculates volume for each NIfTI file and saves results to a CSV file."""
        csv_path = os.path.join(folder, "volume_calculations.csv")
        with open(csv_path, mode='w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["Filename", "Volume (mm³)"])
            for file in Path(folder).glob("*.nii.gz"):
                nifti_img = nib.load(file)
                data = nifti_img.get_fdata()
                voxel_volume = np.prod(nifti_img.header.get_zooms())
                volume = np.sum(data) * voxel_volume
                writer.writerow([file.name, f"{volume:.2f}"])

    def export_predictions_to_stl(self, folder):
        STLConverterGUI(input_folder=folder).convert_files()
    
    def create_widgets(self):
        # Instruction frame at the top
        instruction_frame = ctk.CTkFrame(self)
        instruction_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        instruction_frame.grid_columnconfigure(0, weight=1)
        instruction_text = (
            "Instructions\n\n"
            "This program automatically detects if files are in a single list or organized by patient with multiple time points (e.g., T1, T2, T3).\n"
            "Outputs will be automatically ordered and labeled accordingly (e.g., P1T1, P1T2, P1T3). If the 'Rename files' option is selected, a text file will be generated, \n"
            "listing the original names and corresponding new names for each patient and time point.\n\n"
            
            "- Select tasks to perform:\n"
            "  * Anonymize: Removes personal information from DICOM files.\n"
            "  * Convert to NIfTI: Converts DICOM files to NIfTI format.\n"
            "  * Rename files: Applies a uniform name starting from a specified number.\n"
            "  * Run Prediction: Segments airways (3-12 mins per file).\n"
            "  * Calculate Volume: Outputs volume data as CSV.\n"
            "  * Export as STL: Saves 3D STL files of predictions.\n\n"
            
            "- Click 'Browse' to select the input folder. Based on the selected tasks, subfolders will be created automatically within the input folder:\n"
            "  * Anonymized DICOM files, Converted NIfTI files, Renamed files\n"
            "  * Predictions, Volume CSVs, STL exports\n\n"
            
            "- Additional information:\n"
            "  * Input files can be in DICOM or NIfTI format; outputs will be saved in NIfTI format.\n\n"
            
            "- After making your selections, click 'Start Processing' to begin."
        )


        ctk.CTkLabel(instruction_frame, text=instruction_text, anchor="w", justify="left").grid(row=0, column=0, sticky="w")

        # Input path frame
        path_frame = ctk.CTkFrame(self)
        path_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        path_frame.grid_columnconfigure(0, weight=1)

        # Input Folder
        ctk.CTkLabel(path_frame, text="Input Folder:").grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
        ctk.CTkEntry(path_frame, textvariable=self.input_path, width=500).grid(row=0, column=1, padx=(0, 10), sticky="ew")
        ctk.CTkButton(path_frame, text="Browse", command=self.browse_input_folder).grid(row=0, column=2, padx=(0, 10))

        # File Type Selection
        ctk.CTkLabel(path_frame, text="Starting File Type:").grid(row=2, column=0, padx=(0, 10), pady=5,  sticky="w")
        file_type_menu = ctk.CTkOptionMenu(path_frame, variable=self.file_type, values=["DICOM", "NIfTI"], command=self.update_task_options)
        file_type_menu.grid(row=2, column=1, sticky="w")

        # Task selection frame
        task_frame = ctk.CTkFrame(self)
        task_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        task_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        # Task Toggles
        ctk.CTkLabel(task_frame, text="Tasks:", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=5, sticky="w", padx=5, pady=(0, 10))

        # Anonymize and Rename, and Convert checkboxes

        self.convert_switch = ctk.CTkSwitch(task_frame, text="Convert to NIfTI", variable=self.convert_to_nifti)
        self.convert_switch.grid(row=1, column=0, sticky="w", pady=5, padx=20)
        
        # Inside the `create_widgets` method, attach `toggle_rename_fields` to `self.anonymize_rename_switch`
        self.anonymize_rename_switch = ctk.CTkSwitch(task_frame, text="Anonymize and Rename files", variable=self.rename_files, command=self.toggle_rename_fields)
        self.anonymize_rename_switch.grid(row=2, column=0, sticky="w", pady=5, padx=20)

        # Name to be applied label and entry
        nick_label = ctk.CTkLabel(task_frame, text="Name to be applied:")
        nick_label.grid(row=2, column=1, sticky="", pady=5, padx=(10, 5))
        self.nick_label_entry = ctk.CTkEntry(task_frame, textvariable=self.data_nickname, width=150)
        self.nick_label_entry.grid(row=2, column=2, sticky="w", pady=5)
        
        # Starting number label and entry
        start_number_label = ctk.CTkLabel(task_frame, text="Starting number:")
        start_number_label.grid(row=2, column=3, sticky="", pady=5, padx=(10, 5))
        self.start_number_entry = ctk.CTkEntry(task_frame, textvariable=self.starting_number, width=100)
        self.start_number_entry.grid(row=2, column=4, sticky="w", pady=5)

        # Initialize as disabled
        self.nick_label_entry.configure(state="disabled")
        self.start_number_entry.configure(state="disabled")

        # Additional task toggles
        ctk.CTkSwitch(task_frame, text="Run Prediction", variable=self.run_prediction).grid(row=3, column=0, padx=20, pady=5, sticky="w")
        ctk.CTkSwitch(task_frame, text="Calculate Volume", variable=self.calculate_volume).grid(row=4, column=0, padx=20, pady=5, sticky="w")
        ctk.CTkSwitch(task_frame, text="Export as STL", variable=self.export_stl).grid(row=5, column=0, padx=20, pady=5, sticky="w")

        # Start button
        ctk.CTkButton(self, text="Start Processing", command=self.start_processing).grid(row=3, column=0, pady=12)

if __name__ == "__main__":
    app = UnifiedAirwaySegmentationGUI()
    app.mainloop()
