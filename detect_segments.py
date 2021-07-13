# detect_segments.py
# Collects each object instance detected in the street segment images of a
# given neighborhood, including its bounding box (bbox) size and confidence.
#
# Usage: Run the following command in terminal (modified to your neighborhood of choice)
#   python detect_segments.py -w path_to_weights.pt -s 1080
#   -d Data/ProcessedData/SFStreetView/segment_dictionary_MissionDistrictBlock.json
#   -o Outputs/Detection/Res_640/MissionDistrictBlock_2011-02-01_3/
#   -i Data/ProcessedData/SFStreetView/Res_640/MissionDistrictBlock_2011-02-01_3/
#
# Data inputs:
#   - Segment dictionary for the selected location (from 01_generate_street_segments.py)
#   - Directory containing the location's images (from 02_collect_street_segment_images.py)
#
# Outputs:
#   - CSV file including one row per detected object instance, saved to the
#     selected output_path

import argparse
import glob
import json
import numpy as np
import os
import pandas as pd
import torch
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


def get_objects(img_result, model_names_list, image_path, seg_id):
    """
    Returns a dictionary including the bbox size, confidence and class of each
    object instance detected in an image.
    :param img_result: (tensor) of size (number of objects detected, 6),
    where the columns represent: x1, y1, x2, x2, confidence, class
    :param model_names_list: (list) of classes being predicted (in the order
    they are being encoded)
    :param seg_id: (str)
    :param image_path: (str)
    :return: (dict) including the count for each of the classes in model_names_list
    """
    object_dict = {}
    num_objects = img_result.shape[0]
    img_result = img_result.numpy()

    # Add image and segment ID
    object_dict['segment_id'] = [seg_id] * num_objects
    img_id = image_path.split(os.path.sep)[-1]. \
        split('img_{}_'.format(seg_id))[-1].split('.png')[0]
    object_dict['img_id'] = [img_id] * num_objects

    # Get objects
    object_dict['confidence'] = img_result[:, 4].tolist()
    object_dict['bbox_size'] = np.multiply(
        img_result[:, 2] - img_result[:, 0], img_result[:, 3] - img_result[:, 1]).tolist()

    # Get object classes
    obj_classes = img_result[:, 5].tolist()
    object_dict['class'] = [model_names_list[int(c_id)] for c_id in obj_classes]

    return object_dict


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
    df_columns = {'segment_id': [], 'img_id': [], 'confidence': [],
                  'bbox_size': [], 'class': []}
    model_names = model.names
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

        # Get segment images
        images = glob.glob(
            os.path.join(input_images, 'img_{}_*.png'.format(segment_id)))
        image_paths = images.copy()

        # Skip the segment if it has no associated images
        if len(image_paths) == 0:
            continue

        results = model(images, size=image_size)

        # Add to segment vector DataFrame
        for i in range(len(results)):
            # Get objects and image ID
            img_objects = get_objects(
                results.xyxy[i], model_names, image_paths[i], segment_id)

            segment_vectors = segment_vectors.append(
                pd.DataFrame(img_objects), ignore_index=True)

    # Save segment vectors
    if not os.path.exists(output_path):
        print('[INFO] Creating output directories: {}'.format(output_path))
        os.makedirs(output_path)
    segment_vectors.to_csv(os.path.join(output_path, 'detections.csv'), index=False)
