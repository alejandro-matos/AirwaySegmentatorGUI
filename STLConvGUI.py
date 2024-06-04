import tkinter as tk
from tkinter import filedialog, messagebox
import os
import nibabel as nib
import numpy as np
from skimage import measure
from stl import mesh
from PIL import Image, ImageTk
from pathlib import Path
import sys
import styles  # Import the styles module

class STLConverterGUI(tk.Frame):
    def __init__(self, parent, home_callback):
        super().__init__(parent)
        self.parent = parent
        self.home_callback = home_callback
        self.configure(bg=styles.BG_COLOR)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()

        self.create_widgets()

    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        abs_path = Path(base_path) / relative_path
        return abs_path.as_posix()  # Convert to POSIX (i.e., forward-slash) format

    def browse_input_path(self):
        self.input_path.set(filedialog.askdirectory())

    def browse_output_path(self):
        self.output_path.set(filedialog.askdirectory())

    def open_folder(self):
        output_path_str = self.output_path.get()
        if not output_path_str or not os.path.isdir(output_path_str):
            messagebox.showwarning("Input Error", "Please select a valid directory.")
        else:
            if sys.platform == "win32":
                os.startfile(output_path_str)
            elif sys.platform == "darwin":
                os.system(f"open {output_path_str}")
            else:
                os.system(f"xdg-open {output_path_str}")

    def nifti_to_stl(self, nifti_file, stl_file):
        # Load the NIfTI file
        img = nib.load(nifti_file)
        img_data = img.get_fdata()

        # Ensure the data is binary
        img_data = img_data.astype(np.uint8)
        img_data[img_data > 0] = 1

        # Perform marching cubes to extract the surface mesh
        verts, faces, _, _ = measure.marching_cubes(img_data, level=0)

        # Create a new mesh object
        surface_mesh = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))

        for i, f in enumerate(faces):
            for j in range(3):
                surface_mesh.vectors[i][j] = verts[f[j], :]

        # Save the mesh as an STL file
        surface_mesh.save(stl_file)

    def convert_files(self):
        input_path_str = self.input_path.get()
        output_path_str = self.output_path.get()
        
        if not input_path_str or not output_path_str:
            messagebox.showwarning("Input Error", "Please select both input and output directories.")
            return

        nifti_files = [f for f in os.listdir(input_path_str) if f.endswith('.nii') or f.endswith('.nii.gz')]
        if not nifti_files:
            messagebox.showwarning("Input Error", "No NIfTI files found in the selected input directory.")
            return

        for nifti_file in nifti_files:
            nifti_file_path = os.path.join(input_path_str, nifti_file)
            stl_file_path = os.path.join(output_path_str, f"{os.path.splitext(nifti_file)[0]}.stl")
            self.nifti_to_stl(nifti_file_path, stl_file_path)

        messagebox.showinfo("Conversion Complete", "All NIfTI files have been converted to STL files.")

    def create_widgets(self):
        # Home button
        if self.home_callback:
            home_button = tk.Button(self, text="Home", command=self.home_callback, bg='#FF9800', fg='white',
                                    font=(styles.FONT_FAMILY, styles.BUTTON_FONT_SIZE), padx=styles.BUTTON_PADDING, pady=styles.BUTTON_PADDING)
            home_button.grid(row=0, column=0, padx=(10, 20), pady=(10, 20), sticky="W")

        # Text widget
        text_widget = tk.Text(self, wrap='word', height=9, width=86, bg=styles.BG_COLOR, fg='white', font=(styles.FONT_FAMILY, 13))
        text_widget.insert(tk.END, """\nNIfTI to STL Converter\n\n
        - Click on 'Browse' to select the folder containing the segmentation files in NIfTI format.
        - Browse to the folder where STL files will be saved.
        - Click on 'Convert' to initialize the conversion.""")
        text_widget.grid(row=1, column=0, columnspan=3, padx=20, pady=(10, 20))
        text_widget.tag_configure("bold", font=(styles.FONT_FAMILY, 18, 'bold'))
        text_widget.tag_configure("center", justify='center')
        text_widget.tag_add("bold", "2.0", "3.end")
        text_widget.tag_add("center", "2.0", "3.end")
        text_widget.configure(state='disabled')  # Make the text widget read-only

        label_grid = {'sticky': tk.E, 'padx': 10, 'pady': (10, 10)}
        roww = 1

        # Input folder
        tk.Label(self, text="Segmentations Folder:", bg=styles.BG_COLOR, fg='white', font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold')).grid(row=roww+1, columnspan=1, **label_grid)
        tk.Entry(self, textvariable=self.input_path, width=70).grid(row=roww+1, column=1, sticky="W")
        tk.Button(self, text="Browse", command=self.browse_input_path, font=(styles.FONT_FAMILY, styles.FONT_SIZE)).grid(row=roww+1, column=2, sticky="W", padx=(10, 20))

        # Output folder
        tk.Label(self, text="STL Folder:", bg=styles.BG_COLOR, fg='white', font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold')).grid(row=roww+2, columnspan=1, **label_grid)
        tk.Entry(self, textvariable=self.output_path, width=70).grid(row=roww+2, column=1, sticky="W")
        tk.Button(self, text="Browse", command=self.browse_output_path, font=(styles.FONT_FAMILY, styles.FONT_SIZE)).grid(row=roww+2, column=2, sticky="W", padx=(10, 20))
        
        # Convert button
        tk.Button(self, text="Start", command=self.convert_files, bg='#2196F3', fg='black', font=(styles.FONT_FAMILY, styles.FONT_SIZE)).grid(row=roww+3, column=1, sticky="EW", padx=(50, 50),pady=(10, 20))

        # Open button
        open_button = tk.Button(self, text="Open Results Folder", command=self.open_folder,font=(styles.FONT_FAMILY, styles.BUTTON_FONT_SIZE-2), padx=10, pady=0)
        open_button.grid(row=roww+3, column=2, sticky="E", padx=(0, 80), pady=(0,10))

if __name__ == "__main__":
    root = tk.Tk()
    app = STLConverterGUI(root, root.destroy)  # For standalone testing, 'home' button will close the app
    app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
