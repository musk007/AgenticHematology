import os
from shutil import copy, copytree



data_root = "/Volumes/One Touch/Data/Hematology/Large Leukemia Dataset/Leukemia_Attr"
organized_folder = "/Volumes/One Touch/Data/Hematology/organized_dataset"


image_output_dir = os.path.join(organized_folder, "images")
attributes_output_dir = os.path.join(organized_folder, "attributes")
Localization_output_dir = os.path.join(organized_folder, "Localization")

os.makedirs(image_output_dir, exist_ok=True)
os.makedirs(os.path.join(image_output_dir, "train"), exist_ok=True)
os.makedirs(os.path.join(image_output_dir, "test"), exist_ok=True)

# copying localizatioona dn attribute files into folders 
localization_path = os.path.join(data_root, "LeukemiaAttri_Dataset","H_40X_C2", "txt_labels", "WBC_Detection")
copytree(localization_path, Localization_output_dir)


attributes_path = os.path.join(data_root, "LeukemiaAttri_Dataset","H_40X_C2", "txt_labels", "AttriDet")
copytree(attributes_path, attributes_output_dir)

copy((os.path.join(data_root, "LeukemiaAttri_Dataset","H_40X_C2","json_labels", "train.json")), organized_folder)
copy((os.path.join(data_root, "LeukemiaAttri_Dataset","H_40X_C2","json_labels", "test.json")), organized_folder)

parts = ["", " 2", " 3", " 4", " 5"]
splits = ["train", "test"]
for part in parts:
    for split in splits:
        data_part_path = os.path.join(data_root, f"LeukemiaAttri_Dataset{part}" , "H_40X_C2")
        images_split_path = os.path.join(data_part_path, "Images", split)
        for im in os.listdir(images_split_path):
                # copying images
                src = os.path.join(images_split_path, im)
                dest = os.path.join(image_output_dir, split, im)
                copy(src, dest)
