# Generates a table of the class distributions in a dataset

import glob
import os
import yaml


DATASET = os.path.join('..', '..',
    'Data', 'RawData', 'ObjectDetection', 'Res_640',
                       'Iteration2', 'Roboflow',
                       'Tent_class.v1-iteration2sfoaklandtents.yolov5pytorch')

# Read data.yaml file to learn labels
try:
    with open(os.path.join(DATASET, 'data.yaml')) as file:
        data_file = yaml.safe_load(file)
except FileNotFoundError:
    raise Exception('[ERROR] File not found.')

CLASS_DICT = {}
CLASS_COUNTS = {}
for i, class_inst in enumerate(data_file['names']):
    CLASS_DICT[i] = class_inst
    CLASS_COUNTS[class_inst] = 0

# Count all images
total_images = 0
for split in ['train', 'valid', 'test']:
    labels = glob.glob(os.path.join(DATASET, split, 'labels', '*.txt'))

    for label_file in labels:
        total_images += 1
        with open(label_file, 'r') as file:
            label_text = file.readlines()

        for label_line in label_text:
            label, x, y, w, h = label_line.split(' ')
            CLASS_COUNTS[CLASS_DICT[int(label)]] += 1

# Print results
total_count = 0
for class_inst, class_count in CLASS_COUNTS.items():
    print('Class: {}; Count: {}'.format(class_inst, class_count))
    total_count += class_count

print('Total: {}'.format(total_count))
print('Total images : {}'.format(total_images))
