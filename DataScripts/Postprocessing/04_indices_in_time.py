# 04_indices_in_time.py
# Computes an index of change between two time periods for the same location.
#
# Usage: Run the following command in terminal (modified to your location of choice)
#   python 04_indices_in_time.py
#   -d Outputs/Urban_quality/Res_640
#   -l MissionDistrictBlock
#   -t0 2011-02-01_3
#   -t1 2021-02-01_2
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

# Index change functions


# Define change functions # TODO
CHANGES = {
    'absolute_change': None,
    'relative_change': None
}


if __name__ == '__main__':
    # Capture command line arguments
    args = vars(parser.parse_args())
    indices_dir = args['indices_dir']
    location = args['location']
    t0, t1 = args['t0'], args['t1']

    # Load indices
    indices = {}
    for i, time in enumerate([t0, t1]):
        try:
            with open(os.path.join(
                    indices_dir, '{}_{}'.format(location, time), 'indices.csv'),
                    'r') as file:
                indices[str(i)] = pd.read_csv(file)
        except FileNotFoundError:
            raise Exception('[ERROR] Indices for location at '
                            'time {} not found.'.format(time))

    # Check output path
    output_path = os.path.join(indices_dir, '{}_{}_{}'.format(location, t0, t1))
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Merge DataFrames
    for i in [0, 1]:
        index_columns = [col for col in list(indices[str(i)].columns)
                         if col != 'segment_id']
        column_update = {}
        for col_name in index_columns:
            column_update[col_name] = '{}{}'.format(col_name, i)
        indices[str(i)].rename(columns=column_update, inplace=True)
    merged = pd.merge(indices['0'], indices['1'], on='segment_id')

    # Handle missing values
    merged.dropna(inplace=True, axis=0, how='any')

    # TODO get same columns

    # Compute change indices
    for change in CHANGES:
        change_fun = CHANGES[change]

        for object_class in CLASSES_TO_LABEL.keys(): # TODO
            merged['{}_{}'.format(None, None)] = \
                merged[[]].apply(change_fun, axis=1)

    # Export
    merged.to_csv(
        os.path.join(output_path, 'indices.csv'), index=False)
