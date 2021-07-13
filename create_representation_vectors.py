# create_representation_vectors.py
# Computes a vector representation of each street segment.
#
# Usage: Run the following command in terminal (modified to your neighborhood of choice)
#   python create_representation_vectors.py
#   -i Outputs/Detection/MissionDistrictBlock_2011-02-01_3/
#
# Data inputs:
#   - CSV file including one row per detected object instance (generated
#     using detect_segments.py on the selected neighborhoods)
#
# Outputs:
#   - CSV file including a representation of each street segment (exported to
#     the same directory as the input file)

import argparse
import os
import pandas as pd


# Set up command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-i', '--input_dir', required=True,
                    help='Input directory for segment vectors')
parser.add_argument('-s', '--size', required=True, default=640, help='Image size')


if __name__ == '__main__':
    # Capture command line arguments
    args = vars(parser.parse_args())
    input_dir = args['input_dir']
    image_size = args['size']

    # Load segment vectors
    try:
        with open(os.path.join(input_dir, 'detections.csv'), 'r') as file:
            segment_vectors = pd.read_csv(file)
    except FileNotFoundError:
        raise Exception('[ERROR] Segment vectors file not found.')

    # Load images.txt file for neighborhood

    # Aggregate vectors
    pass

