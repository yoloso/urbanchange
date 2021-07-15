# create_representation_vectors.py
# Computes a vector representation of each street segment.
#
# Usage: Run the following command in terminal (modified to your neighborhood of choice)
#   python create_representation_vectors.py
#   -v Outputs/Detection/Res_640/MissionDistrictBlock_2011-02-01_3/
#   -s 640
#   -d Data/ProcessedData/SFStreetView/segment_dictionary_MissionDistrict.json
#   -i Data/ProcessedData/SFStreetView/Res_640/MissionDistrictBlock_2011-02-01_3/
#
# Data inputs:
#   - CSV file including one row per detected object instance (generated
#     using detect_segments.py on the selected neighborhoods)
#
# Outputs:
#   - CSV file including a representation of each street segment (exported to
#     the same directory as the input file)

import argparse
import json
import os
import pandas as pd
from tqdm import tqdm


# Set up command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-v', '--segment_vectors', required=True,
                    help='Input directory for segment vectors')
parser.add_argument('-s', '--image_size', required=True, default=640,
                    help='Image resolution')
parser.add_argument('-d', '--segment_dictionary', required=True,
                    help='Path to segment dictionary for the location')
parser.add_argument('-i', '--images_dir', required=True,
                    help='Path to the directory containing images.txt')


# Aggregation functions
def aggregate_count(df):
    """
    Aggregates a DataFrame representing the object instances observed in a
    particular street segment by counting the number of objects in each class.
    :param df: (pd.DataFrame) containing rows for a particular segment_id, and
    the columns: img_id, confidence, bbox_size and class. Each row represents
    the instance of an object observed in an image associated to the street segment.
    :return: (dict) of counts for each class
    """
    counts = df[['img_id', 'class']].groupby(['class']).count().squeeze()
    return counts.to_dict()


def aggregate_confidence_weighted(df):
    pass # TODO


def aggregate_bbox_weighted(df):
    pass # TODO


def aggregate_confxbbox_weighted(df):
    pass # TODO


# Define aggregation types
AGGREGATIONS = {'count': aggregate_count,
                'Conf_weighted': aggregate_confidence_weighted,
                'Bbox_weighted': aggregate_bbox_weighted,
                'ConfxBbox_weighted': aggregate_confxbbox_weighted}


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
            image_log = pd.read_csv(file, sep=' ')
    except FileNotFoundError:
        raise Exception('[ERROR] images.txt file not found.')
    # TODO convert images.txt to set from list to remove duplicates

    # Set up aggregation DataFrames
    # TODO

    # Aggregate vectors
    print('[INFO] Computing segment vector representations.')
    for key, segment in tqdm(segment_dictionary.items()):
        # Hash segment ID
        segment_id = json.loads(segment['segment_id'])
        segment_id = '{}-{}'.format(segment_id[0], segment_id[1])

        # Get segment length to normalize vectors
        length = segment['length']

        for aggregation in AGGREGATIONS.keys():
            pass
        # TODO how to deal with overlap????
