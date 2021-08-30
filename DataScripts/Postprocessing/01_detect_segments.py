# 01_detect_segments.py
# Collects each object instance detected in the street segment images of a
# given neighborhood, including its bounding box (bbox) size and confidence.
#
# Usage: Run the following command in terminal (modified to your neighborhood of choice)
#   python 01_detect_segments.py -w path_to_weights.pt -s 1080
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

from DataScripts.read_files import load_segment_dict
from DataScripts.urbanchange_utils import AppendLogger


# Set up command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-w', '--weights', required=True,
                    help='Path to model weights')
parser.add_argument('-s', '--size', required=True, default=640,
                    help='Image size', type=int)
parser.add_argument('-d', '--segment_dictionary', required=True,
                    help='Path to segment JSON dictionary')
parser.add_argument('-o', '--output_path', required=True,
                    help='Output path for segment vectors')
parser.add_argument('-i', '--input_images', required=True,
                    help='Path to input images for inference')


def get_objects(img_result, model_names_list, image_path, seg_id, torch_device):
    """
    Returns a dictionary including the bbox size, confidence and class of each
    object instance detected in an image.
    :param img_result: (tensor) of size (number of objects detected, 6),
    where the columns represent: x1, y1, x2, x2, confidence, class
    :param model_names_list: (list) of classes being predicted (in the order
    they are being encoded)
    :param seg_id: (str)
    :param image_path: (str)
    :param torch_device: one of ['cuda', 'cpu']
    :return: (dict) including the count for each of the classes in model_names_list
    """
    object_dict = {}
    num_objects = img_result.shape[0]

    if torch_device == 'cuda':
        img_result = img_result.cpu()
    img_result = img_result.numpy()

    # Add image and segment ID
    object_dict['segment_id'] = [seg_id] * num_objects
    image_id = image_path.split(os.path.sep)[-1]. \
        split('img_{}_'.format(seg_id))[-1].split('.png')[0]
    object_dict['img_id'] = [image_id] * num_objects

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
    segment_dictionary = load_segment_dict(segment_dictionary_file)

    # Check images directory
    num_images = len(glob.glob(os.path.join(input_images, '*.png')))
    if num_images == 0:
        raise Exception('[ERROR] No images found in images directory.')

    # Load model with custom weights
    print('[INFO] Loading YOLOv5 model with custom weights.')
    model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_weights)
    model_names = model.names

    # Set up intermediate txt file
    logger_path = os.path.join(output_path, 'detections_temp.txt')
    logger = AppendLogger(logger_path)

    # Identify device
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # Verify image neighborhood matches segment dictionary neighborhood
    segment_neighborhood = \
        segment_dictionary_file.split(os.path.sep)[-1].split('.')[0].split('_')[-1]
    image_neighborhood = input_images.split(os.path.sep)[-1].split('_')[0]
    if segment_neighborhood != image_neighborhood:
        raise Exception('[ERROR] Image neighborhood should match segment neighborhood.')

    # Check past progress
    if not os.path.exists(logger_path):
        if not os.path.exists(output_path):
            print('[INFO] Creating output directories: {}'.format(output_path))
            os.makedirs(output_path)
        key_start = 0
    else:
        with open(logger_path, 'r') as file:
            processed_segments = file.readlines()
        processed_segments = [
            segment.split(' ')[0] for segment in processed_segments]
        key_start = len(set(processed_segments)) - 1

    # Inference on each segment and image
    print('[INFO] Generating {} segment vectors for {}'.format(
        len(segment_dictionary) - key_start, segment_neighborhood))
    for key in tqdm(range(key_start, len(segment_dictionary))):
        segment = segment_dictionary[str(key)]

        # Hash segment ID
        segment_id = json.loads(segment['segment_id'])
        segment_id = '{}-{}'.format(segment_id[0], segment_id[1])

        # Get segment images
        images = glob.glob(
            os.path.join(input_images, 'img_{}_*.png'.format(segment_id)))
        image_paths = images.copy()

        # Skip the segment if it has no associated images (identify missing
        # by adding a row of Nones). A segment will usually have no associated
        # images if it had an unavailable heading for it's first node or if
        # it had no associated coordinates.
        if len(image_paths) == 0:
            logger.write('{} {} {} {} {} {}'.format(
                segment_id, None, None, None, None, None))
            continue

        results_list, image_paths_list = [], []
        try:
            results = model(images, size=image_size)
            results_list.append(results)
            image_paths_list.append(image_paths)
        except RuntimeError:
            # Handle out of memory errors
            image_paths_g1 = image_paths[0:int(len(image_paths) / 2)]
            image_paths_g2 = image_paths[int(len(image_paths) / 2):]

            images1 = image_paths_g1.copy()
            images2 = image_paths_g2.copy()

            results1 = model(images1, size=image_size)
            results2 = model(images2, size=image_size)

            results_list.append(results1)
            results_list.append(results2)
            image_paths_list.append(image_paths_g1)
            image_paths_list.append(image_paths_g2)

        # Add to segment vector DataFrame
        # Loop over each image in the segment
        segment_result_counter = 0
        for results_batch, image_paths_batch in zip(results_list, image_paths_list):
            # Loop over each image
            for i in range(len(results_batch)):
                # Get objects and image ID
                img_objects = get_objects(
                    results_batch.xyxy[i], model_names, image_paths_batch[i],
                    segment_id, device)

                # Loop over each object instance in the image and write to logger
                for j in range(len(img_objects['segment_id'])):
                    logger.write('{} {} {} {} {} {}'.format(
                        img_objects['segment_id'][j],  # Segment ID
                        img_objects['img_id'][j],  # Image ID
                        j,  # Object instance ID
                        round(img_objects['confidence'][j], 4),  # Confidence
                        round(img_objects['bbox_size'][j], 2),  # Bounding box size
                        img_objects['class'][j]  # Class
                    ))
                    segment_result_counter += 1

        if segment_result_counter == 0:
            logger.write('{} {} {} {} {} {}'.format(
                segment_id, None, None, None, None, None))

    # Check number of processed object vectors and save to DataFrame
    with open(logger_path, 'r') as file:
        processed_object_vectors = file.readlines()
    processed_segments = [
        segment.split(' ')[0] for segment in processed_object_vectors]
    number_of_processed_segments = len(set(processed_segments))

    # Export to pd.DataFrame if all segments have been processed
    if number_of_processed_segments == len(segment_dictionary):
        df_columns = {'segment_id': [], 'img_id': [], 'object_id': [],
                      'confidence': [], 'bbox_size': [], 'class': []}
        object_vectors = pd.DataFrame(df_columns)

        # Loop over the object instances
        for object_instance in tqdm(processed_object_vectors):
            segment_id, img_id, object_id, confidence, bbox_size, class_id = \
                object_instance.rstrip().split(' ')
            object_instance_dict = {'segment_id': segment_id,
                                    'img_id': img_id,
                                    'object_id': object_id,
                                    'confidence': confidence,
                                    'bbox_size': bbox_size,
                                    'class': class_id}
            object_vectors = object_vectors.append(
                object_instance_dict, ignore_index=True)

        # Export to CSV
        object_vectors.to_csv(
            os.path.join(output_path, 'detections.csv'), index=False)
    else:
        raise Exception('[ERROR] Incomplete street segment temporary file.')
