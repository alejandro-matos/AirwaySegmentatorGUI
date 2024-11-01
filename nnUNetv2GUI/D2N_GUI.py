import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
from pathlib import Path
import sys
import pydicom
import SimpleITK as sitk
import styles

class AnonDtoNGUI(ctk.CTkFrame):
    def __init__(self, parent, home_callback):
        super().__init__(parent)
        self.parent = parent
        self.home_callback = home_callback


        self.input_path = ctk.StringVar()
        self.output_path = ctk.StringVar()
        self.starting_number = ctk.IntVar(value=1)
        self.anonymize = ctk.BooleanVar()
        self.convert_to_nifti = ctk.BooleanVar()
        self.rename_files = ctk.BooleanVar()
        self.data_nickname = ctk.StringVar(value='Airways')

        self.create_widgets()
        # Adjust grid configuration for vertical centering
        self.grid_columnconfigure(0, weight=1)

    def resource_path(self, relative_path):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        abs_path = Path(base_path) / relative_path
        return abs_path.as_posix()

    def browse_input_path(self):
        selected_path = filedialog.askdirectory()
        if selected_path:
            self.input_path.set(selected_path)
            print(f"Input path set to: {selected_path}")

    def browse_output_path(self):
        selected_path = filedialog.askdirectory()
        if selected_path:
            self.output_path.set(selected_path)
            print(f"Output path set to: {selected_path}")

    def open_folder(self):
        input_path_str = self.input_path.get()
        parent_directory = os.path.dirname(input_path_str)
        processed_dir = os.path.join(parent_directory, f"{os.path.basename(input_path_str)}_ConvertedFiles")
        if processed_dir:
            if not os.path.isdir(processed_dir):
                messagebox.showwarning("Directory Error", f"The directory {processed_dir} does not exist. Please ensure that the correct folder is selected and/or that it has been processed.")
            else:
                print(f"Opening folder: {processed_dir}")
                if sys.platform == "win32":
                    os.startfile(processed_dir)
                elif sys.platform == "darwin":
                    os.system(f"open {processed_dir}")
                else:
                    os.system(f"xdg-open {processed_dir}")

    def anonymize_dicom(self, input_file, output_file, patient_name):
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

    def convert_dicom_to_nifti(self, dicom_folder, output_file):
        print(f"Converting DICOM folder: {dicom_folder}")
        print(f"Output file: {output_file}")

        reader = sitk.ImageSeriesReader()
        dicom_names = reader.GetGDCMSeriesFileNames(dicom_folder)
        reader.SetFileNames(dicom_names)
        image = reader.Execute()

        direction = image.GetDirection()
        if direction[8] < 0:
            image = sitk.Flip(image, [False, False, True])

        sitk.WriteImage(image, output_file)

        print(f"Image size: {image.GetSize()}")
        print(f"Image spacing: {image.GetSpacing()}")
        print(f"Image origin: {image.GetOrigin()}")
        print(f"Image direction: {image.GetDirection()}")

        print(f"NIfTI file saved: {output_file}")

    def convert_files(self):
        input_path_str = self.input_path.get()
        if not input_path_str:
            messagebox.showwarning("Input Error", "Please select the input directory.")
            return

        parent_directory = os.path.dirname(input_path_str)
        output_dir = os.path.join(parent_directory, f"{os.path.basename(input_path_str)}_ConvertedFiles")
        self.output_path.set(output_dir)

        anonymize = self.anonymize.get()
        convert_to_nifti = self.convert_to_nifti.get()
        rename_files = self.rename_files.get()
        data_nick = self.data_nickname.get()

        if convert_to_nifti:
            central_nifti_folder = os.path.join(output_dir, "NIfTI")
            os.makedirs(central_nifti_folder, exist_ok=True)

        if rename_files:
            mapping_file_path = os.path.join(output_dir, "folder_mapping.txt")
            with open(mapping_file_path, "w") as mapping_file:
                mapping_file.write("Original Folder\tAnonymized Folder\n")

        patient_folders = [f for f in os.listdir(input_path_str) if os.path.isdir(os.path.join(input_path_str, f))]
        start_number = self.starting_number.get()
        print(f"These are the patient folders: {patient_folders}")
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

            if anonymize:
                if rename_files:
                    base_anonymized_path = os.path.join(output_dir, "AnonymizedRenamed DICOMs")
                else:
                    base_anonymized_path = os.path.join(output_dir, "Anonymized DICOMs")
                os.makedirs(base_anonymized_path, exist_ok=True)
                anonymized_folder_path = os.path.join(base_anonymized_path, anonymized_folder_name)
                self.anonymize_dicom_folder(patient_folder_path, anonymized_folder_path, patient_index, patient_name)
            else:
                anonymized_folder_path = patient_folder_path

            if convert_to_nifti:
                try:
                    if anonymize:
                        source_folder = anonymized_folder_path
                    else:
                        source_folder = patient_folder_path
                    
                    if rename_files:
                        output_filename = f"{data_nick}_{patient_index}.nii.gz"
                    else:
                        output_filename = f"{patient_folder}.nii.gz"
                    
                    output_file = os.path.join(central_nifti_folder, output_filename)
                    self.convert_dicom_to_nifti(source_folder, output_file)
                except Exception as e:
                    print(f"Error converting {source_folder}: {e}")

        messagebox.showinfo("Process Complete", "The selected operations have been completed.")

    def anonymize_dicom_folder(self, input_folder, output_folder, patient_index, patient_name):
        os.makedirs(output_folder, exist_ok=True)
        start_number = self.starting_number.get()
        data_nick = self.data_nickname.get()
        print(f"Anonymizing DICOM folder: {input_folder} -> {output_folder}")
        for root, _, files in os.walk(input_folder):
            for i, file_name in enumerate(files):
                if file_name.lower().endswith(".dcm") or "DCM" in file_name:
                    input_file_path = os.path.join(root, file_name)
                    if self.rename_files.get():
                        anonymized_file_name = f"{data_nick}_{patient_index}_{1 + i}.dcm"
                    else:
                        anonymized_file_name = file_name
                    output_file_path = os.path.join(output_folder, anonymized_file_name)
                    self.anonymize_dicom(input_file_path, output_file_path, patient_name)

    def toggle_rename_fields(self):
        if self.rename_files.get():
            self.nick_label_entry.configure(state="normal")
            self.start_number_entry.configure(state="normal")
        else:
            self.nick_label_entry.configure(state="disabled")
            self.start_number_entry.configure(state="disabled")

    def create_widgets(self):
        # Home button
        home_button = ctk.CTkButton(self, text="Home", command=self.home_callback, fg_color='#FF9800', text_color='white',
                            font=(styles.FONT_FAMILY, styles.HOME_BUTTON_FONT_SIZE), width=styles.HOME_BUTTON_WIDTH, height=styles.HOME_BUTTON_HEIGHT)
        home_button.grid(row=0, column=0, padx=(styles.PADDING_X, styles.PADDING_X), pady=(styles.PADDING_Y, styles.PADDING_Y), sticky="w")


        # Main content frame
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=1, column=0, sticky="", padx=20, pady=10)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        text_frame = ctk.CTkFrame(content_frame)
        text_frame.grid(row=0, column=0, sticky="nsew")
        text_frame.grid_columnconfigure(0, weight=1)

        # Text widget
        text_widget = ctk.CTkTextbox(text_frame, wrap='word', height=styles.TEXTBOX_HEIGHT, width=styles.TEXTBOX_WIDTH)
        text_widget.grid(row=0, column=0, sticky="nsew", padx=styles.PADDING_X, pady=styles.PADDING_Y)
        text_widget.insert("1.0", """File Converter Module\n
        This module processes DICOM images by anonymizing them, converting them to NIfTI format,
        and renaming the files to meet the algorithm's naming convention for proper identification.
                
        Instructions:
        - Use the toggle buttons to select tasks:
                - Anonymize: Removes personal information and numbers anonymized files starting 
                    from the specified number in the "Starting number" line. A .txt file containing the 
                    naming key relating the original and anonymized files is also created in this step.
                - Convert to NIfTI: Converts DICOM files to NIfTI (.nii.gz) format.
        - Click 'Browse' to select the folder containing the files.
        - Input the starting number for numbering the anonymized files.
        - Make sure that the folder contains only the DICOM files to be anonymized and/or converted.
        - Click 'Start' to begin processing the selected tasks.
        - Once done, click 'Open Folder' to access the processed images and renaming key in the newly 
        created folder called "{Folder Name}_Processed_Images".""")
        text_widget.configure(state='disabled')

        # Task selection frame
        task_frame = ctk.CTkFrame(text_frame)
        task_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        task_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        task_label = ctk.CTkLabel(task_frame, text="Select tasks to perform:", font=(styles.FONT_FAMILY, styles.FONT_SIZE+4, 'bold'))
        task_label.grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 10))

        anonymize_switch = ctk.CTkSwitch(task_frame, text="Anonymize DICOMs", variable=self.anonymize, 
                                         font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold'))
        anonymize_switch.grid(row=1, column=0, columnspan=2, sticky="w", pady=5)

        convert_switch = ctk.CTkSwitch(task_frame, text="Convert to NIfTI", variable=self.convert_to_nifti,
                                       font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold'))
        convert_switch.grid(row=1, column=2, columnspan=2, sticky="w", pady=5)

        separator = ctk.CTkFrame(task_frame, height=2, fg_color='white')
        separator.grid(row=2, column=0, columnspan=5, sticky="ew", pady=10)

        rename_switch = ctk.CTkSwitch(task_frame, text="Rename files", variable=self.rename_files,
                                      font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold'),
                                      command=self.toggle_rename_fields)
        rename_switch.grid(row=3, column=0, sticky="w", pady=5)

        nick_label = ctk.CTkLabel(task_frame, text="Name to be applied:", font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold'))
        nick_label.grid(row=3, column=1, sticky="e", pady=5, padx=(10, 5))
        self.nick_label_entry = ctk.CTkEntry(task_frame, textvariable=self.data_nickname, width=150)
        self.nick_label_entry.grid(row=3, column=2, sticky="w", pady=5)

        start_number_label = ctk.CTkLabel(task_frame, text="Starting number:", font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold'))
        start_number_label.grid(row=3, column=3, sticky="e", pady=5, padx=(10, 5))
        self.start_number_entry = ctk.CTkEntry(task_frame, textvariable=self.starting_number, width=100)
        self.start_number_entry.grid(row=3, column=4, sticky="w", pady=5)

        # Input folder frame
        input_frame = ctk.CTkFrame(text_frame)
        input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        input_frame.grid_columnconfigure(1, weight=1)

        input_label = ctk.CTkLabel(input_frame, text="Select Folder:", font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold'))
        input_label.grid(row=0, column=0, sticky="w", padx=(0, 10))
        input_entry = ctk.CTkEntry(input_frame, textvariable=self.input_path)
        input_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        input_button = ctk.CTkButton(input_frame, text="Browse", command=self.browse_input_path, font=(styles.FONT_FAMILY, styles.BUTTON_FONT_SIZE-2), fg_color='#2196F3')
        input_button.grid(row=0, column=2, padx=(0, 10))
        open_button = ctk.CTkButton(input_frame, text="Open Folder", command=self.open_folder, font=(styles.FONT_FAMILY, styles.BUTTON_FONT_SIZE-2))
        open_button.grid(row=0, column=3)

        # Start button
        convert_button = ctk.CTkButton(text_frame, text="Start", command=self.convert_files, fg_color='#008000', text_color='white',
                                       font=(styles.FONT_FAMILY, styles.BUTTON_FONT_SIZE))
        convert_button.grid(row=3, column=0, pady=20)

        # Initially disable the name and starting number fields
        self.toggle_rename_fields()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")  # Set the appearance mode to dark
    ctk.set_default_color_theme("blue")  # Set the color theme to blue

    root = ctk.CTk()
    root.title("DICOM to NIfTI Converter")
    root.geometry("900x00")  # Adjusted initial geometry for better display
    root.resizable(True, True)  # Allow window resizing

    app = AnonDtoNGUI(root, root.destroy)
    app.pack(fill="both", expand=True)  # Expand to fill available space
    root.mainloop()