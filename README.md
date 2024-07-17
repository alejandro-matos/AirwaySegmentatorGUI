# UpperAirwaySegmentator GUI: A User-Friendly Tool for Airway Segmentation
![image](https://github.com/alejandro-matos/AirwaySegmentatorGUI/assets/84166343/24214a16-b97b-44d5-a6ec-eaa5a7d0f241)

 This Graphical User Interface (GUI) provides a streamlined workflow for converting medical imaging data and generating 3D models of the upper airway. With just a few clicks, you can: 
 1. **Convert DICOM to NIfTI**: Easily transform your DICOM images into the NIfTI file format, a common standard for medical image analysis.
 2. **Automatic Airway Segmentation**: Leverage the power of the "AirwaySegmentor" neural network model, trained using the nnUNet framework, to automatically segment the upper airway from your CBCT scans.
 3. **Generate STL Models**: Convert the resulting segmentations into STL files, a widely-used format for 3D printing and computer-aided design (CAD) applications. With its intuitive interface and automated processes, the nnUNet GUI simplifies the complex task of airway segmentation, enabling researchers, clinicians, and engineers to easily extract and visualize 3D models of the upper airway from medical imaging data.

## UpperAirwaySegmentator Model
UpperAirwaySegmentator is based on nnUNet framework. The Upper Airway (UA) of 75 CBCTs coming from the University of Alberta were manually segmented. 40 of these CBCT sets were randomly selected for training, while the remaining 35 were used for testing its performance.

If you use UpperAirwaySegmentator for your work, please cite our paper and nnU-Net:

> Matos Camarillo A, Capenakas-Gianoni S, Punithakumar K, Lagravere-Vich M. AirwaySegmentator: A deep learning-based method for Nasopharyngeal airway segmentation. Published online Month day, 2024:2024.xx.xx.xxxxxxxx. doi:10.1101/2024.xx.xx.xxxxxxxx

> Isensee F, Jaeger PF, Kohl SAA, Petersen J, Maier-Hein KH. nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation. Nat Methods. 2021;18(2):203-211. doi:10.1038/s41592-020-01008-z

There will also soon be a 3D Slicer extension available for this model, which can be found here: (https://github.com/alejandro-matos/SlicerUpperAirwaySegmentator)

## Getting started with UpperAirwaySegmentator
This GUI has been tested in Windows, soon to be tested on MacOS and Linux.

<!--tk Will add a tutorial and images here-->

## Troubleshooting
This section will list the most commonly encountered issues and how to solve them.
<!--tk Add issues and how to solve them-->

## Acknowledgements
Authors: A. Matos Camarillo (University of Alberta), S. Capenakas-Gianoni (University of Alberta), M. Lagravere-Vich (University of Alberta)
Supported by (Add funding sources tk)
