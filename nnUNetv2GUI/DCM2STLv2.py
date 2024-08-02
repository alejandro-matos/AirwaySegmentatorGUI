import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
from pathlib import Path
import sys
import styles
import vtk

class AirwaySegmenterGUI(ctk.CTkFrame):
    def __init__(self, parent, home_callback):
        super().__init__(parent)
        self.parent = parent
        self.home_callback = home_callback
        
        # Set the size of the frame to match the main window
        self.configure(width=styles.WINDOW_WIDTH, height=styles.WINDOW_HEIGHT)

        self.input_path = ctk.StringVar()
        self.output_path = ctk.StringVar()

        self.create_widgets()

    def resource_path(self, relative_path):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        abs_path = Path(base_path) / relative_path
        return abs_path.as_posix()

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
            base_name = os.path.splitext(os.path.splitext(nifti_file)[0])[0]
            stl_file_path = os.path.join(output_path_str, f"{base_name}.stl")
            print(f"The base name is {base_name}")
            print(f"The stl_file_path is {stl_file_path}")
            self.nifti_to_stl(nifti_file_path, stl_file_path, threshold_value=1, decimate=True, decimate_target_reduction=0.5)

        messagebox.showinfo("Conversion Complete", "All NIfTI files have been converted to STL files.")

    def create_widgets(self):
        # Home button
        if self.home_callback:
            home_button = ctk.CTkButton(self, text="Home", command=self.home_callback, fg_color='#FF9800', text_color='white',
                                        font=(styles.FONT_FAMILY, styles.BUTTON_FONT_SIZE))
            home_button.grid(row=0, column=0, padx=(10, 20), pady=(10, 20), sticky="w")

        # Text widget
        text_widget = ctk.CTkTextbox(self, wrap='word', height=200, width=600)
        text_widget.insert("1.0", """\nNIfTI to STL Converter\n\n
        - Click on 'Browse' to select the folder containing the segmentation files in NIfTI format.
        - Browse to the folder where STL files will be saved.
        - Click on 'Convert' to initialize the conversion.""")
        text_widget.grid(row=1, column=0, columnspan=3, padx=20, pady=(10, 20))
        text_widget.configure(state='disabled')  # Make the text widget read-only

        # Input folder
        ctk.CTkLabel(self, text="Segmentations Folder:", font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold')).grid(row=2, column=0, sticky="e", padx=10, pady=(10, 10))
        ctk.CTkEntry(self, textvariable=self.input_path, width=400).grid(row=2, column=1, sticky="w")
        ctk.CTkButton(self, text="Browse", command=self.browse_input_path, font=(styles.FONT_FAMILY, styles.FONT_SIZE)).grid(row=2, column=2, sticky="w", padx=(10, 20))

        # Output folder
        ctk.CTkLabel(self, text="STL Folder:", font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold')).grid(row=3, column=0, sticky="e", padx=10, pady=(10, 10))
        ctk.CTkEntry(self, textvariable=self.output_path, width=400).grid(row=3, column=1, sticky="w")
        ctk.CTkButton(self, text="Browse", command=self.browse_output_path, font=(styles.FONT_FAMILY, styles.FONT_SIZE)).grid(row=3, column=2, sticky="w", padx=(10, 20))
        
        # Convert button
        ctk.CTkButton(self, text="Start", command=self.convert_files, fg_color='#2196F3', text_color='black', font=(styles.FONT_FAMILY, styles.FONT_SIZE)).grid(row=4, column=1, sticky="ew", padx=(50, 50), pady=(10, 20))

        # Open button
        open_button = ctk.CTkButton(self, text="Open Results Folder", command=self.open_folder, font=(styles.FONT_FAMILY, styles.BUTTON_FONT_SIZE-2))
        open_button.grid(row=4, column=2, sticky="e", padx=(0, 80), pady=(0, 10))

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")  # Set the appearance mode to dark
    ctk.set_default_color_theme("blue")  # Set the color theme to blue

    root = ctk.CTk()
    root.title("NIfTI to STL Converter")
    root.geometry(f"{styles.WINDOW_WIDTH}x{styles.WINDOW_HEIGHT}")  # Set fixed geometry
    root.resizable(False, False)  # Disable window resizing
    app = STLConverterGUI(root, root.destroy)  # For standalone testing, 'home' button will close the app
    app.pack(fill="both", expand=True)
    root.mainloop()
