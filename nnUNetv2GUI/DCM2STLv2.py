import tkinter as tk
from tkinter import messagebox, filedialog
import dicom2nifti
import os
from pathlib import Path
import sys
import subprocess
import threading
from PIL import Image, ImageTk
import numpy as np
import nibabel as nib
from skimage import measure
from stl import mesh
import styles

class CustomCheckButton(tk.Label):
    def __init__(self, parent, variable, on_image, off_image, command=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.variable = variable
        self.on_image = on_image
        self.off_image = off_image
        self.command = command
        self.configure(image=self.off_image, bg=styles.BG_COLOR)
        self.bind("<Button-1>", self.toggle)

    def toggle(self, event=None):
        if self.variable.get():
            self.variable.set(False)
            self.configure(image=self.off_image)
        else:
            self.variable.set(True)
            self.configure(image=self.on_image)
        
        if self.command:
            self.command()

class AirwaySegmenterGUI(tk.Frame):
    def __init__(self, parent, home_callback):
        super().__init__(parent)
        self.parent = parent
        self.home_callback = home_callback
        self.configure(bg=styles.BG_COLOR)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.starting_number = tk.IntVar(value=1)
        self.rename_files = tk.BooleanVar()
        self.data_nickname = tk.StringVar(value='Airways')

        self.setup_paths()
        self.load_icons()
        self.create_widgets()

    def setup_paths(self):
        self.parent_dir = os.path.dirname(os.getcwd())
        self.parent_dir2 = os.path.dirname(self.parent_dir)
        # Construct the path to the target folder and create path
        self.Path1 = Path(os.path.join(self.parent_dir2, 'Airways_v2', 'nnUNet_raw')).as_posix()
        self.Path2 = Path(os.path.join(self.parent_dir2, 'Airways_v2', 'nnUNet_results')).as_posix()
        self.Path3 = Path(os.path.join(self.parent_dir2, 'Airways_v2', 'nnUNet_preprocessed')).as_posix()

    def browse_input_path(self):
        selected_path = filedialog.askdirectory()
        if selected_path:
            self.input_path.set(selected_path)

    def load_icons(self):
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            checked_icon_path = os.path.join(base_dir, "Images", "checked.png")
            unchecked_icon_path = os.path.join(base_dir, "Images", "unchecked.png")

            image_size = 30

            checked_icon = Image.open(checked_icon_path).resize((image_size, image_size), Image.LANCZOS)
            self.checked_icon = ImageTk.PhotoImage(checked_icon)

            unchecked_icon = Image.open(unchecked_icon_path).resize((image_size, image_size), Image.LANCZOS)
            self.unchecked_icon = ImageTk.PhotoImage(unchecked_icon)

        except Exception as e:
            print(f"Error loading images: {e}")
            self.checked_icon = None
            self.unchecked_icon = None

    def open_folder(self):
        input_path_str = self.input_path.get()
        parent_directory = os.path.dirname(input_path_str)
        processed_dir = os.path.join(parent_directory, f"{os.path.basename(input_path_str)}_Processed_Images")
        if processed_dir:
            if not os.path.isdir(processed_dir):
                messagebox.showwarning("Directory Error", f"The directory {processed_dir} does not exist. Please ensure that the correct DICOM folder is selected and/or check that DICOM files have been  processed.")
            else:
                print(f"Opening folder: {processed_dir}")
                if sys.platform == "win32":
                    os.startfile(processed_dir)
                elif sys.platform == "darwin":
                    os.system(f"open {processed_dir}")
                else:
                    os.system(f"xdg-open {processed_dir}")

    def convert_files(self):
        input_path_str = self.input_path.get()
        rename_files = self.rename_files.get()
        data_nick = self.data_nickname.get()

        if not input_path_str:
            messagebox.showwarning("Input Error", "Please select the input directory.")
            return

        parent_directory = os.path.dirname(input_path_str)
        output_dir = os.path.join(parent_directory, f"{os.path.basename(input_path_str)}_Processed_Images")
        self.output_path.set(output_dir)

        central_nifti_folder = os.path.join(output_dir, "NIfTI")
        os.makedirs(central_nifti_folder, exist_ok=True)

        if rename_files:
            mapping_file_path = os.path.join(output_dir, "folder_mapping.txt")
            with open(mapping_file_path, "w") as mapping_file:
                mapping_file.write("Original Folder\tAnonymized Folder\n")

        patient_folders = [f for f in os.listdir(input_path_str) if os.path.isdir(os.path.join(input_path_str, f))]
        start_number = self.starting_number.get()
        nifti_filenames = []  # List to keep track of NIfTI filenames

        print(f"This is the output of patient_folders: {patient_folders}")
        for patient_index, patient_folder in enumerate(patient_folders, start=start_number):
            print(f"Processing patient folder: {patient_folder} with index {patient_index}")
            patient_folder_path = os.path.join(input_path_str, patient_folder)

            if rename_files:
                anonymized_folder_name = f"{data_nick}_{patient_index}"
                with open(mapping_file_path, "a") as mapping_file:
                    mapping_file.write(f"{patient_folder}\t{anonymized_folder_name}\n")
                patient_name = anonymized_folder_name
            else:
                anonymized_folder_name = patient_folder
                patient_name = patient_folder

            anonymized_folder_path = patient_folder_path

            try:
                dicom2nifti.convert_directory(anonymized_folder_path, central_nifti_folder, compression=True)
            except dicom2nifti.exceptions.ConversionError as e:
                print(f"Error converting {anonymized_folder_path}: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")

            nifti_files = [f for f in os.listdir(central_nifti_folder) if f.endswith('.nii') or f.endswith('.nii.gz')]
            for nifti_file in nifti_files:
                base_name, ext = os.path.splitext(nifti_file)
                suffix = "_0000"

                if ext == ".gz":
                    base_name, ext2 = os.path.splitext(base_name)
                    if rename_files:
                        new_name = f"{data_nick}_{patient_index}{suffix}{ext2}{ext}"
                    else:
                        new_name = f"{patient_folder}{suffix}{ext2}{ext}"

                new_path = os.path.join(central_nifti_folder, new_name)
                if not os.path.exists(new_path):
                    print(f"Renaming NIfTI file {nifti_file} to {new_name}")
                    os.rename(os.path.join(central_nifti_folder, nifti_file), new_path)
                
                nifti_filenames.append(new_name.replace('_0000.nii.gz', ''))  # Add the new NIfTI filename to the list and remove the suffix from name because the segmentation has no suffix

        # Pass the list of NIfTI filenames to the convert_niftis_to_stl function
        self.segment_airway(central_nifti_folder, output_dir)
        self.convert_niftis_to_stl(output_dir, nifti_filenames)


    def segment_airway(self, nifti_folder, output_dir):
        print(f"Segmenting airway using nnUNet on data in {nifti_folder}")

        try:
            # Set environment variables
            os.environ['nnUNet_raw'] = self.Path1
            os.environ['nnUNet_results'] = self.Path2
            os.environ['nnUNet_preprocessed'] = self.Path3

            result = subprocess.run([
                'nnUNetv2_predict', '-i', nifti_folder, '-o', os.path.join(output_dir, "Segmentation"),
                '-d', '13', '-c', '3d_fullres',
            ], capture_output=True, text=True)

            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, result.args, output=result.stdout, stderr=result.stderr)

        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to run the nnUNet prediction: {e.stderr}")


    def nifti_to_stl(self,nifti_file_path, stl_file_path, threshold_value=1, decimate=True, decimate_target_reduction=0.5):
        try:
            # Load NIfTI file
            reader = vtk.vtkNIFTIImageReader()
            reader.SetFileName(nifti_file_path)
            reader.Update()
            
            # Apply vtkDiscreteFlyingEdges3D
            discrete_flying_edges = vtk.vtkDiscreteFlyingEdges3D()
            discrete_flying_edges.SetInputConnection(reader.GetOutputPort())
            discrete_flying_edges.SetValue(0, threshold_value)  # Set the threshold value
            discrete_flying_edges.Update()
            
            # Output from vtkDiscreteFlyingEdges3D
            output_polydata = discrete_flying_edges.GetOutput()

            # Apply vtkDecimatePro for decimation (optional)
            if decimate:
                decimator = vtk.vtkDecimatePro()
                decimator.SetInputData(output_polydata)
                decimator.SetTargetReduction(decimate_target_reduction)  # Reduce to target percentage
                decimator.PreserveTopologyOn()
                decimator.Update()
                output_polydata = decimator.GetOutput()
            # else:
            #     output_polydata = smoothed_polydata1

            # Apply smoothing filter to reduce segmentation artifacts
            smoothing_filter = vtk.vtkSmoothPolyDataFilter()
            smoothing_filter.SetInputData(output_polydata)
            smoothing_filter.SetNumberOfIterations(5)
            smoothing_filter.SetRelaxationFactor(0.05)
            smoothing_filter.FeatureEdgeSmoothingOff()
            smoothing_filter.BoundarySmoothingOn()
            smoothing_filter.Update()
            output_polydata2 = smoothing_filter.GetOutput()

            # Load the NIfTI file using nibabel to get the affine matrix
            nifti_image = nib.load(nifti_file_path)
            affine_matrix = nifti_image.affine
            
            # Create the transformation matrix
            transform = vtk.vtkTransform()
            
            # Apply the rotation (180 degrees around the Z-axis)
            transform.RotateZ(180)
            
            # Apply the translation (shift down using the affine matrix)
            translation = affine_matrix[:3, 3]
            transform.Translate(translation[0], translation[1], translation[2])

            # Apply the transform to the polydata
            transform_filter = vtk.vtkTransformPolyDataFilter()
            transform_filter.SetInputData(output_polydata2)
            transform_filter.SetTransform(transform)
            transform_filter.Update()
            transformed_polydata = transform_filter.GetOutput()

            # Apply vtkPolyDataNormals
            normals = vtk.vtkPolyDataNormals()
            normals.SetInputData(transformed_polydata)
            normals.SetFeatureAngle(60.0)
            normals.Update()
            
            # Write to STL file
            stl_writer = vtk.vtkSTLWriter()
            stl_writer.SetFileTypeToBinary()
            stl_writer.SetFileName(stl_file_path)
            stl_writer.SetInputData(normals.GetOutput())
            stl_writer.Write()

        except Exception as e:
            messagebox.showerror("Conversion Error", f"Failed to convert {nifti_file_path} to STL. Error: {e}")

    def convert_niftis_to_stl(self, output_dir, nifti_filenames):
        input_path_str = os.path.join(output_dir, "Segmentation")
        output_path_str = os.path.join(output_dir, "STL")
        os.makedirs(output_path_str, exist_ok=True)
                
        if not nifti_filenames:
            messagebox.showwarning("Input Error", "No NIfTI files found in the selected input directory.")
            return

        for nifti_file in nifti_filenames:
            nifti_file_path = os.path.join(input_path_str, f"{nifti_file}{'.nii.gz'}")
            stl_file_path = os.path.join(output_path_str, f"{nifti_file}{'.stl'}")
            self.nifti_to_stl(nifti_file_path, stl_file_path, threshold_value=1, decimate=True, decimate_target_reduction=0.5)

        messagebox.showinfo("Conversion Complete", "All NIfTI files have been converted to STL files.")


    def toggle_rename_fields(self):
        if self.rename_files.get():
            self.nick_label_entry.config(state=tk.NORMAL)
            self.start_number_entry.config(state=tk.NORMAL)
        else:
            self.nick_label_entry.config(state=tk.DISABLED)
            self.start_number_entry.config(state=tk.DISABLED)

    def create_widgets(self):
        home_button = tk.Button(self, text="Home", command=self.home_callback, bg='#FF9800', fg='white',
                                font=(styles.FONT_FAMILY, styles.BUTTON_FONT_SIZE), padx=styles.BUTTON_PADDING, pady=styles.BUTTON_PADDING)
        home_button.grid(row=0, column=0, padx=(10, 20), pady=(10, 20), sticky="W")

        text_widget = tk.Text(self, wrap='word', height=18, width=86, bg=styles.BG_COLOR, fg='white', font=(styles.FONT_FAMILY, 13))
        text_widget.insert(tk.END, """File Converter Module\n
        This module processes DICOM images by converting them to NIfTI format,
        and renaming the files to meet the algorithm's naming convention for proper identification.
                   
        Instructions:
        - Use the toggle buttons to select tasks:
                - Rename files: Numbers anonymized files starting 
                    from the specified number in the "Starting number" line. A .txt file containing the 
                    naming key relating the original and anonymized files is also created in this step.
        - Click 'Browse' to select the folder containing the files.
        - Input the starting number for numbering the anonymized files.
        - Make sure that the folder contains only the DICOM files to be converted.
        - Click 'Start' to begin processing the selected tasks.
        - Once done, click 'Open Folder' to access the processed images and renaming key in the newly 
          created folder called "{Folder Name}_Processed_Images".""")
        text_widget.grid(row=1, column=0, columnspan=3, padx=20, pady=(10, 20))
        text_widget.tag_configure("bold", font=(styles.FONT_FAMILY, 18, 'bold'))
        text_widget.tag_configure("center", justify='center')
        text_widget.tag_add("bold", "1.0", "1.end")
        text_widget.tag_add("center", "1.0", "1.end")
        text_widget.configure(state='disabled')

        label_style = {'bg': styles.BG_COLOR, 'fg': 'white', 'font': (styles.FONT_FAMILY, styles.FONT_SIZE, 'bold')}
        label_grid = {'sticky': tk.W, 'padx': 10, 'pady': (15, 10)}
        button_style1 = {'font': (styles.FONT_FAMILY, styles.BUTTON_FONT_SIZE-2), 'padx': 10, 'pady': 0}
        button_style2 = {'bg': '#2196F3', 'fg': 'white', 'font': (styles.FONT_FAMILY, styles.BUTTON_FONT_SIZE), 'padx': 20, 'pady': 5}

        roww = 2

        rename_label = tk.Label(self, text="Rename files?", **label_style)
        rename_label.grid(row=roww, column=0, **label_grid)
        rename_toggle = CustomCheckButton(self, variable=self.rename_files, on_image=self.checked_icon, off_image=self.unchecked_icon, command=self.toggle_rename_fields)
        rename_toggle.grid(row=roww, column=0, sticky="E", padx=(0, 40), pady=(10, 5))

        nick_label = tk.Label(self, text="Name to be applied to files:", **label_style)
        nick_label.grid(row=roww, column=1, sticky="W", padx=(0, 0), pady=(10, 5))
        self.nick_label_entry = tk.Entry(self, textvariable=self.data_nickname, width=9)
        self.nick_label_entry.grid(row=roww, column=1, sticky="E", padx=(0, 30), pady=(10, 5))

        start_number_label = tk.Label(self, text="Starting number:", **label_style)
        start_number_label.grid(row=roww, column=2, sticky='W', padx=(10, 5), pady=(10, 5))
        self.start_number_entry = tk.Entry(self, textvariable=self.starting_number, width=5)
        self.start_number_entry.grid(row=roww, column=2, sticky="E", padx=(10, 80), pady=(10, 5))

        input_label = tk.Label(self, text="Select Folder:", **label_style)
        input_label.grid(row=roww + 1, column=0, **label_grid)
        input_entry = tk.Entry(self, textvariable=self.input_path, width=65)
        input_entry.grid(row=roww + 1, column=0, columnspan=2, sticky="W", padx=(130, 0))

        input_button = tk.Button(self, text="Browse", command=self.browse_input_path, **button_style1)
        input_button.grid(row=roww + 1, column=2, sticky="W", padx=(0, 10))

        open_button = tk.Button(self, text="Open Results Folder", command=self.open_folder, **button_style1)
        open_button.grid(row=roww+1, column=2, sticky="E", padx=(0, 10))

        convert_button = tk.Button(self, text="Start", command=self.convert_files, **button_style2)

        convert_button.grid(row=roww+6, column=0, columnspan=3, padx=(100, 0), pady=(10, 20))

        self.toggle_rename_fields()

if __name__ == "__main__":
    root = tk.Tk()
    app = AirwaySegmenterGUI(root, root.destroy)
    app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
