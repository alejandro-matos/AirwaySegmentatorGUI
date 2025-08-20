# UpperAirwaySegmentator GUI: A User-Friendly Tool for Airway Segmentation
<img src="https://github.com/alejandro-matos/AirwaySegmentatorGUI/raw/main/nnUNetv2GUI/Images/GUI_Screenshot.png" width="900"/>

 This Graphical User Interface (GUI) provides a streamlined workflow for converting medical imaging data and generating 3D models of the upper airway. With just a few clicks, you can: 
 1. **Convert DICOM to NIfTI**: Easily transform your DICOM images into the NIfTI file format, a common standard for medical image analysis.
 2. **Anonymize and Rename files**: Easily transform your DICOM images into the NIfTI file format, a common standard for medical image analysis.
 3. **Automatic Airway Segmentation**: Leverage the power of the "AirwaySegmentor" neural network model, trained using the nnUNet framework, to automatically segment the upper airway from CBCT scans.
 4. **Generate STL Models**: Convert the resulting segmentations into STL files, a widely-used format for 3D printing and computer-aided design (CAD) applications. 
 
 With its intuitive interface and automated processes, the nnUNet GUI simplifies the complex task of airway segmentation, enabling researchers, clinicians, and engineers to easily extract and visualize 3D models of the upper airway from medical imaging data.

## UpperAirwaySegmentator Model
UpperAirwaySegmentator is based on nnUNet framework. The Upper Airway (UA) of 220 CBCTs coming from the University of Alberta, Chile and France were manually segmented. 155 of these CBCT sets were randomly selected for training, while the remaining 65 were used for testing its performance.

If you use UpperAirwaySegmentator for your work, please cite our paper and nnU-Net:

> Matos Camarillo A, Capenakas-Gianoni S, Punithakumar K, Lagravere-Vich M. AirwaySegmentator: A deep learning-based method for Nasopharyngeal airway segmentation. Published online Month day, 2024:2024.xx.xx.xxxxxxxx. doi:10.1101/2024.xx.xx.xxxxxxxx

> Isensee F, Jaeger PF, Kohl SAA, Petersen J, Maier-Hein KH. nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation. Nat Methods. 2021;18(2):203-211. doi:10.1038/s41592-020-01008-z

There will also soon be a 3D Slicer extension available for this model, which can be found here: (https://github.com/alejandro-matos/SlicerUpperAirwaySegmentator)

## Getting started with UpperAirwaySegmentator
1. System Requirements

OS: Windows 10 (tested
Python: 3.11
GPU (optional): CUDA 11.8 or higher recommended for faster processing
Virtual Environment: Recommended to avoid conflicts

2. Install Step-by-Step
a) Clone the repository
```bash
git clone https://github.com/alejandro-matos/AirwaySegmentatorGUI.git
cd AirwaySegmentatorGUI
```

b) Create and activate a virtual environment
```bash
python -m venv venv
```
### On Windows:
```bash
venv\Scripts\activate
```
### On macOS/Linux:
```bash
source venv/bin/activate
```

c) Install PyTorch first
Important: nnU-Net requires PyTorch to be installed before its own installation.
Visit pytorch.org to select the command for your system. Examples:
CPU only:
```bash
pip install torch torchvision torchaudio
```

GPU with CUDA 11.8:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

d) Install nnU-Net v2
```bash
pip install nnunetv2
```

e) Install additional dependencies
```bash
pip install SimpleITK nibabel PyQt5 vtk
```

3. Verify the installation

Run this quick test:
```bash
python - <<EOF
import torch, nnunetv2, SimpleITK, nibabel, PyQt5, vtk
print("PyTorch:", torch.__version__)
print("nnU-Net:", nnunetv2.__version__)
print("SimpleITK:", SimpleITK.__version__)
print("nibabel:", nibabel.__version__)
print("PyQt5:", PyQt5.__version__)
print("VTK:", vtk.vtkVersion.GetVTKVersion())
EOF
```


If everything prints without errors, your setup is ready.

4. Launch the GUI
```bash
python UpperAirwaySegmentator_GUI.py
```

2. Automatic Installer Script

You can add this as install_windows.bat (for Windows) or install_linux.sh (for Linux/macOS). It enforces installation order and verifies the setup automatically.

### Windows (install_windows.bat)
```bash
@echo off
echo === Setting up UpperAirwaySegmentator GUI ===

REM Create virtual environment
python -m venv venv
call venv\Scripts\activate

REM Install PyTorch first (CPU version by default)
echo Installing PyTorch...
pip install torch torchvision torchaudio

REM Install nnU-Net v2
echo Installing nnU-Net v2...
pip install nnunetv2

REM Install additional dependencies
echo Installing additional dependencies...
pip install SimpleITK nibabel PyQt5 vtk

REM Verify installation
echo Verifying installation...
python - <<EOF
import torch, nnunetv2, SimpleITK, nibabel, PyQt5, vtk
print("PyTorch:", torch.__version__)
print("nnU-Net:", nnunetv2.__version__)
print("SimpleITK:", SimpleITK.__version__)
print("nibabel:", nibabel.__version__)
print("PyQt5:", PyQt5.__version__)
print("VTK:", vtk.vtkVersion.GetVTKVersion())
EOF

echo === Setup complete! ===
echo To run the GUI: 
echo call venv\Scripts\activate
echo python UpperAirwaySegmentator_GUI.py
pause
```

## Troubleshooting
This section will list the most commonly encountered issues and how to solve them.
<!--tk Add issues and how to solve them-->

## Acknowledgements
Authors: A. Matos Camarillo (University of Alberta), S. Capenakas-Gianoni (University of Alberta), K. Punithakumar (University of Alberta), M. Lagravere-Vich (University of Alberta)
Supported by (Add funding sources tk)
