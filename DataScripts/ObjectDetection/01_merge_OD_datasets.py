import glob
import os
import random
import shutil
import shutil
import yaml
from zipfile import ZipFile

# Parameters
ROBOFLOW_DIRECTORY = os.path.join(
    'Data', 'RawData', 'ObjectDetection', 'Roboflow')
OUTPUT_DIRECTORY = os.path.join('Data', 'ProcessedData', 'ObjectDetection')
NUM_VALID_IMAGES = 150

# Class dictionary
CLASSES_FROM_LABEL = {0: 'facade',
                      1: 'graffiti',
                      2: 'weed',
                      3: 'garbage',
                      4: 'pothole',
                      5: 'tent',
                      6: 'window'}

CLASSES_TO_LABEL = {'facade': 0,
                    'graffiti': 1,
                    'weed': 2,
                    'garbage': 3,
                    'pothole': 4,
                    'tent': 5,
                    'window': 6}


# Helper functions
def check_label_consistency(label_list):
    consistent_bool = True
    consistency_dictionary = {}

    # Check each class
    for i in range(len(label_list)):
        if label_list[i] != CLASSES_FROM_LABEL[i]:
            consistent_bool = False
        if label_list[i] not in CLASSES_TO_LABEL.keys():
            raise Exception('[ERROR] Class {} not in dictionary'.format(label_list[i]))
        else:
            consistency_dictionary[i] = CLASSES_TO_LABEL[label_list[i]]

    return consistent_bool, consistency_dictionary


def correct_annotations(consistency_dictionary, annotation_path):
    # Create new annotations file
    new_annot_path = ''.join([annotation_path.split('.txt')[0], '_corrected.txt'])

    # Open annotations file
    with open(annotation_path, 'r') as annot_file:
        with open(new_annot_path, 'w') as new_annot_file:
            for line in annot_file:
                # Read line
                label, box1, box2, box3, box4 = line.split(' ')
                corrected_label = str(consistency_dictionary[int(label)])
                new_line = ' '.join([corrected_label, box1, box2, box3, box4])

                # Write corrected line to new file
                new_annot_file.write(new_line)

    return new_annot_path


def get_image_name(image_path):
    image_name = image_path.split(os.path.sep)[-1]
    image_name = '.'.join(image_name.split('.')[:-1])
    return image_name

def process_image(image_path, rf_dir, split,
                  consistent, consistency_dict, counter):
    # Get the image name (excluding extension)
    image_name = get_image_name(image_path)

    # Get annotations
    annot_path = os.path.join(
        rf_dir, split, 'labels', ''.join([image_name, '.txt']))

    # Homogenize classes if inconsistent
    if not consistent:
        annot_path = correct_annotations(
            consistency_dictionary=consistency_dict, annotation_path=annot_path)

    # Get new file paths for the image and its annotations
    new_image_path = os.path.join(
        OUTPUT_DIRECTORY, 'train', 'images', ''.join([image_name, '.jpg']))
    new_annot_path = os.path.join(
        OUTPUT_DIRECTORY, 'train', 'labels', ''.join([image_name, '.txt']))

    # Check for duplicate file names and copy to output directory
    if not os.path.exists(new_image_path):
        shutil.copyfile(image_path, new_image_path)
        shutil.copyfile(annot_path, new_annot_path)
        counter += 1
    else:
        print('[WARNING] Duplicate image name: {}'.format(image_name))

    # Remove corrected annotations file
    if not consistent:
        os.remove(annot_path)

    return counter


if __name__ == '__main__':
    # Collect Roboflow datasets
    # (Note that these are formatted for YOLOv5 in PyTorch)
    datasets = glob.glob(os.path.join(ROBOFLOW_DIRECTORY, '*yolov5pytorch*'))
    print('[INFO] Merging {} datasets exported from Roboflow'.format(len(datasets)))

    # Set up new dataset in output directory
    if not os.path.exists(OUTPUT_DIRECTORY):
        print('[INFO] Creating output directory')
        os.makedirs(OUTPUT_DIRECTORY)

    # Create split directories
    for split in ['train', 'valid', 'test']:
        if not os.path.exists(os.path.join(OUTPUT_DIRECTORY, split)):
            os.makedirs(os.path.join(OUTPUT_DIRECTORY, split, 'images'))
            os.makedirs(os.path.join(OUTPUT_DIRECTORY, split, 'labels'))

    # Collect annotated samples
    counter = 0
    for dataset in datasets:
        print('[INFO] Processing {}'.format(dataset))
        # Unzip file
        dir_name = dataset.split(os.path.sep)[-1].split('.zip')[0]
        rf_dir = os.path.join(ROBOFLOW_DIRECTORY, dir_name)
        with ZipFile(dataset, 'r') as file:
            file.extractall(rf_dir)

        # Check label consistency
        with open(os.path.join(rf_dir, 'data.yaml'), 'r') as file:
            labels = yaml.safe_load(file)['names']
        consistent, consistency_dict = check_label_consistency(label_list=labels)

        # Loop over each split
        for split in ['train', 'valid', 'test']:
            if os.path.exists(os.path.join(rf_dir, split)):
                # Gather images in directory and process each one
                images = glob.glob(os.path.join(rf_dir, split, 'images', '*'))
                for image_path in images:
                    counter = process_image(
                        image_path=image_path, rf_dir=rf_dir, split=split,
                        consistent=consistent, consistency_dict=consistency_dict,
                        counter=counter)

    # Create train/validation split
    print('[INFO] Creating train/validation split...')
    train_imgs = glob.glob(os.path.join(OUTPUT_DIRECTORY, 'train', 'images', '*'))
    random.seed(42)
    random.shuffle(train_imgs)
    val_imgs = train_imgs[:NUM_VALID_IMAGES]

    for val_img in val_imgs:
        img_name = get_image_name(val_img)

        # Move image and annotation file to validation directory
        new_val_img = os.path.join(
            OUTPUT_DIRECTORY, 'valid', 'images', ''.join([img_name, '.jpg']))
        val_annot = os.path.join(
            OUTPUT_DIRECTORY, 'train', 'labels', ''.join([img_name, '.txt']))
        new_val_annot = os.path.join(
            OUTPUT_DIRECTORY, 'valid', 'labels', ''.join([img_name, '.txt']))

        shutil.move(val_img, new_val_img)
        shutil.move(val_annot, new_val_annot)

    # Create .yaml file
    print('[INFO] Generating YAML file..')
    yaml_dict = {
        'train': '../train/images',
        'val': '../valid/images',
        'nc': 7,
        'names': ['facade', 'graffiti', 'weed', 'garbage', 'pothole',
                  'tent', 'window']
    }
    with open(os.path.join(OUTPUT_DIRECTORY, 'data.yaml'), 'w') as file:
        yaml.safe_dump(yaml_dict, file, default_flow_style=False)
    # TODO correct YAML file output

    # Check
    for split in ['train', 'valid']:
        img_count = len(glob.glob(os.path.join(OUTPUT_DIRECTORY, split, 'images', '*')))
        lab_count = len(glob.glob(os.path.join(OUTPUT_DIRECTORY, split, 'labels', '*')))
        if img_count != lab_count:
            print('[ERROR] in {}; images: {}; labels: {}'.format(split, img_count, lab_count))

    print('[INFO] Collected {} images'.format(counter))
