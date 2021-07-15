# 02_create_representation_vectors.py
# Computes a vector representation of each street segment.
#
# Usage: Run the following command in terminal (modified to your neighborhood of choice)
#   python 02_create_representation_vectors.py
#   -v Outputs/Detection/Res_640/MissionDistrictBlock_2011-02-01_3/
#   -s 640
#   -d Data/ProcessedData/SFStreetView/segment_dictionary_MissionDistrict.json
#   -i Data/ProcessedData/SFStreetView/Res_640/MissionDistrictBlock_2011-02-01_3/
#
# Data inputs:
#   - CSV file including one row per detected object instance (generated
#     using 01_detect_segments.py on the selected neighborhoods)
#
# Outputs:
#   - JSON file including a representation of each street segment (exported to
#     the same directory as the input file)
# TODO how to deal with overlap?
import argparse
import json
import os
import pandas as pd
from tqdm import tqdm

from utils import AppendLogger


# Set up command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-v', '--segment_vectors', required=True,
                    help='Input directory for segment vectors produced by 01_detect_segments.py')
parser.add_argument('-s', '--image_size', required=True, default=640,
                    help='Image resolution')
parser.add_argument('-d', '--segment_dictionary', required=True,
                    help='Path to segment dictionary for the location')
parser.add_argument('-i', '--images_dir', required=True,
                    help='Path to the directory containing images.txt')


# Aggregation functions # TODO add normalization
def aggregate_count(df, img_size=None):
    """
    Aggregates a DataFrame representing the object instances observed in a
    particular street segment by counting the number of objects in each class.
    :param df: (pd.DataFrame) containing rows for a particular segment_id, and
    the columns: img_id, confidence, bbox_size and class. Each row represents
    the instance of an object observed in an image associated to the street segment.
    :param img_size: Not used. Added for convenience as it is required by other
    aggregation functions.
    :return: (dict) of counts for each class
    """
    counts = df[['img_id', 'class']].groupby(['class']).count().squeeze()
    return counts.to_dict()


def aggregate_confidence_weighted(df, img_size=None):
    """
    Aggregates a DataFrame representing the object instances observed in a
    particular street segment by counting the number of objects in each class,
    weighted by the confidence of each instance's prediction.
    :param df: (pd.DataFrame) containing rows for a particular segment_id, and
    the columns: img_id, confidence, bbox_size and class. Each row represents
    the instance of an object observed in an image associated to the street segment.
    :param img_size: Not used. Added for convenience as it is required by other
    aggregation functions.
    :return: (dict) of confidence-weighted counts for each class
    """
    # Weight counts
    weighted_counts = df[['confidence', 'class']].groupby(['class']).sum().squeeze()
    return weighted_counts.to_dict()


def aggregate_bbox_weighted(df, img_size):
    """
    Aggregates a DataFrame representing the object instances observed in a
    particular street segment by counting the number of objects in each class,
    weighted by the bounding box coverage of the image of each instance's prediction.
    :param df: (pd.DataFrame) containing rows for a particular segment_id, and
    the columns: img_id, confidence, bbox_size and class. Each row represents
    the instance of an object observed in an image associated to the street segment.
    :param img_size: (int) the size of the image (e.g. 640)
    :return: (dict) of bounding box-weighted counts for each class
    """
    # Normalize bounding boxes to percentage of the image
    df['normalized_bbox'] = df['bbox_size'] / (img_size * img_size) * 100

    weighted_counts = \
        df[['normalized_bbox', 'class']].groupby(['class']).sum().squeeze()
    return weighted_counts.to_dict()


def aggregate_confxbbox_weighted(df, img_size):
    """
    Aggregates a DataFrame representing the object instances observed in a
    particular street segment by counting the number of objects in each class,
    weighted by the bounding box coverage of the image of each instance's
    prediction and its confidence.
    :param df: (pd.DataFrame) containing rows for a particular segment_id, and
    the columns: img_id, confidence, bbox_size and class. Each row represents
    the instance of an object observed in an image associated to the street segment.
    :param img_size: (int) the size of the image (e.g. 640)
    :return: (dict) of bounding box, confidence-weighted counts for each class
    """
    # Normalize bounding boxes to percentage of the image
    df['normalized_bbox'] = df['bbox_size'] / (img_size * img_size) * 100

    # Weight by confidence
    df['conf_normalized_bbox'] = df['normalized_bbox'] * df['confidence']

    weighted_counts = \
        df[['conf_normalized_bbox', 'class']].groupby(['class']).sum().squeeze()
    return weighted_counts.to_dict()


# Define aggregation and normalization types
AGGREGATIONS = {'count': aggregate_count,
                'Conf_weighted': aggregate_confidence_weighted,
                'Bbox_weighted': aggregate_bbox_weighted,
                'ConfxBbox_weighted': aggregate_confxbbox_weighted}

