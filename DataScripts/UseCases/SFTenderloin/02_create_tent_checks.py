# 02_create_base_panel.py
# Generates a CSV file to identify tent false positives
#
# Usage: Run the following command in terminal after modifying the parameters
#   python 02_create_tent_checks.py
#
# Data inputs:
#   - CSV file including one row per detected object instance (generated
#     using 01_detect_segments.py on the selected neighborhoods)
#   - Segment dictionary for the selected neighborhood
#   - Image log for the selected neighborhood generated during the image
#   collection process
#
# Outputs:
#   - CSV file

import os
import pandas as pd

from DataScripts.read_files import prep_object_vectors_with_dates


# Parameters
IMAGES_DIR = os.path.join(
    'Data', 'ProcessedData', 'SFStreetView', 'Res_640',
    'SFTenderloin_full_2009_2021')
OBJECT_VECTORS_DIR = os.path.join(
    'Outputs', 'Detection', 'Res_640', 'SFTenderloin_full_2009_2021')
OUTPUT_DIR = os.path.join(
    'Data', 'ProcessedData', 'UseCases', 'SFTenderloin')

# Load files
object_vectors = prep_object_vectors_with_dates(OBJECT_VECTORS_DIR, IMAGES_DIR)

# Convert dates to datetime
object_vectors['segment_date'] = pd.to_datetime(object_vectors['img_date'])
object_vectors['segment_date'] = object_vectors['segment_date'].apply(
    lambda x: x.date())

# Get tent instances and sort according to confidence level
tent_vectors = object_vectors[object_vectors['class'] == 'tent'].copy()
tent_vectors = tent_vectors.sort_values('confidence')

# Generate complete image name to facilitate false positive identification
tent_vectors['complete_image_name'] = tent_vectors.apply(
    lambda x: 'img_{}_{}'.format(x['segment_id'], x['img_id']), axis=1)
tent_vectors['true_tent'] = None

# Save CSV
tent_vectors.to_csv(os.path.join(OUTPUT_DIR, 'tent_checks.csv'), index=False)
