import tkinter as tk
from tkinter import messagebox, filedialog
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

        # Get the current working directory and go one level up
        # In this case, it is /Alejandro
        self.parent_dir = os.path.dirname(os.getcwd())
        # Construct the path to the target folder and create path
        self.Path1 = Path(os.path.join(self.parent_dir, 'Airways_v2', 'nnUNet_raw'))
        self.Path2 = Path(os.path.join(self.parent_dir, 'Airways_v2', 'nnUNet_results'))
        self.Path3 = Path(os.path.join(self.parent_dir, 'Airways_v2', 'nnUNet_preprocessed'))
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()

        self.create_widgets()
    
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

    def setup_paths(self):
        nnUNet_IN = self.input_path.get()
        nnUNet_OUT = self.output_path.get()
        return nnUNet_IN, nnUNet_OUT

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

    def run_script(self):
        
        loading = tk.Toplevel(self.parent)  # Use parent to create Toplevel window
        loading.title('Processing')
        loading.configure(bg=styles.BG_COLOR)

        label_font = (styles.FONT_FAMILY, 20)
        tk.Label(loading, text=f'Prediction is running, please wait...', font=label_font, bg=styles.BG_COLOR, fg='white').pack(pady=100, padx=100)
        loading.grab_set()

        def script_execution():
            nnUNet_IN, nnUNet_OUT = self.setup_paths()
            
            # Ensure paths are in Unix format
            self.Path1 = self.Path1.as_posix()
            self.Path2 = self.Path2.as_posix()
            self.Path3 = self.Path3.as_posix()

            # Debugging print statements
            print('nnUNet_IN:', nnUNet_IN)
            print('nnUNet_OUT:', nnUNet_OUT)
            print('Path1:', self.Path1)
            print('Path2:', self.Path2)
            print('Path3:', self.Path3)

            # Set environment variables
            os.environ['nnUNet_raw'] = self.Path1
            os.environ['nnUNet_results'] = self.Path2
            os.environ['nnUNet_preprocessed'] = self.Path3

            try:
                # Run nnUNet_predict command
                result = subprocess.run([
                    'nnUNetv2_predict', '-i', nnUNet_IN, '-o', nnUNet_OUT,
                    '-d', '13', '-c', '3d_fullres',
                ], capture_output=True, text=True)
                
                # Print the output for debugging
                print('stdout:', result.stdout)
                print('stderr:', result.stderr)

                result.check_returncode()  # This will raise CalledProcessError if the return code is non-zero

                messagebox.showinfo('Notification', f'The prediction has been completed!')
            except subprocess.CalledProcessError as e:
                print(f"Error: {e.stderr}")
                messagebox.showerror("Error", f"Failed to run nnUNet prediction: {e.stderr}")

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
        text_widget.grid(row=1, column=0, columnspan=3, padx=20, pady=10)
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
        
        label_style = {'bg': styles.BG_COLOR, 'fg': 'white', 'font': (styles.FONT_FAMILY, styles.FONT_SIZE, 'bold')}

        roww = 1
        
        # Input folder
        tk.Label(self, text="CBCT folder:", **label_style).grid(row=roww+1, column=0, sticky="E", padx=10, pady = (10, 5))
        tk.Entry(self, textvariable=self.input_path, width=60).grid(row=roww+1, column=1, sticky="W")
        tk.Button(self, text="Browse", command=self.browse_input_path, font=(styles.FONT_FAMILY, styles.FONT_SIZE)).grid(row=roww+1, column=1, sticky="E", padx=(10, 20))

        # Output folder
        tk.Label(self, text="Prediction folder:", **label_style).grid(row=roww+2, column=0, sticky="E", padx=10, pady = (10, 5))
        tk.Entry(self, textvariable=self.output_path, width=60).grid(row=roww+2, column=1, sticky="W")
        tk.Button(self, text="Browse", command=self.browse_output_path, font=(styles.FONT_FAMILY, styles.FONT_SIZE)).grid(row=roww+2, column=1, sticky="E", padx=(10, 20))

        tk.Button(self, text="Open CBCT Folder", command=lambda: self.open_folder(self.input_path.get()), bg='#BA562E', fg='white', width=20).grid(row=roww+1, column=2, sticky="W", padx=(0), pady=5)

        tk.Button(self, text="Open Predictions Folder", command=lambda: self.open_folder(self.output_path.get()), bg='#BA562E', fg='white', width=20).grid(row=roww+2, column=2, sticky="W", padx=(0), pady=5)

        tk.Button(self, text="Run nnUNet", command=lambda: self.run_script(), bg='#2196F3', fg='white', width=40).grid(row=roww+5, column=1, sticky="W", padx=30, pady=5)

if __name__ == "__main__":
    root = tk.Tk()
    app = nnUNetGUI4(root, root.destroy)  # For standalone testing, 'home' button will close the app
    app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
