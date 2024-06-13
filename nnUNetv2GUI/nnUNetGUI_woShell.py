import tkinter as tk
from tkinter import messagebox
import subprocess
import threading
import webbrowser
import os
from pathlib import Path
import sys
from PIL import Image, ImageTk
import styles
import platform

class nnUNetGUI4(tk.Frame):
    def __init__(self, parent, home_callback):
        super().__init__(parent)
        self.parent = parent  # Store reference to the main Tk window
        self.home_callback = home_callback
        self.configure(bg=styles.BG_COLOR)

        self.Path0 = Path(self.resource_path("Airways"))
        self.Path1 = Path(self.resource_path("Airways/nnUNet_raw"))
        self.Path2 = Path(self.resource_path("Airways/nnUNet_results"))
        self.Path3 = Path(self.resource_path("Airways/nnUNet_preprocessed"))

        self.create_widgets()

    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        base_path = getattr(sys, '_MEIPASS', Path(__file__).parent)
        return (base_path / relative_path).as_posix()

    def setup_paths(self, task_no):
        """Constructs paths for input and output directories based on the task number."""
        nnUNet_IN = Path(self.Path0) / "nnUNet_raw_data_base" / "nnUNet_raw_data" / task_no / "imagesTs"
        nnUNet_OUT = Path(self.Path0) / "nnUNet_raw_data_base" / "nnUNet_raw_data" / task_no / "imagesOut"
        return nnUNet_IN.as_posix(), nnUNet_OUT.as_posix()

    def open_folder(self, path):
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            os.makedirs(path)
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open the directory: {str(e)}")

    def run_script(self, task_no):
        if not task_no:
            messagebox.showwarning("Warning", "Task Number field cannot be empty!")
            return

        loading = tk.Toplevel(self.parent)  # Use parent to create Toplevel window
        loading.title("Processing")
        loading.configure(bg=styles.BG_COLOR)

        label_font = (styles.FONT_FAMILY, 20)
        tk.Label(loading, text="Prediction for " + task_no + " is running, please wait...", font=label_font, bg=styles.BG_COLOR, fg="white").pack(pady=100, padx=100)
        loading.grab_set()

        def script_execution():
            nnUNet_IN, nnUNet_OUT = self.setup_paths(task_no)
            
            # Construct the user profile path
            user_profile_path = Path(os.path.expanduser('~'))

            # If you need to convert to string, handle OS differences
            if platform.system() == "Windows":
                user_profile_path_str = user_profile_path.as_posix()
            else:
                user_profile_path_str = str(user_profile_path)
            try:

                nnUNet_IN = nnUNet_IN
                nnUNet_OUT = nnUNet_OUT
                # Ensure paths are in Unix format
                self.Path1 = self.Path1.as_posix()
                self.Path2 = self.Path2.as_posix()
                self.Path3 = self.Path3.as_posix()

                print(nnUNet_IN,self.Path1)

                # Set environment variables
                # --- Example for Windows----
                # os.environ["nnUNet_raw"] = "C:/Users/alejandromatos/Desktop/Alejandro/Airways_v2/nnUNet_raw"
                # os.environ["nnUNet_results"] = "C:/Users/alejandromatos/Desktop/Alejandro/Airways_v2/nnUNet_results"
                # os.environ["nnUNet_preprocessed"] = "C:/Users/alejandromatos/Desktop/Alejandro/Airways_v2/nnUNet_preprocessed"
                #----- Setting paths programatically -----
                os.environ["nnUNet_raw_data_base"] = self.Path1
                os.environ["RESULTS_FOLDER"] = self.Path2
                os.environ["nnUNet_preprocessed"] = self.Path3

                # Run nnUNet_predict command
                result = subprocess.run([
                    'nnUNetv2_predict', '-i', nnUNet_IN, '-o', nnUNet_OUT,
                    '-d', '13', '-c', '3d_fullres',
                ], capture_output=True, text=True)


                if result.returncode != 0:
                    raise subprocess.CalledProcessError(result.returncode, result.args, output=result.stdout, stderr=result.stderr)

                messagebox.showinfo("Notification", f"The prediction for {task_no} has been completed!")
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"Failed to run the nnUNet prediction: {e.stderr}")
            finally:
                loading.destroy()

        threading.Thread(target=script_execution).start()

    def create_widgets(self):
        home_button = tk.Button(self, text="Home", command=self.home_callback, bg='#FF9800', fg='white',
                                font=(styles.FONT_FAMILY, styles.BUTTON_FONT_SIZE), padx=styles.BUTTON_PADDING, pady=styles.BUTTON_PADDING)
        home_button.grid(row=0, column=0, padx=(10, 20), pady=(10, 20), sticky="W")

        text_widget = tk.Text(self, wrap='word', height=22, width=100, bg=styles.BG_COLOR, fg="white", font=(styles.FONT_FAMILY, 12), pady=10)
        text_widget.insert(tk.END, "Welcome to the nnUNet GUI\n\n"
                           "    - Ensure your images are in NIfTI format.\n"
                           "    - If your images are in DICOM format, use the DICOM to NIfTI Converter module.\n"
                           "    - CBCT files should be named as \"{Case Identifier}_0000\".\n"
                           "      - The Case Identifier uniquely identifies each file.\n"
                           "      - Use descriptive names and number files sequentially, e.g., Airways_1_0000, Airways_2_0000.\n"
                           "    - For other medical image formats, use 3D Slicer to convert to NIfTI: 3D SLICER\n\n"
                           
                           "Steps to start automatic segmentation:\n"
                           "    - Input a unique Task Number in the format \"TaskXXX_Identifier\".\n"
                           "       - XXX is any 3-digit number, e.g., Task123_ProjectX.\n"
                           "    - Click 'Open/Create IN Folder' and copy your CBCT files into the folder.\n"
                           "    - Click 'Run nnUNet' to start segmentation.\n"
                           "    - Wait for the notification that segmentation is complete.\n"
                           "       - Estimated time: 12 minutes per CBCT.\n"
                           "    - Notification: \"The prediction for 'Your Task Number' has been completed!\"\n"
                           "    - Click 'Go to OUT Folder (Results)' to see the segmented files.\n"
                           "*For more information, visit the nnUNet GitHub page.*"
                          )
        text_widget.tag_configure("bold", font=(styles.FONT_FAMILY, 18, 'bold'))
        text_widget.tag_add("bold", "1.0", "1.end")
        text_widget.tag_add("bold", "10.0", "10.end")

        text_widget.tag_configure("bold2", font=(styles.FONT_FAMILY, 14, 'bold'))
        text_widget.tag_add("bold2", "6.62", "6.end")
        text_widget.tag_add("bold2", "12.62", "12.end")

        text_widget.configure(state='disabled')  
        text_widget.grid(row=1, column=0, columnspan=2, padx=20, pady=10)
        text_widget.tag_add("center", "1.0", "1.end") 
        text_widget.tag_add("center", "10.0", "10.end") 
        text_widget.tag_add("center", "19.0", "19.end") 
        text_widget.tag_configure("center", justify='center')
        text_widget.tag_add("white_text", "1.0", "end")
        text_widget.tag_configure("white_text", foreground="white")
        text_widget.tag_add("link", "8.70", "8.end")
        text_widget.tag_add("bold2", "8.70", "8.end")
        text_widget.tag_configure("link", foreground="#00008B", underline=True)

        def open_url(event):
            webbrowser.open_new("https://download.slicer.org/")
        text_widget.tag_bind("link", "<Button-1>", open_url)

        text_widget.tag_add("link2", "19.0", "19.end")
        text_widget.tag_add("bold2", "19.0", "19.end")
        text_widget.tag_configure("link2", foreground="#00008B", underline=True)

        def open_url(event):
            webbrowser.open_new("http://github.com/MIC-DKFZ/nnUNet")
        text_widget.tag_bind("link2", "<Button-1>", open_url)

        tk.Label(self, text="Enter Task Number:", bg=styles.BG_COLOR, fg='white', font=(styles.FONT_FAMILY, styles.FONT_SIZE, 'bold')).grid(row=2, column=0, padx=5, pady=(0, 10), sticky="E")
        self.task_number_entry = tk.Entry(self)
        self.task_number_entry.grid(row=2, column=1, padx=25, pady=(0, 10), sticky="EW")

        tk.Button(self, text="Open/Create IN Folder", command=self.open_in_folder, bg='#BA562E', fg='white').grid(row=3, column=0, columnspan=2, sticky="EW", padx=20, pady=10)

        tk.Button(self, text="Run nnUNet", command=lambda: self.run_script(self.task_number_entry.get()), bg='#2196F3', fg='white').grid(row=4, column=0, columnspan=2, sticky="EW", padx=20, pady=10)

        tk.Button(self, text="Go to OUT Folder (Results)", command=self.navigate_to_out_folder, bg='#FF9800', fg='white').grid(row=5, column=0, columnspan=2, sticky="EW", padx=20, pady=10)

    def open_in_folder(self):
        task_no = self.task_number_entry.get()
        if not task_no:
            messagebox.showwarning("Warning", "Task Number field cannot be empty!")
            return
        nnUNet_IN, nnUNet_OUT = self.setup_paths(task_no)
        if not os.path.exists(nnUNet_IN):
            os.makedirs(nnUNet_IN)
        if not os.path.exists(nnUNet_OUT):
            os.makedirs(nnUNet_OUT)
        self.open_folder(nnUNet_IN)

    def navigate_to_out_folder(self):
        task_no = self.task_number_entry.get()
        if not task_no:
            messagebox.showwarning("Warning", "Task Number field cannot be empty!")
            return
        _, nnUNet_OUT = self.setup_paths(task_no)
        self.open_folder(nnUNet_OUT)

if __name__ == "__main__":
    root = tk.Tk()
    app = nnUNetGUI4(root, root.destroy)  # For standalone testing, 'home' button will close the app
    app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
