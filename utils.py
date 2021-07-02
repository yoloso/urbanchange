import os


def get_image_name(image_path):
    image_name = image_path.split(os.path.sep)[-1]
    image_name = '.'.join(image_name.split('.')[:-1])
    return image_name


def load_annotations(annotation_path):
    with open(annotation_path, 'r') as file:
        box_list = file.readlines()
    return box_list

def preprocess_box_list(box_list):
    num_objects = len(box_list)
    boxes = []

    for box in box_list:
        pass

    return num_objects, labels, XXX