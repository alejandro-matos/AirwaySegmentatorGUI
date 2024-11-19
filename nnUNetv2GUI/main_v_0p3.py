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
# ----   Not used in this code (yet)  ----
# from nnUNetGUIv3 import nnUNetScript
# from D2N_GUI import AnonDtoNGUI

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
                # Attempt to read the file as DICOM
                try:
                    pydicom.dcmread(item_path, stop_before_pixels=True)
                    return True
                except pydicom.errors.InvalidDicomError:
                    # Continue to check if the filename contains "DCM" if it's not valid DICOM
                    pass

                # Check if "DCM" is in the filename as an alternative identifier
                if "DCM" in item.upper() and not item.startswith("._"):
                    print(f"Filename suggests DICOM: {item_path}")
                    return True

        return False

    def anonymize_and_rename_dicom_structure(self, source_dir, destination_dir):
        global_index = self.starting_number.get()  # Start numbering from the specified start number
        self.renamed_folders = {}  # Reset dictionary for each processing session

        # Path for the renaming log file
        rename_log_path = os.path.join(destination_dir, "rename_log.txt")
        with open(rename_log_path, 'w') as log_file:
            log_file.write("Original Folder\tNew Folder\n")  # Header for clarity

            # Process each patient folder
            patient_folders = [
                d for d in os.listdir(source_dir)
                if os.path.isdir(os.path.join(source_dir, d))
            ]
            for patient_folder in patient_folders:
                patient_path = os.path.join(source_dir, patient_folder)

                # Check if the folder contains DICOM files directly (list structure)
                if self.contains_dicom_files(patient_path):
                    # List structure: DICOMs are directly within the patient folder
                    new_folder_path = os.path.join(destination_dir, f"{self.data_nickname.get()}_{global_index}")
                    os.makedirs(new_folder_path, exist_ok=True)

                    # Process and rename DICOM files using Nickname_global_index format
                    self.process_dicom_files(patient_path, new_folder_path, f"{self.data_nickname.get()}_{global_index}")

                    # Log the renaming for each scan in list structure
                    log_file.write(f"{patient_folder}\t{self.data_nickname.get()}_{global_index}\n")

                    # Increment the global index for each scan
                    global_index += 1
                else:
                    # Tree structure: process subfolders (time points) within the patient folder
                    subfolders = [
                        d for d in os.listdir(patient_path)
                        if os.path.isdir(os.path.join(patient_path, d))
                    ]
                    for time_point in subfolders:
                        time_point_path = os.path.join(patient_path, time_point)

                        # Assign a unique name based on the global index for each time point
                        time_point_nickname = f"{self.data_nickname.get()}_{global_index}"
                        self.renamed_folders[os.path.join(patient_folder, time_point)] = time_point_nickname

                        # Log the renaming with the unique global index
                        log_file.write(f"{os.path.join(patient_folder, time_point)}\t{time_point_nickname}\n")

                        if self.contains_dicom_files(time_point_path):
                            # Create a separate folder for each time point
                            new_folder_path = os.path.join(destination_dir, time_point_nickname)
                            os.makedirs(new_folder_path, exist_ok=True)

                            # Process and rename DICOM files within each time point using Nickname_global_index
                            self.process_dicom_files(time_point_path, new_folder_path, time_point_nickname)

                        # Increment the global index after each time point
                        global_index += 1

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
        global_index = self.starting_number.get()  # Start numbering from the specified start number
        self.renamed_files = {}  # Reset dictionary for each processing session

        # Path for the renaming log file
        rename_log_path = os.path.join(destination_dir, "rename_log.txt")
        os.makedirs(destination_dir, exist_ok=True)  # Ensure the destination directory exists

        with open(rename_log_path, 'w') as log_file:
            log_file.write("Original File\tNew File\n")  # Header for clarity

            # Traverse the source directory, including subdirectories if present
            for root, _, files in os.walk(source_dir):
                for file_name in files:
                    if file_name.endswith('.nii.gz'):
                        input_file_path = os.path.join(root, file_name)
                        
                        # Construct the new name with the global index
                        new_file_name = f"{self.data_nickname.get()}_{global_index}.nii.gz"
                        new_file_path = os.path.join(destination_dir, new_file_name)
                        
                        # Copy the file to the destination with the new name by reading and writing in binary mode
                        with open(input_file_path, 'rb') as f_src:
                            with open(new_file_path, 'wb') as f_dst:
                                f_dst.write(f_src.read())
                        
                        # Log only the original file name and new file name
                        log_file.write(f"{file_name}\t{new_file_name}\n")

                        # Increment the global index for each NIfTI file
                        global_index += 1


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

                    nifti_filename = self.get_nifti_filename(patient_name, time_point, rename_enabled=self.rename_files.get())
                    nifti_path = os.path.join(nifti_folder, nifti_filename)
                    sitk.WriteImage(image, nifti_path)
                    logging.info(f"NIfTI file saved at: {nifti_path}")

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
    
    # Need to check if it works when starting from prediction all the way to volume calc and with multiple files
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

        except Exception as e:
            logging.error("Error in volume calculation: %s", e)
            messagebox.showerror("Error", f"Failed to save volume calculation results: {e}")

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
    
    ## ------------------------------------------------------- ##
    ## ------------ STL Creation ----------------------------- ##
    ## ------------------------------------------------------- ##
    def nifti_to_stl(self,nifti_file_path, stl_file_path, threshold_value=1, decimate=True, decimate_target_reduction=0.5):
        try:
            # Load NIfTI file
            reader = vtk.vtkNIFTIImageReader()
            reader.SetFileName(nifti_file_path)
            reader.Update()
            
            # Apply vtkDiscreteFlyingEdges3D
            discrete_flying_edges = vtk.vtkDiscreteFlyingEdges3D()
            discrete_flying_edges.SetInputConnection(reader.GetOutputPort())
            discrete_flying_edges.SetValue(0, threshold_value)
            discrete_flying_edges.Update()
            
            output_polydata = discrete_flying_edges.GetOutput()

            # Apply decimation if requested
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
            smoothing_filter.SetRelaxationFactor(0.05)
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
    def create_widgets(self):
        # Instruction frame at the top
        instruction_frame = ctk.CTkFrame(self)
        instruction_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        instruction_frame.grid_columnconfigure(0, weight=1)
        instruction_text = (
            "     Instructions\n\n"
            "     This program automatically detects if files are in a single list or organized by patient with multiple time points (e.g., T1, T2, T3).\n"
            "     Outputs will be automatically ordered and labeled accordingly (e.g., P1T1, P1T2, P1T3). If the 'Rename files' option is selected, a text file will be generated, \n"
            "     listing the original names and corresponding new names for each patient and time point.\n\n"
            
            "     - Select tasks to perform:\n"
            "       * Convert to NIfTI: Converts DICOM (DCM or .dcm) files to compact NIfTI (.nii.gz) format.\n"
            "       * Anonymize and Rename: Removes identifying information from DCM file metadata, applies user-specified name and numbering to all files.\n"
            "       * Upper Airway Segmentation: Segments upper airway structures in 3-12 minutes per file, saving results with a '_seg' suffix for easy identification.\n"
            "       * Calculate Volume: Creates a .txt file containing the volumes of the upper airway segmentations that can be esasily imported into Excel.\n"
            "       * Export as STL: Saves 3D STL files of segmentations for 3D printing or CFD simulations.\n\n"
            
            "     - Click 'Browse' to select the input folder. Based on the selected tasks, subfolders will be created automatically within the input folder:\n"
            "       * CBCT_Renamed_Anonymized, NIfTI_Converted, Predictions, STL_Exports, Volume_Calculations\n\n"
            
            "     - Additional information:\n"
            "       * Input files can be in DICOM or NIfTI format; outputs will be saved in NIfTI format.\n\n"
            
            "     - After making your selections, click 'Start Processing' to begin."
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
        file_type_menu = ctk.CTkOptionMenu(path_frame, variable=self.file_type, values=["DICOM", "NIfTI"], command=self.update_file_options)
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
        self.nick_label_entry = ctk.CTkEntry(task_frame, textvariable=self.data_nickname, width=150)
        self.nick_label_entry.grid(row=2, column=2, sticky="w", pady=5)
        
        # Starting number label and entry
        start_number_label = ctk.CTkLabel(task_frame, text="Starting Number:")
        start_number_label.grid(row=2, column=3, sticky="", pady=5, padx=(10, 5))
        self.start_number_entry = ctk.CTkEntry(task_frame, textvariable=self.starting_number, width=100)
        self.start_number_entry.grid(row=2, column=4, sticky="w", pady=5)

        # Initialize as disabled
        self.nick_label_entry.configure(state="disabled")
        self.start_number_entry.configure(state="disabled")

        # Additional task toggles
        ctk.CTkSwitch(task_frame, text="Segment (Predict) Upper Airway", variable=self.run_prediction).grid(row=3, column=0, padx=20, pady=5, sticky="w")
        ctk.CTkSwitch(task_frame, text="Calculate Segmentation Volume", variable=self.calculate_volume).grid(row=4, column=0, padx=20, pady=5, sticky="w")
        ctk.CTkSwitch(task_frame, text="Export Segmentation as STL", variable=self.export_stl).grid(row=5, column=0, padx=20, pady=5, sticky="w")

        # Start button
        ctk.CTkButton(self, text="Start Processing", command=self.start_processing).grid(row=3, column=0, pady=12)

if __name__ == "__main__":
    app = UnifiedAirwaySegmentationGUI()
    app.mainloop()
