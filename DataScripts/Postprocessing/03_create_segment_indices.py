# 03_create_segment_indices.py
# Computes an index of each street segment.
#
# Usage: Run the following command in terminal (modified to your neighborhood of choice)
#   python 03_create_segment_indices.py
#   -v Outputs/Detection/Res_640/MissionDistrictBlock_2011-02-01_3/
#   -a count
#   -o Outputs/Urban_quality/Res_640
#   -m mark_missing
#   -c 50
#
# Data inputs:
#   - CSV file including a representation of each street segment for an
#     aggregation type (generated using 02_create_representation_vectors.py
#     on the selected neighborhoods)
#
# Outputs:
#   - CSV file including indices of each street segment (exported to the
#     selected output path)

import argparse
import numpy as np
import os
import pandas as pd
from tqdm import tqdm

from object_classes import CLASSES_TO_LABEL

# Parameters
WEIGHTS = {'facade': 0.1,
           'graffiti': 0.2,
           'weed': 0.1,
           'garbage': 0.2,
           'pothole': 0,
           'tent': 0,
           'window': 0.2,
           'graffiti2': 0.1}

# Set up command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-v', '--representation_vectors_dir', required=True,
                    help='Input directory for representation vectors produced '
                         'by 02_create_representation_vectors.py')
parser.add_argument('-a', '--aggregation_type', required=True,
                    help='Aggregation type used to generate segment vectors')
parser.add_argument('-m', '--missing_image', required=True,
                    help='Image normalization used to generate segment vectors')
parser.add_argument('-o', '--output_dir',
                    default=os.path.join('..', '..', 'Outputs', 'Urban_quality', 'Res_640'),
                    help='Output directory path')
parser.add_argument('-c', '--confidence_level', required=True, type=int,
                    help='Minimum confidence level to filter detections (in percent)')


# Aggregation functions
def object_sum(x):
    row_sum = 0
    for object_class in CLASSES_TO_LABEL.keys():
        row_sum += x[object_class]
    return row_sum


def object_weighted_sum(x):
    row_sum = 0
    for object_class in CLASSES_TO_LABEL.keys():
        row_sum += x[object_class] * WEIGHTS[object_class]
    return row_sum


# Define aggregation types
AGGREGATIONS = {
    'sum': object_sum,
    'weighted_sum': object_weighted_sum
}

# Report progress
tqdm.pandas()

if __name__ == '__main__':
    # Capture command line arguments
    args = vars(parser.parse_args())
    representation_vectors_dir = args['representation_vectors_dir']
    aggregation_type = args['aggregation_type']
    missing_image_normalization = args['missing_image']
    output_dir = args['output_dir']
    min_confidence_level = args['confidence_level']

    # Load representation vectors
    try:
        with open(os.path.join(
                representation_vectors_dir, '{}_{}_{}.csv'.format(
                    aggregation_type, missing_image_normalization,
                    str(min_confidence_level))), 'r') as file:
            representation_vectors = pd.read_csv(file)
    except FileNotFoundError:
        raise Exception('[ERROR] Representation vectors file not found.')

    # Identify location and time
    location_time = representation_vectors_dir.split(os.path.sep)[-1]
    location, time = location_time.split('_')[0], location_time.split('_')[1]
    print('[INFO] Computing indices for location: {}; time period: {}'.format(
        location, time))

    # Check output path
    if not os.path.exists(os.path.join(output_dir, location_time)):
        os.makedirs(os.path.join(output_dir, location_time))

    # Compute indices
    for aggregation in AGGREGATIONS:
        agg_fun = AGGREGATIONS[aggregation]
        representation_vectors[aggregation] = \
            representation_vectors.progress_apply(agg_fun, axis=1)

    # Generate logs
    index_cols = [col for col in representation_vectors.columns if col != 'segment_id']
    for index_col in index_cols:
        log_col = '{}_log'.format(index_col)
        representation_vectors[log_col] = representation_vectors[index_col] + 0.0001
        representation_vectors[log_col] = representation_vectors[log_col].apply(np.log)

    # Export
    representation_vectors.to_csv(
        os.path.join(output_dir, location_time,
                     'indices_{}_{}_{}.csv'.format(
                         aggregation_type, missing_image_normalization,
                         str(min_confidence_level))),
        index=False)
