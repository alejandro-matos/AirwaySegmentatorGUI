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
import numpy as np
from STLConvGUI import STLConverterGUI
from tkinter.ttk import Progressbar
import vtk
import random  # Import the random module for shuffling
from natsort import natsorted 

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

        # Path setup for nnUNet data
        self.parent_dir = Path(os.getcwd()).parent
        self.parent_of_parent_dir = self.parent_dir.parent
        nnunet_folder = 'nnUNet_training_v2'
        self.Path1 = self.parent_of_parent_dir / nnunet_folder / 'nnUNet_raw'
        self.Path2 = self.parent_of_parent_dir / nnunet_folder / 'nnUNet_results'
        self.Path3 = self.parent_of_parent_dir / nnunet_folder / 'nnUNet_preprocessed'

        # Set the color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # Build the interface
        self.create_instruction_frame()  # Call the instruction frame function
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
            # Enable the fields and update colors
            self.nick_label_entry.configure(state="normal", fg_color="white", text_color="black")
            self.start_number_entry.configure(state="normal", fg_color="white", text_color="black")
        else:
            # Disable the fields and reset colors to their inactive appearance
            self.nick_label_entry.configure(state="disabled", fg_color="gray", text_color="darkgray")
            self.start_number_entry.configure(state="disabled", fg_color="gray", text_color="darkgray")


    def update_file_options(self, selected_file_type):
        """Enable/Disable options based on the file type selected."""
        if selected_file_type == "NIfTI":
            # Disable anonymize checkboxes
            self.convert_switch.configure(state="disabled")
            self.convert_to_nifti.set(False)  # Uncheck if already checked
            # self.anonymize_rename_switch.configure(state="disabled")
            # self.rename_files.set(False)
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

        # Check if the parent directory already has "_Processed" in its name
        parent_dir = Path(input_folder).parent
        if "_Processed" in parent_dir.name:
            output_folder = str(parent_dir)  # Use the existing parent directory
        else:
            # Create a new output folder with a "_Processed" suffix
            output_folder = os.path.join(parent_dir, f"{Path(input_folder).stem}_Processed")
            os.makedirs(output_folder, exist_ok=True)

        # Step 1: Anonymize and Rename if selected
        if self.rename_files.get():
            renamed_folder = os.path.join(output_folder, "Renamed_Anonymized")
            os.makedirs(renamed_folder, exist_ok=True)
            if self.file_type.get() == "NIfTI":
                self.rename_nifti_structure(input_folder, renamed_folder)
            else:
                self.anonymize_and_rename_dicom_structure(input_folder, renamed_folder)
                input_folder = renamed_folder  # Update input folder to renamed folder


        # Step 2: Convert to NIfTI if selected
        if self.convert_to_nifti.get():
            nifti_folder = os.path.join(output_folder, "NIfTI_Converted")
            os.makedirs(nifti_folder, exist_ok=True)
            self.convert_dicom_to_nifti(input_folder, nifti_folder)
            input_folder = nifti_folder  # Update input folder to NIfTI folder for further processing

        # Step 3: Run nnUNet prediction if selected
        if self.run_prediction.get():
             # Set prediction output folder
            prediction_folder = os.path.join(output_folder, "Segmentations")
            os.makedirs(prediction_folder, exist_ok=True)
            # Determine nnUNet_IN based on file type and conversion setting
            if self.file_type.get() == "NIfTI":
                # If already in NIfTI, use the input folder directly
                nnUNet_IN = input_folder
            elif self.file_type.get() == "DICOM":
                # Enforce conversion to NIfTI for prediction if the files are in DICOM format
                if not self.convert_to_nifti.get():
                    print('Automatically converting files from DICOM to NIfTI')
                # Convert DICOM to NIfTI
                nifti_folder = os.path.join(output_folder, "NIfTI_Converted")
                os.makedirs(nifti_folder, exist_ok=True)
                self.convert_dicom_to_nifti(input_folder, nifti_folder)
                nnUNet_IN = nifti_folder  # Use the converted NIfTI folder as input
            else:
                messagebox.showerror("Error", "Files must be either in NIfTI format or converted to NIfTI from DICOM.")
                return

            self.run_nnunet_prediction(output_folder, nnUNet_IN, prediction_folder)

        # Added the else to do if not doing prediction
        else:
            # Step 4: If only volume calculation is selected, run it directly on the input folder
            if self.calculate_volume.get():
                self.calculate_airway_volumes(input_folder, output_folder)

            # Step 5: Create STL from prediction
            if self.export_stl.get():
                stl_folder = os.path.join(output_folder, "STL_Exports")
                os.makedirs(stl_folder, exist_ok=True)
                self.export_predictions_to_stl(input_folder, stl_folder)

    def contains_dicom_files(self, folder):
        for item in os.listdir(folder):
            item_path = os.path.join(folder, item)
            # Check if the item is a file
            if os.path.isfile(item_path):
                try:
                    # Attempt to read the file as DICOM
                    pydicom.dcmread(item_path, stop_before_pixels=True)
                    return True  # If no exception, it's a valid DICOM
                except (pydicom.errors.InvalidDicomError, IsADirectoryError):
                    # Invalid DICOM or directory, continue checking other files
                    continue
        return False
        
    def generate_randomized_mapping(self, items, starting_index):
        """
        Generate a consistent mapping from item names to randomized indices.

        Parameters:
            items (list): List of items (folders or file names).
            starting_index (int): Starting index for renaming.

        Returns:
            dict: Mapping of original item names to randomized indices.
        """
        indices = list(range(starting_index, starting_index + len(items)))
        random.shuffle(indices)
        return dict(zip(items, indices))

    def anonymize_and_rename_dicom_structure(self, source_dir, destination_dir):
        """
        Renames and anonymizes DICOM files while skipping any directories located in folders containing DICOM files.
        """
        # Gather all `P#T#` folders (patient and timepoint combination)
        folders = []
        for root, subdirs, files in os.walk(source_dir):
            # Check if the current folder contains DICOM files
            if self.contains_dicom_files(root):
                # If DICOM files are found, ignore subdirectories and only process the files in this folder
                subdirs.clear()  # Skip all subdirectories in the current folder
                relative_path = os.path.relpath(root, source_dir)
                folders.append((root, relative_path))
        
        # Debug: Check if folders were found
        if not folders:
            logging.warning("No DICOM folders found in the source directory.")
            messagebox.showwarning("No Folders", "No DICOM folders containing files were found in the selected input directory.")
            return

        # Shuffle the list of folders to randomize the order
        random.shuffle(folders)

        # Create unique randomized indices for all folders
        total_folders = len(folders)
        indices = list(range(self.starting_number.get(), self.starting_number.get() + total_folders))

        # Map each shuffled folder to a unique randomized name
        folder_mapping = {relative_path: f"{self.data_nickname.get()}_{index}" for (_, relative_path), index in zip(folders, indices)}

        # Ensure the destination directory exists
        os.makedirs(destination_dir, exist_ok=True)

        # Path for the renaming log file
        rename_log_path = os.path.join(destination_dir, "rename_log.txt")

        # Open the log file for recording the renaming process
        with open(rename_log_path, 'w') as log_file:
            log_file.write("Original Folder\tNew Folder\n")  # Log header

            # Process each folder
            for relative_path, new_folder_name in folder_mapping.items():
                # Reconstruct the full original folder path
                original_folder_path = os.path.join(source_dir, relative_path)

                # Create the new folder in the destination directory
                new_folder_path = os.path.join(destination_dir, new_folder_name)
                os.makedirs(new_folder_path, exist_ok=True)

                logging.info(f"Renaming folder {relative_path} to {new_folder_name}")

                # Log the folder renaming
                log_file.write(f"{relative_path}\t{new_folder_name}\n")
                log_file.flush()  # Ensure the entry is written immediately

                # Get a filtered list of valid files
                valid_files = [
                    file_name for file_name in os.listdir(original_folder_path)
                    if os.path.isfile(os.path.join(original_folder_path, file_name)) and
                    not file_name.startswith("._")  # Exclude hidden/system files
                ]

                # Process each valid file
                for file_index, file_name in enumerate(valid_files, start=1):
                    input_file_path = os.path.join(original_folder_path, file_name)

                    # Anonymized file name
                    anonymized_file_name = f"{new_folder_name}_{file_index}.dcm"
                    output_file_path = os.path.join(new_folder_path, anonymized_file_name)

                    # Anonymize and copy the file
                    try:
                        self.anonymize_dicom(input_file_path, output_file_path, patient_name=new_folder_name)
                        # logging.info(f"Renamed {file_name} to {anonymized_file_name}")  # Logging the renaming of every file

                    except Exception as e:
                        logging.error(f"Error renaming file {file_name} in folder {relative_path}: {e}")
                        messagebox.showerror("Renaming Error", f"Failed to rename {file_name} in folder {relative_path}. Error: {e}")

        # After logging all names, rearrange alphabetically:
        rename_log_path = os.path.join(destination_dir, "rename_log.txt")
        self.rearrange_rename_log(rename_log_path)

    def rearrange_rename_log(self, rename_log_path):
        """
        Rearranges the entries in rename_log.txt to sort original folder names alphabetically.
        """
        try:
            with open(rename_log_path, 'r') as log_file:
                lines = log_file.readlines()

            # Preserve the header line
            header = lines[0]
            entries = lines[1:]  # Skip the header

            # Sort entries alphabetically by the original folder name (first column)
            sorted_entries = sorted(entries, key=lambda line: line.split("\t")[0])

            # Rewrite the log file with sorted entries
            with open(rename_log_path, 'w') as log_file:
                log_file.write(header)  # Write the header back
                log_file.writelines(sorted_entries)

            # logging.info("Successfully rearranged rename_log.txt to alphabetical order.")
        except Exception as e:
            logging.error(f"Error rearranging rename_log.txt: {e}")
            messagebox.showerror("Error", f"Failed to rearrange rename_log.txt. Error: {e}")


    def process_dicom_files(self, input_folder, output_folder, patient_name):
        """
        Anonymize and rename DICOM files in a specified folder.
        """
        file_index = 1  # Start numbering from 1 or any other desired start point
        for file_name in os.listdir(input_folder):
            input_file_path = os.path.join(input_folder, file_name)

            # Skip if it's a directory or unwanted files
            if os.path.isdir(input_file_path) or file_name.startswith("._") or file_name == ".DS_Store":
                continue

            # Process only DICOM files
            if self.contains_dicom_files(input_folder):  # Check if file is a DICOM
                anonymized_file_name = f"{patient_name}_{file_index}.dcm"
                output_file_path = os.path.join(output_folder, anonymized_file_name)
                
                # Anonymize and rename each DICOM file
                self.anonymize_dicom(input_file_path, output_file_path, patient_name)
                file_index += 1  # Increment only for valid files

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

    def rename_nifti_structure(self, source_dir, destination_dir):
        """
        Renames NIfTI files based on a randomized mapping, ensuring unique names for all files.
        """
        # Gather all NIfTI files
        nifti_files = []
        for root, _, files in os.walk(source_dir):
            for file_name in files:
                if file_name.endswith('.nii.gz'):
                    nifti_files.append((root, file_name))

        # Debug: Check if files were found
        if not nifti_files:
            logging.warning("No NIfTI files found in the source directory.")
            messagebox.showwarning("No Files", "No NIfTI files found in the selected input directory.")
            return

        # Create a unique randomized index for all files
        total_files = len(nifti_files)
        indices = list(range(self.starting_number.get(), self.starting_number.get() + total_files))
        random.shuffle(indices)

        # Map each file to a unique index
        file_to_index = {file: idx for file, idx in zip(nifti_files, indices)}

        # Ensure the destination directory exists
        os.makedirs(destination_dir, exist_ok=True)

        # Path for the renaming log file
        rename_log_path = os.path.join(destination_dir, "rename_log.txt")

        # Open the log file for recording the renaming process
        with open(rename_log_path, 'w') as log_file:
            log_file.write("Original File\tNew File\n")  # Log header

            # Process each NIfTI file
            for (root, file_name), unique_index in file_to_index.items():
                new_file_name = f"{self.data_nickname.get()}_{unique_index}.nii.gz"

                # Full paths for the input and renamed files
                input_file_path = os.path.join(root, file_name)
                new_file_path = os.path.join(destination_dir, new_file_name)

                # Debug: Log file paths
                logging.info(f"Renaming {input_file_path} to {new_file_path}")

                try:
                    # Rename (copy) the file
                    with open(input_file_path, 'rb') as f_src:
                        with open(new_file_path, 'wb') as f_dst:
                            f_dst.write(f_src.read())

                    # Log the renaming in the text file
                    log_file.write(f"{file_name}\t{new_file_name}\n")
                    logging.info(f"Successfully renamed {file_name} to {new_file_name}")

                except Exception as e:
                    logging.error(f"Error renaming file {file_name}: {e}")
                    messagebox.showerror("Renaming Error", f"Failed to rename {file_name}. Error: {e}")


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
                    
                    # Ensure no interpolation or resampling
                    reader.MetaDataDictionaryArrayUpdateOn()
                    image = reader.Execute()
                    
                    # Extract and log original voxel spacing
                    spacing = image.GetSpacing()
                    # logging.info(f"Original voxel spacing (x, y, z): {spacing}") # Logging voxel spacing in all 3 directions
                    
                    # Correct potential flipping in direction
                    direction = image.GetDirection()
                    if direction[8] < 0:
                        image = sitk.Flip(image, [False, False, True])
                        spacing = image.GetSpacing()  # Re-check after flipping
                        logging.info(f"Flipped image. New voxel spacing (x, y, z): {spacing}")
                    
                    # Verify and log slice positions
                    slice_positions = [
                        float(image.TransformIndexToPhysicalPoint([0, 0, z])[2])
                        for z in range(image.GetSize()[2])
                    ]
                    slice_differences = [
                        round(slice_positions[i+1] - slice_positions[i], 5)
                        for i in range(len(slice_positions) - 1)
                    ]
                    #logging.info(f"Slice position differences in z-direction: {slice_differences}") # Logging the voxel spacing in the z direction
                    
                    # Save as NIfTI
                    nifti_filename = self.get_nifti_filename(patient_name, time_point, rename_enabled=self.rename_files.get())
                    nifti_path = os.path.join(nifti_folder, nifti_filename)
                    sitk.WriteImage(image, nifti_path)
                    # logging.info(f"NIfTI file saved at: {nifti_path}") # Logging NIfTI saved location

            # Main conversion loop
            patient_folders = [
                d for d in os.listdir(input_folder)
                if os.path.isdir(os.path.join(input_folder, d))
            ]
            for patient_folder in patient_folders:
                patient_path = os.path.join(input_folder, patient_folder)

                # Determine patient name based on renaming
                if self.rename_files.get():
                    patient_name = self.renamed_folders.get(patient_folder, patient_folder)
                else:
                    patient_name = patient_folder

                if self.contains_dicom_files(patient_path):
                    # Process DICOM files in this folder and ignore subfolders
                    process_dicom_series(patient_path, patient_name)
                else:
                    # Process subfolders
                    subfolders = [
                        d for d in os.listdir(patient_path)
                        if os.path.isdir(os.path.join(patient_path, d))
                    ]
                    for time_point in subfolders:
                        time_point_path = os.path.join(patient_path, time_point)
                        if self.contains_dicom_files(time_point_path):
                            # Determine time point name based on renaming
                            if self.rename_files.get():
                                time_point_name = f"{patient_name}_{time_point}"
                            else:
                                time_point_name = f"{patient_name}_{time_point}"
                            process_dicom_series(time_point_path, patient_name, time_point=time_point)
                        else:
                            logging.warning(f"No DICOM files found in {time_point_path}. Skipping.")
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

    # ------------ NNUNET SECTION --------------------------------------
    def run_nnunet_prediction(self, output_folder, nnUNet_IN, nnUNet_OUT):
        # Set up the loading dialog with a progress bar
        loading = ctk.CTkToplevel(self)
        loading.title('Processing')
        label_font = ("Arial", 20)
        ctk.CTkLabel(loading, text='Prediction is running, please wait...', font=label_font).pack(pady=10, padx=10)
        
        progress = Progressbar(loading, orient='horizontal', length=300, mode='indeterminate')
        progress.pack(pady=10)
        progress.start()

        loading.grab_set()

        def script_execution():
            if not nnUNet_IN or not nnUNet_OUT:
                messagebox.showerror("Error", "Path to CBCT files in NIfTI format and/or Predictions folder not selected/valid")
                loading.destroy()
                return

            # Set environment variables, if not already set
            os.environ.setdefault('nnUNet_raw', str(self.Path1))
            os.environ.setdefault('nnUNet_results', str(self.Path2))
            os.environ.setdefault('nnUNet_preprocessed', str(self.Path3))

            self.suffix_files(nnUNet_IN)

            try:
                result = subprocess.run([
                    'nnUNetv2_predict', '-i', nnUNet_IN, '-o', nnUNet_OUT,
                    '-d', '14', '-c', '3d_fullres', '-f', 'all',
                ], capture_output=True, text=True)

                logging.info('stdout: %s', result.stdout)
                logging.error('stderr: %s', result.stderr)

                result.check_returncode()

                
            except subprocess.CalledProcessError as e:
                logging.error("Error: %s", e.stderr)
                messagebox.showerror("Error", f"Failed to run nnUNet prediction: {e.stderr}")
            except Exception as e:
                logging.error("Unexpected error: %s", str(e))
                messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")
            finally:
                # Rename file to include _seg
                self.rename_output_files(nnUNet_OUT)
                self.remove_nnunet_internal(nnUNet_OUT)
                # Calculate volume also, after prediction
                self.calculate_airway_volumes(nnUNet_OUT, output_folder)
                if self.export_stl.get():
                    stl_folder = os.path.join(output_folder, "STL_Exports")
                    os.makedirs(stl_folder, exist_ok=True)
                    self.export_predictions_to_stl(nnUNet_OUT, stl_folder)
                progress.stop()
                loading.destroy()

        threading.Thread(target=script_execution).start()
    
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
    
    def remove_nnunet_internal(self, nnUNet_OUT):
        # Loop through all files in the specified nnUNet_OUT
        for filename in os.listdir(nnUNet_OUT):
            # Check if the file ends with .json
            if filename.endswith('.json'):
                # Construct the full file path
                file_path = os.path.join(nnUNet_OUT, filename)
                # Remove the file
                os.remove(file_path)
                print(f"Removed: {file_path}")
    
    # Need to check if it works when starting from prediction all the way to volume calc and with multiple files tk
    def calculate_airway_volumes(self, input_path, output_path, file_format="txt"):
        if not os.path.exists(input_path):
            messagebox.showwarning("Path Error", "Input path for volume calculation does not exist.")
            return

        volume_results = []
        for file in Path(input_path).glob("*.nii.gz"):
            volume = self.calculate_volume_from_file(file)
            volume_results.append((file.name, volume))

        try:
            file_path = Path(output_path) / "Volume Calculations.txt"
            with open(file_path, "w") as f:
                f.write("Filename\tVolume (mm^3)\n")
                for filename, volume in volume_results:
                    f.write(f"{filename}\t{volume:.2f}\n")
                    f.flush()  # Ensure the entry is written immediately
                    print(file_path)

        except Exception as e:
            logging.error("Error in volume calculation: %s", e)
            messagebox.showerror("Error", f"Failed to save volume calculation results: {e}")
        print(file_path)
        self.rearrange_volume_calculations(file_path)

    def calculate_volume_from_file(self, file_path, airway_label=1):
        """
        Calculate the volume of the airway from a NIfTI file.

        Parameters:
        - file_path (Path): Path to the .nii.gz file
        - airway_label (int): Label used for the airway segmentation in the mask (default is 1)

        Returns:
        - total_volume (float): Volume in ml^3
        """
        try:
            # Load the NIfTI file
            nifti_img = nib.load(file_path)
            data = nifti_img.get_fdata()

            # Log the affine matrix and zooms for debugging
            affine = nifti_img.affine
            voxel_sizes = nifti_img.header.get_zooms()  # Voxel dimensions in mm
            # --- Login file path and info
            #logging.info(f"File: {file_path}")
            #logging.info(f"Affine matrix: \n{affine}")
            #logging.info(f"Voxel dimensions (in mm): {voxel_sizes}")

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
    
    def rearrange_volume_calculations(self, file_path):
        """
        Rearranges the entries in the volume calculation file to sort filenames in natural order.
        """
        try:
            # Read the contents of the file
            with open(file_path, 'r') as f:
                lines = f.readlines()

            # Separate the header from the data
            header = lines[0]
            entries = lines[1:]

            # Sort the entries in natural order based on the filename
            sorted_entries = natsorted(entries, key=lambda line: line.split("\t")[0])

            # Write the rearranged content back to the file
            with open(file_path, 'w') as f:
                f.write(header)  # Write the header first
                f.writelines(sorted_entries)  # Write the sorted entries

            logging.info(f"Rearranged volume calculations in natural order: {file_path}")

        except Exception as e:
            logging.error(f"Error rearranging volume calculations: {e}")
            messagebox.showerror("Error", f"Failed to rearrange volume calculations: {e}")
    
    ## ------------------------------------------------------- ##
    ## ------------ STL Creation ----------------------------- ##
    ## ------------------------------------------------------- ##
    def nifti_to_stl(self, nifti_file_path, stl_file_path, threshold_value=1, decimate=True, decimate_target_reduction=0.5):
        try:
            # Load NIfTI file
            reader = vtk.vtkNIFTIImageReader()
            reader.SetFileName(nifti_file_path)
            reader.Update()

            # Add padding to ensure closed surfaces
            pad_filter = vtk.vtkImageConstantPad()
            pad_filter.SetInputConnection(reader.GetOutputPort())
            
            # Set padding: Add one layer of zero-value voxels on all sides
            extent = reader.GetDataExtent()
            pad_filter.SetOutputWholeExtent(
                extent[0] - 1, extent[1] + 1,  # X-axis padding
                extent[2] - 1, extent[3] + 1,  # Y-axis padding
                extent[4] - 1, extent[5] + 1   # Z-axis padding
            )
            pad_filter.SetConstant(0)  # Fill padding with zero
            pad_filter.Update()

            # Apply vtkDiscreteFlyingEdges3D
            discrete_flying_edges = vtk.vtkDiscreteFlyingEdges3D()
            discrete_flying_edges.SetInputConnection(pad_filter.GetOutputPort())
            discrete_flying_edges.SetValue(0, threshold_value)
            discrete_flying_edges.Update()

            output_polydata = discrete_flying_edges.GetOutput()

            # Apply decimation to reduce file size
            if decimate:
                decimator = vtk.vtkDecimatePro()
                decimator.SetInputData(output_polydata)
                decimator.SetTargetReduction(decimate_target_reduction)
                decimator.PreserveTopologyOn()
                decimator.Update()
                output_polydata = decimator.GetOutput()

            # Apply smoothing
            smoothing_filter = vtk.vtkSmoothPolyDataFilter()
            smoothing_filter.SetInputData(output_polydata)
            smoothing_filter.SetNumberOfIterations(5)
            smoothing_filter.SetRelaxationFactor(0.1)
            smoothing_filter.FeatureEdgeSmoothingOff()
            smoothing_filter.BoundarySmoothingOn()
            smoothing_filter.Update()
            output_polydata = smoothing_filter.GetOutput()

            # Get QForm matrix
            qform_matrix = reader.GetQFormMatrix()

            # Create IJK to RAS transformation
            ijk_to_ras = vtk.vtkMatrix4x4()
            ijk_to_ras.DeepCopy(qform_matrix)

            # Adjust for VTK's coordinate system
            flip_xy = vtk.vtkMatrix4x4()
            flip_xy.SetElement(0, 0, -1)
            flip_xy.SetElement(1, 1, -1)

            vtk.vtkMatrix4x4.Multiply4x4(flip_xy, ijk_to_ras, ijk_to_ras)

            # Create transformation matrix
            transform = vtk.vtkTransform()
            transform.SetMatrix(ijk_to_ras)

            # Apply transformation
            transform_filter = vtk.vtkTransformPolyDataFilter()
            transform_filter.SetInputData(output_polydata)
            transform_filter.SetTransform(transform)
            transform_filter.Update()
            transformed_polydata = transform_filter.GetOutput()

            # Compute normals
            normals = vtk.vtkPolyDataNormals()
            normals.SetInputData(transformed_polydata)
            normals.SetFeatureAngle(60.0)
            normals.ConsistencyOn()
            normals.SplittingOff()
            normals.Update()

            # Write STL file
            stl_writer = vtk.vtkSTLWriter()
            stl_writer.SetFileTypeToBinary()
            stl_writer.SetFileName(stl_file_path)
            stl_writer.SetInputData(normals.GetOutput())
            stl_writer.Write()

        except Exception as e:
            messagebox.showerror("Conversion Error", f"Failed to convert {nifti_file_path} to STL. Error: {e}")


    def export_predictions_to_stl(self,input_path_str,output_path_str):

        if not input_path_str or not output_path_str:
            messagebox.showwarning("Input Error", "Please select both input and output directories.")
            return

        nifti_files = [f for f in os.listdir(input_path_str) if f.endswith('.nii') or f.endswith('.nii.gz')]
        if not nifti_files:
            messagebox.showwarning("Input Error", "No NIfTI files found in the selected input directory.")
            return

        for nifti_file in nifti_files:
            nifti_file_path = os.path.join(input_path_str, nifti_file)
            base_name = os.path.splitext(os.path.splitext(nifti_file)[0])[0]
            stl_file_path = os.path.join(output_path_str, f"{base_name}.stl")
            print(f"The base name is {base_name}")
            print(f"The stl_file_path is {stl_file_path}")
            self.nifti_to_stl(nifti_file_path, stl_file_path, threshold_value=1, decimate=True, decimate_target_reduction=0.5)
    
    ## ------------------------------------------------------- ##
    ## ------------ GUI Widgets ------------------------------ ##
    ## ------------------------------------------------------- ##
    def create_instruction_frame(self):
        instruction_frame = ctk.CTkFrame(self)
        instruction_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        instruction_frame.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(
            instruction_frame, 
            text="Instructions for Using the Upper Airway Segmentation Tool",
            font=("Arial", 16, "bold"),  # Bold for the title
            anchor="w"
        ).grid(row=0, column=0, sticky="w", pady=(0, 0))

        # Step 1
        ctk.CTkLabel(
            instruction_frame, 
            text="1. Understand the Workflow:",
            font=("Arial", 12, "bold"),  # Bold for section headings
            anchor="w"
        ).grid(row=1, column=0, sticky="w", pady=(0, 0))

        ctk.CTkLabel(
            instruction_frame, 
            text=(
                "- Files to be converted can be organized as:\n"
                "       • A single list of files.\n"
                "       • Grouped by patient with multiple time points within each patient folder (e.g., T1, T2, T3).\n"
                "- Input files can be either DICOM or NIfTI.\n"
                "- are saved in NIfTI format for further processing.\n"
                "- If 'Rename Files' is selected, a log file called 're' tracks name changes."
            ),
            font=("Arial", 11),  # Normal font for text
            anchor="w",
            justify="left"
        ).grid(row=2, column=0, sticky="w", padx=10)

        # Step 2
        ctk.CTkLabel(
            instruction_frame, 
            text="2. Available Tasks:",
            font=("Arial", 12, "bold"),  # Bold for section headings
            anchor="w"
        ).grid(row=3, column=0, sticky="w", pady=(0, 0))

        ctk.CTkLabel(
            instruction_frame, 
            text=(
                "- Convert to NIfTI: Converts DICOM files to NIfTI format.\n"
                "- Anonymize and Rename: Removes identifying information from DICOM file metadata, applies user-specified name and numbering to all files.\n"
                "- Upper Airway Segmentation: Segments upper airway structures in 3-12 minutes per file, saving results with a '_seg' suffix for easy identification.\n"
                "- Calculate Volume: Creates a .txt file containing the volumes of the airway segmentations that can be easily imported into Excel.\n"
                "- Export as STL: Saves 3D STL files of segmentations for 3D printing or CFD simulations."
            ),
            font=("Arial", 11),  # Normal font for text
            anchor="w",
            justify="left"
        ).grid(row=4, column=0, sticky="w", padx=10)

        # Step 3
        ctk.CTkLabel(
            instruction_frame, 
            text="3. Folder Structure:",
            font=("Arial", 12, "bold"),  # Bold for section headings
            anchor="w"
        ).grid(row=5, column=0, sticky="w", pady=(0, 0))

        ctk.CTkLabel(
            instruction_frame, 
            text=(
                "- Select the input folder with 'Browse'.\n"
                "- Subfolders are created as needed, such as: CBCT_Renamed_Anonymized, NIfTI_Converted, Predictions, STL_Exports, Volume_Calculations"),
            font=("Arial", 11),  # Normal font for text
            anchor="w",
            justify="left"
        ).grid(row=6, column=0, sticky="w", padx=10)

        # Step 5
        ctk.CTkLabel(
            instruction_frame, 
            text="4. Start Processing:",
            font=("Arial", 12, "bold"),  # Bold for section headings
            anchor="w"
        ).grid(row=9, column=0, sticky="w", pady=(0, 0))

        ctk.CTkLabel(
            instruction_frame, 
            text=(
                "- Configure the options you need by selecting the desired tasks.\n"
                "- After setup, click 'Start Processing' to begin.\n"
                "- The tool will guide you through the steps and log the progress."
            ),
            font=("Arial", 11),  # Normal font for text
            anchor="w",
            justify="left"
        ).grid(row=10, column=0, sticky="w", padx=10)

    def create_widgets(self):
        # Input path frame
        path_frame = ctk.CTkFrame(self)
        path_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        path_frame.grid_columnconfigure(0, weight=1)

        # Input Folder
        ctk.CTkLabel(path_frame, text="Input Folder:").grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
        ctk.CTkEntry(path_frame, textvariable=self.input_path, width=500, fg_color="white", text_color="black").grid(row=0, column=1, padx=(0, 10), sticky="ew")
        ctk.CTkButton(path_frame, text="Browse", command=self.browse_input_folder, font=("Times_New_Roman", 14, "bold")).grid(row=0, column=2, padx=(0, 10))

        # File Type Selection
        ctk.CTkLabel(path_frame, text="Starting File Type:").grid(row=2, column=0, padx=(0, 10), pady=5,  sticky="w")
        file_type_menu = ctk.CTkOptionMenu(path_frame, variable=self.file_type, values=["DICOM", "NIfTI"], command=self.update_file_options, font=("Times_New_Roman", 14, "bold"))
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
        nick_label = ctk.CTkLabel(task_frame, text="New File Name:")
        nick_label.grid(row=2, column=1, sticky="", pady=5, padx=(10, 5))
        self.nick_label_entry = ctk.CTkEntry(task_frame, textvariable=self.data_nickname, width=150, fg_color="gray", text_color="darkgray")
        self.nick_label_entry.grid(row=2, column=2, sticky="w", pady=5)
        
        # Starting number label and entry
        start_number_label = ctk.CTkLabel(task_frame, text="Starting Number:")
        start_number_label.grid(row=2, column=3, sticky="", pady=5, padx=(10, 5))
        self.start_number_entry = ctk.CTkEntry(task_frame, textvariable=self.starting_number, width=100, fg_color="gray", text_color="darkgray")
        self.start_number_entry.grid(row=2, column=4, sticky="w", pady=5)

        # Initialize as disabled
        self.nick_label_entry.configure(state="disabled")
        self.start_number_entry.configure(state="disabled")

        # Additional task toggles
        ctk.CTkSwitch(task_frame, text="Segment (Predict) Upper Airway", variable=self.run_prediction).grid(row=3, column=0, padx=20, pady=5, sticky="w")
        ctk.CTkSwitch(task_frame, text="Calculate Segmentation Volume", variable=self.calculate_volume).grid(row=4, column=0, padx=20, pady=5, sticky="w")
        ctk.CTkSwitch(task_frame, text="Export Segmentation as STL", variable=self.export_stl).grid(row=5, column=0, padx=20, pady=5, sticky="w")

        # Start button
        ctk.CTkButton(self, text="Start Processing", command=self.start_processing, font=("Times_New_Roman", 14, "bold")).grid(row=3, column=0, pady=5)

if __name__ == "__main__":
    app = UnifiedAirwaySegmentationGUI()
    app.mainloop()