NORMALIZATIONS = {'length': None}


if __name__ == '__main__':
    # Capture command line arguments
    args = vars(parser.parse_args())
    segment_vectors_dir = args['segment_vectors']
    image_size = args['image_size']
    segment_dict_file = args['segment_dictionary']
    images_dir = args['images_dir']

    print('[INFO] Loading segment dictionary, vectors and image log.')
    # Load segment vectors
    try:
        with open(os.path.join(segment_vectors_dir, 'detections.csv'), 'r') as file:
            segment_vectors = pd.read_csv(file)
    except FileNotFoundError:
        raise Exception('[ERROR] Segment vectors file not found.')

    # Load segment dictionary
    try:
        with open(segment_dict_file, 'r') as file:
            segment_dictionary = json.load(file)
    except FileNotFoundError:
        raise Exception('[ERROR] Segment dictionary not found.')

    # Load images.txt file for neighborhood
    try:
        with open(os.path.join(images_dir, 'images.txt'), 'r') as file:
            image_log = pd.read_csv(
                file, sep=' ', header=0,
                names=['segment_id', 'img_id', 'panoid', 'img_date'])
    except FileNotFoundError:
        raise Exception('[ERROR] images.txt file not found.')

    # Note: the image log may potentially have duplicate lines related to the
    # process stopping and picking up again at an unfinished segment.

    # Get selected location-time and verify the three files match
    location_time = segment_vectors_dir.split(os.path.sep)[-1]
    location = location_time.split('_')[0]
    segment_dict_location = \
        segment_dict_file.split(os.path.sep)[-1].split('.')[0].split('_')[-1]
    images_location_time = images_dir.split(os.path.sep)[-1]

    if not (location == segment_dict_location and location_time == images_location_time):
        raise Exception('[ERROR] Input files point to different location-time selections.')
    print('[INFO] Creating representation vectors for {}'.format(location_time))

    # Set up aggregation files
    aggregation_files = {}
    for aggregation in AGGREGATIONS.keys():
        aggregation_files[aggregation] = AppendLogger(
            os.path.join(segment_vectors_dir, '{}_{}.txt'.format(
                location_time, aggregation)))

    # Aggregate vectors
    print('[INFO] Computing segment vector representations.')

    # Recognize past progress
    if os.path.exists(os.path.join(
            segment_vectors_dir, '{}_ConfxBbox_weighted.txt'.format(location_time))):
        with open(os.path.join(
                segment_vectors_dir, '{}_ConfxBbox_weighted.txt'.format(location_time)),
                'r') as file:
            processed_segments = file.readlines()
        key_start = len(set(processed_segments)) - 1
    else:
        key_start = 0

    print('[INFO] Creating vectors for {} street segments.'.format(
        len(segment_dictionary) - key_start))
    for key in tqdm(range(key_start, len(segment_dictionary))):
        segment = segment_dictionary[str(key)]

        # Hash segment ID
        segment_id = json.loads(segment['segment_id'])
        segment_id = '{}-{}'.format(segment_id[0], segment_id[1])

        # Get segment length to normalize vectors
        length = segment['length']

        segment_df = \
            segment_vectors[segment_vectors['segment_id'] == segment_id].copy()

        for aggregation in AGGREGATIONS.keys():
            # Compute aggregation and save to file
            agg_function = AGGREGATIONS[aggregation]
            segment_aggregation = agg_function(segment_df, image_size)

            # Tag with the segment ID
            segment_aggregation = {'segment_id': segment_aggregation}
            row_str = json.dumps(segment_aggregation)

            # Save to file
            agg_logger = aggregation_files[aggregation]
            agg_logger.write(row_str)

    # Save temporary files as JSON
    print('[INFO] Segment representations generated. Exporting temporary files'
          'to JSON.')
    for aggregation in AGGREGATIONS.keys():
        # Get temporary and JSON files for the aggregation
        agg_temporary_file = os.path.join(segment_vectors_dir, '{}_{}.txt'.format(
                location_time, aggregation))
        agg_json_file = os.path.join(segment_vectors_dir, '{}_{}.json'.format(
                location_time, aggregation))

        # Check number of processed segments
        with open(agg_temporary_file, 'r') as file:
            vector_representations = file.readlines()
        number_of_processed_segments = len(vector_representations)

        # Export to JSON if all segments have been processed # TODO deal with missings
        if number_of_processed_segments == len(segment_dictionary) - 1:
            segment_representations_dict = {}
            for segment in vector_representations:
                segment_dict = json.loads(segment)
                for key, item in segment_dict.items():
                    segment_representations_dict[key] = item
            with open(agg_json_file, 'w') as file:
                json.dump(segment_representations_dict, file)
        else:
            raise Exception('[ERROR] Incomplete street segments representations temporary file.')
