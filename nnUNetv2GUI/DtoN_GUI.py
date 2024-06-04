import tkinter as tk
from tkinter import messagebox, filedialog
import dicom2nifti
import os
from pathlib import Path
import sys
import styles
import pydicom

class AnonDtoNGUI(tk.Frame):
    def __init__(self, parent, home_callback):
        super().__init__(parent)
        self.parent = parent
        self.home_callback = home_callback
        self.configure(bg=styles.BG_COLOR)

        self.input_path = tk.StringVar()
        self.starting_number = tk.IntVar(value=1)  # Added starting number variable
        self.anonymize = tk.BooleanVar()
        self.convert_to_nifti = tk.BooleanVar()
        self.prepare_for_segmentation = tk.BooleanVar()

        self.create_widgets()

    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        abs_path = Path(base_path) / relative_path
        return abs_path.as_posix()

    def browse_input_path(self):
        selected_path = filedialog.askdirectory()
        if selected_path:
            self.input_path.set(selected_path)
            print(f"Input path set to: {selected_path}")

    def open_folder(self):
        input_path_str = self.input_path.get()
        if not input_path_str or not os.path.isdir(input_path_str):
            messagebox.showwarning("Input Error", "Please select a valid directory.")
        else:
            if sys.platform == "win32":
                os.startfile(input_path_str)
            elif sys.platform == "darwin":
                os.system(f"open {input_path_str}")
            else:
                os.system(f"xdg-open {input_path_str}")

    def anonymize_dicom_folder(self, input_folder, output_folder, patient_index):
        os.makedirs(output_folder, exist_ok=True)
        start_number = self.starting_number.get()
        for root, _, files in os.walk(input_folder):
            for i, file_name in enumerate(files):
                if file_name.lower().endswith(".dcm") or "DCM" in file_name:
                    input_file_path = os.path.join(root, file_name)
                    # Rename the file using the patient index and starting number
                    anonymized_file_name = f"Anon_{patient_index}_{start_number + i}.dcm"
                    output_file_path = os.path.join(output_folder, anonymized_file_name)
                    self.anonymize_dicom(input_file_path, output_file_path)

    def anonymize_dicom(self, input_file, output_file):
        dataset = pydicom.dcmread(input_file)
        tags_to_anonymize = [
            ("PatientName", "ANONYMIZED"),
            ("PatientID", "ANONYMIZED"),
            ("PatientBirthDate", "N/A"),
            ("PatientSex", "N/A"),
        ]
        for tag, value in tags_to_anonymize:
            if tag in dataset:
                dataset.data_element(tag).value = value
        dataset.save_as(output_file)

    def convert_files(self):
        input_path_str = self.input_path.get()
        output_path_str = self.input_path.get()
        anonymize = self.anonymize.get()
        convert_to_nifti = self.convert_to_nifti.get()
        prepare_for_segmentation = self.prepare_for_segmentation.get()

        print(f"Input path: {input_path_str}")
        print(f"Output path: {output_path_str}")
        print(f"Anonymize: {anonymize}")
        print(f"Convert to NIfTI: {convert_to_nifti}")
        print(f"Prepare for segmentation: {prepare_for_segmentation}")

        if not input_path_str:
            messagebox.showwarning("Input Error", "Please select the input directory.")
            return

        # Create a base anonymized directory at the same level as input_path_str
        base_anonymized_path = os.path.join(os.path.dirname(input_path_str), "Anonymized")
        os.makedirs(base_anonymized_path, exist_ok=True)

        patient_folders = [f for f in os.listdir(input_path_str) if os.path.isdir(os.path.join(input_path_str, f))]

        for patient_index, patient_folder in enumerate(patient_folders):
            patient_folder_path = os.path.join(input_path_str, patient_folder)
            anonymized_folder_name = f"Anon_{patient_index}"
            anonymized_folder_path = os.path.join(base_anonymized_path, anonymized_folder_name)

            if anonymize:
                self.anonymize_dicom_folder(patient_folder_path, anonymized_folder_path, patient_index)
            else:
                anonymized_folder_path = patient_folder_path

            if convert_to_nifti:
                output_patient_folder = os.path.join(anonymized_folder_path, "NIfTI")
                os.makedirs(output_patient_folder, exist_ok=True)
                try:
                    dicom2nifti.convert_directory(anonymized_folder_path, output_patient_folder, compression=True)
                except dicom2nifti.exceptions.ConversionError as e:
                    print(f"Error converting {anonymized_folder_path}: {e}")
                except Exception as e:
                    print(f"Unexpected error: {e}")

                for nifti_file in os.listdir(output_patient_folder):
                    if nifti_file.endswith('.nii') or nifti_file.endswith('.nii.gz'):
                        base_name, ext = os.path.splitext(nifti_file)
                        if ext == ".gz":
                            base_name, ext2 = os.path.splitext(base_name)
                            new_name = f"Anon_{patient_index}_{base_name}{ext2}{ext}"
                        else:
                            new_name = f"Anon_{patient_index}_{base_name}{ext}"
                        os.rename(os.path.join(output_patient_folder, nifti_file), os.path.join(output_patient_folder, new_name))

                if prepare_for_segmentation:
                    suffix = "_0000"
                    for nifti_file in os.listdir(output_patient_folder):
                        if nifti_file.endswith('.nii') or nifti_file.endswith('.nii.gz'):
                            base_name, ext = os.path.splitext(nifti_file)
                            if ext == ".gz":
                                base_name, ext2 = os.path.splitext(base_name)
                                new_name = f"{base_name}{suffix}{ext2}{ext}"
                            else:
                                new_name = f"{base_name}{suffix}{ext}"
                            os.rename(os.path.join(output_patient_folder, nifti_file), os.path.join(output_patient_folder, new_name))

        messagebox.showinfo("Process Complete", "The selected operations have been completed.")

    def create_widgets(self):
        home_button = tk.Button(self, text="Home", command=self.home_callback, bg='#FF9800', fg='white',
                                font=(styles.FONT_FAMILY, styles.BUTTON_FONT_SIZE), padx=styles.BUTTON_PADDING, pady=styles.BUTTON_PADDING)
        home_button.grid(row=0, column=0, padx=(10, 20), pady=(10, 20), sticky="W")

        text_widget = tk.Text(self, wrap='word', height=18, width=86, bg=styles.BG_COLOR, fg='white', font=(styles.FONT_FAMILY, 13))
        text_widget.insert(tk.END, """File Converter Module\n
        This module processes DICOM images by anonymizing them, converting them to NIfTI format,
        and renaming the files to meet the algorithm's naming convention for proper identification.
                   
        Instructions:
        - Use the toggle buttons to select tasks:
            - Anonymize: Removes personal information and numbers anonymized files starting 
                from the specified number in the "Starting number" line. A .txt file containing the 
                naming key relating the original and anonymized files is also created in this step.
            - Convert to NIfTI: Converts DICOM files to NIfTI (.nii.gz) format.
            - Add Suffix for Segmentation: Adds '_0000' to the file names for segmentation use.
        - Click 'Browse' to select the folder containing the files.
        - Input the starting number for anonymized files.
        - Click 'Start' to begin processing the selected tasks.
        - Once done, click 'Open Folder' to access the processed images and renaming key in the newly 
          created folder called "Processed_Images".""")
        text_widget.grid(row=1, column=0, columnspan=3, padx=20, pady=(10, 20))
        text_widget.tag_configure("bold", font=(styles.FONT_FAMILY, 18, 'bold'))
        text_widget.tag_configure("center", justify='center')
        text_widget.tag_add("bold", "1.0", "1.end")
        text_widget.tag_add("center", "1.0", "1.end")
        text_widget.configure(state='disabled')

        label_style_title = {'bg': styles.BG_COLOR, 'fg': 'white', 'font': (styles.FONT_FAMILY, styles.FONT_SIZE+4, 'bold')}
        label_style = {'bg': styles.BG_COLOR, 'fg': 'white', 'font': (styles.FONT_FAMILY, styles.FONT_SIZE, 'bold')}
        label_grid = {'sticky': tk.W, 'padx': 10, 'pady': (10, 5)}

        roww = 2

        task_label = tk.Label(self, text="Select tasks to perform:", **label_style_title).grid(row=roww, columnspan=3, **label_grid)

        anonymize_label = tk.Label(self, text="Anonymize", **label_style)
        anonymize_label.grid(row=roww+1, column=0, sticky="EW", padx=(20, 0))
        anonymize_toggle = tk.Checkbutton(self, variable=self.anonymize, bg=styles.BG_COLOR)
        anonymize_toggle.grid(row=roww+2, column=0, sticky="EW", padx=(20, 0))

        convert_label = tk.Label(self, text="Convert to NIfTI", **label_style)
        convert_label.grid(row=roww+1, column=1, sticky="EW", padx=(20, 0))
        convert_toggle = tk.Checkbutton(self, variable=self.convert_to_nifti, bg=styles.BG_COLOR)
        convert_toggle.grid(row=roww+2, column=1, sticky="EW", padx=(20, 0))

        segmentation_label = tk.Label(self, text="Add suffix for nnUNet segmentation", **label_style)
        segmentation_label.grid(row=roww+1, column=2, sticky="EW", padx=(20, 0))
        segmentation_toggle = tk.Checkbutton(self, variable=self.prepare_for_segmentation, bg=styles.BG_COLOR)
        segmentation_toggle.grid(row=roww+2, column=2, sticky="EW", padx=(20, 0))

        # Starting number for anonymized files
        start_number_label = tk.Label(self, text="Starting number:", **label_style).grid(row=roww+3, column=0, **label_grid)
        start_number_entry = tk.Entry(self, textvariable=self.starting_number, width=10)
        start_number_entry.grid(row=roww+3, column=1, sticky="W", padx=(0, 10))

        input_label = tk.Label(self, text="Select Folder:", **label_style).grid(row=roww+4, column=0, **label_grid)
        input_entry = tk.Entry(self, textvariable=self.input_path, width=50)
        input_entry.grid(row=roww+4, column=1, sticky="EW", padx=(0, 10))

        input_button = tk.Button(self, text="Browse", command=self.browse_input_path,font=(styles.FONT_FAMILY, styles.BUTTON_FONT_SIZE-2), padx=10, pady=0)
        input_button.grid(row=roww+4, column=2, sticky="W", padx=(10, 10))

        open_button = tk.Button(self, text="Open Folder", command=self.open_folder,font=(styles.FONT_FAMILY, styles.BUTTON_FONT_SIZE-2), padx=10, pady=0)
        open_button.grid(row=roww+4, column=2, sticky="E", padx=(0, 80))

        convert_button = tk.Button(self, text="Start", command=self.convert_files, bg='#2196F3', fg='white',
                                   font=(styles.FONT_FAMILY, styles.BUTTON_FONT_SIZE),  # Increase font size
                                   padx=20, pady=10)  # Increase padding
        convert_button.grid(row=roww+5, column=0, columnspan=3, padx=(100, 0), pady=(10, 20))

        
if __name__ == "__main__":
    root = tk.Tk()
    app = AnonDtoNGUI(root, root.destroy)  # For standalone testing, 'home' button will close the app
    app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
