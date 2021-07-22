# 04_indices_in_time.py
# Computes an index of change between two time periods for the same location.
#
# Usage: Run the following command in terminal (modified to your location of choice)
#   python 04_indices_in_time.py
#   -d Outputs/Urban_quality/Res_640
#   -l MissionDistrictBlock
#   -t0 2011-02-01_3
#   -t1 2021-02-01_2
#   -c 50
#   -m mark_missing
#   -a count
#
# Data inputs:
#   - CSV file including indices of each street segment  (generated using
#     02_create_segment_indices.py on the selected neighborhoods)
#
# Outputs:
#   - CSV file including urban change indices of each street segment (exported
#     to the selected output path)

import argparse
import os
import pandas as pd
from tqdm import tqdm

from object_classes import CLASSES_TO_LABEL

# Set up command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-d', '--indices_dir', required=True,
                    help='Input directory for indices produced '
                         'by 03_create_segment_indices.py',
                    default=os.path.join('..', '..', 'Outputs', 'Urban_quality', 'Res_640'))
parser.add_argument('-l', '--location', required=True,
                    help='Location/neighborhood')
parser.add_argument('--t0', required=True, help='Start time period')
parser.add_argument('--t1', required=True, help='End time period')
parser.add_argument('-c', '--confidence_level', required=True, type=int,
                    help='Minimum confidence level to filter detections (in percent)')
parser.add_argument('-a', '--aggregation_type', required=True,
                    help='Aggregation type used to generate segment vectors')
parser.add_argument('-m', '--missing_image', required=True,
                    help='Image normalization used to generate segment vectors')


# Index change functions
def absolute_change(v0, v1):
    return v1 - v0


def relative_change(v0, v1):
    if abs(v0) < 1e-10:
        return None
    else:
        return (v1 / v0 - 1) * 100


# Define change functions
CHANGES = {
    'absoluteChange': absolute_change,
    'relativeChange': relative_change
}

if __name__ == '__main__':
    # Capture command line arguments
    args = vars(parser.parse_args())
    indices_dir = args['indices_dir']
    location = args['location']
    t0, t1 = args['t0'], args['t1']
    min_confidence_level = args['confidence_level']
    aggregation_type = args['aggregation_type']
    missing_image_normalization = args['missing_image']

    # Load indices
    indices = {}
    for i, time in enumerate([t0, t1]):
        try:
            with open(os.path.join(
                    indices_dir, '{}_{}'.format(location, time),
                    'indices_{}_{}_{}.csv'.format(
                        aggregation_type, missing_image_normalization,
                        str(min_confidence_level))), 'r') as file:
                indices[str(i)] = pd.read_csv(file)
        except FileNotFoundError:
            raise Exception('[ERROR] Indices for location at '
                            'time {} not found.'.format(time))

    # Check output path
    output_path = os.path.join(indices_dir, '{}_{}_{}'.format(location, t0, t1))
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Get columns in common (except segment_id)
    common_cols = set(indices['0'].columns).intersection(set(indices['1'].columns))
    common_cols = [col for col in common_cols if col != 'segment_id']

    # Merge DataFrames
    for i in [0, 1]:
        column_update = {}
        for col_name in common_cols:
            column_update[col_name] = '{}{}'.format(col_name, i)
        indices[str(i)].rename(columns=column_update, inplace=True)
    merged = pd.merge(indices['0'], indices['1'], on='segment_id')

    # Handle missing values
    merged.dropna(inplace=True, axis=0, how='any')

    # Compute change indices
    for change in CHANGES:
        change_fun = CHANGES[change]

        for col_name in common_cols:
            merged['{}_{}'.format(col_name, change)] = merged.apply(
                lambda x: change_fun(x['{}0'.format(col_name)],
                                     x['{}1'.format(col_name)]), axis=1)

    # Keep only change columns
    merged.set_index('segment_id', inplace=True)
    merged = merged[[col for col in merged.columns if 'Change' in col]]

    # Export
    merged.to_csv(
        os.path.join(output_path, 'indices_{}_{}_{}.csv'.format(
                         aggregation_type, missing_image_normalization,
                         str(min_confidence_level))), index=True)
