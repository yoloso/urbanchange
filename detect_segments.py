# detect_segments.py
#
# Usage:
#
# Inputs:
# Outputs:

import argparse
import glob
import json
import numpy as np
import os
import pandas as pd
from PIL import Image
import torch
import torchvision
from tqdm import tqdm


# Set up command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-w', '--weights', required=True,
                    help='Path to model weights')
parser.add_argument('-s', '--size', required=True, default=640, help='Image size')
parser.add_argument('-d', '--segment_dictionary', required=True,
                    help='Path to segment JSON dictionary')
parser.add_argument('-o', '--output_path', required=True,
                    help='Output path for segment vectors')
parser.add_argument('-i', '--input_images', required=True,
                    help='Path to input images for inference')


def get_object_count(img_result, model_names_list):
    """
    Counts the number of instances of each object class in an image.
    :param img_result: (tensor) of size (number of objects detected, 6),
    where the columns represent: x1, y1, x2, x2, confidence, class
    :param model_names_list: (list) of classes being predicted (in the order
    they are being encoded)
    :return: (dict) including the count for each of the classes in model_names_list
    """
    object_count_dict = {}
    for j in range(len(model_names_list)):
        object_count_dict[model_names_list[j]] = (img_result[:, -1] == j).sum().item()
    return object_count_dict


if __name__ == '__main__':
    # Capture command line arguments
    args = vars(parser.parse_args())
    model_weights = args['weights']
    image_size = args['size']
    segment_dictionary_file = args['segment_dictionary']
    output_path = args['output_path']
    input_images = args['input_images']

    # Load segment dictionary
    try:
        print('[INFO] Loading segment dictionary.')
        with open(segment_dictionary_file, 'r') as seg_file:
            segment_dictionary = json.load(seg_file)
    except FileNotFoundError:
        raise Exception('[ERROR] Segment file dictionary not found.')

    # Load model with custom weights
    print('[INFO] Loading YOLOv5 model with custom weights.')
    model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_weights)

    # Set up segment vector DataFrame
    df_columns = {'segment_id': [], 'img_id': []}
    model_names = model.names
    for name in model_names:
        df_columns[name] = []
    segment_vectors = pd.DataFrame(df_columns)

    # Verify image neighborhood matches segment dictionary neighborhood
    segment_neighborhood = \
        segment_dictionary_file.split(os.path.sep)[-1].split('.')[0].split('_')[-1]
    image_neighborhood = input_images.split(os.path.sep)[-1].split('_')[0]
    if segment_neighborhood != image_neighborhood:
        raise Exception('[ERROR] Image neighborhood should match segment neighborhood.')

    # Inference on each segment and image
    print('[INFO] Generating segment vectors for {}'.format(segment_neighborhood))
    for key, segment in tqdm(segment_dictionary.items()):
        # Hash segment ID
        segment_id = json.loads(segment['segment_id'])
        segment_id = '{}-{}'.format(segment_id[0], segment_id[1])

        # Get image predictions
        images = glob.glob(
            os.path.join(input_images, 'img_{}_*.png'.format(segment_id)))
        image_paths = images.copy()
        results = model(images, size=image_size)

        # Add to segment vector DataFrame
        for i in range(len(results)):
            # Get object count and image ID
            object_count = get_object_count(results.xyxy[i], model_names)
            img_id = image_paths[i].split(os.path.sep)[-1].\
                split('img_{}_'.format(segment_id))[-1].split('.png')[0]

            # Append to DataFrame
            object_count['segment_id'] = segment_id
            object_count['img_id'] = img_id
            segment_vectors = segment_vectors.append(
                object_count, ignore_index=True)

    # Save segment vectors
    if not os.path.exists(output_path):
        print('[INFO] Creating output directories: {}'.format(output_path))
        os.makedirs(output_path)
    segment_vectors.to_csv(output_path, index=False)
