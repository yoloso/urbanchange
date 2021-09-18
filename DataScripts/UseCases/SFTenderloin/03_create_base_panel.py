# 03_create_base_panel.py
# Generates a base panel for a specific location and time period containing
# monthly observations of tent presence and urban index at the street segment
# level.
#
# Usage: Run the following command in terminal after modifying the parameters
#   python 03_create_base_panel.py
#
# Data inputs:
#   - CSV file containing detected tent instances (tent_checks.csv)
#   - Segment dictionary for the selected neighborhood
#   - Urban index generated by 04_indices_in_time.py
#
# Outputs:
#   - CSV file

from datetime import date
import json
import os
import pandas as pd

from DataScripts.read_files import load_segment_dict


# Parameters
SEGMENT_DICTIONARY_FILE = os.path.join(
    'Data', 'ProcessedData', 'SFStreetView',
    'segment_dictionary_SFTenderloin.json')
TENT_DETECTIONS_FILE = os.path.join(
    'Data', 'ProcessedData', 'UseCases', 'SFTenderloin', 'tent_checks.csv')
URBAN_INDEX = os.path.join(
    'Outputs', 'Urban_quality', 'Res_640', 'SFTenderloin_full_2009_2021',
    'indices_count_pano_adjustment_50_excludingtents.csv')
OUTPUT_DIR = os.path.join(
    'Data', 'ProcessedData', 'UseCases', 'SFTenderloin')
SELECTED_INDEX = 'weighted_sum_log'
PERIOD = {'start': date(2009, 1, 1), 'end': date(2021, 7, 31)}
CONFIDENCE_LEVEL = 0


# Load files
segment_dictionary = load_segment_dict(SEGMENT_DICTIONARY_FILE)

try:
    with open(TENT_DETECTIONS_FILE, 'r') as file:
        tent_vectors = pd.read_csv(file)
except FileNotFoundError:
    raise Exception('[ERROR] Tent checks file not found.')

# Load selected urban index
try:
    with open(URBAN_INDEX, 'r') as file:
        urban_index = pd.read_csv(file)
except FileNotFoundError:
    raise Exception('[ERROR] Urban index file not found.')

try:
    urban_index['index'] = urban_index[SELECTED_INDEX]
    urban_index = urban_index[['segment_id', 'segment_date', 'index', 'tent']]
except KeyError:
    raise Exception('[ERROR] Selected index is not found in urban index file.')

# Convert dates to datetime
tent_vectors['segment_date'] = pd.to_datetime(tent_vectors['img_date'])
urban_index['segment_date'] = pd.to_datetime(urban_index['segment_date'])

tent_vectors['segment_date'] = tent_vectors['segment_date'].apply(
    lambda x: x.date())
urban_index['segment_date'] = urban_index['segment_date'].apply(
    lambda x: x.date())

# Filter tent instances for false positives and/or confidence level
tent_vectors = tent_vectors[tent_vectors['confidence'] >= CONFIDENCE_LEVEL / 100]
tent_vectors = tent_vectors[tent_vectors['true_tent'] == 1]

# Aggregate tent detections at the street segment level
tent_vectors = tent_vectors.groupby(['segment_id', 'segment_date']).size().\
    reset_index(name='count')

# Generate base panel
months = [ts.date() for ts in pd.date_range(
    PERIOD['start'], PERIOD['end'], freq='MS')]
month_df = pd.DataFrame({'segment_date': months})

hashed_segments = [
    json.loads(seg['segment_id']) for seg in segment_dictionary.values()]
hashed_segments = ['{}-{}'.format(seg_id[0], seg_id[1]) for seg_id in hashed_segments]
segment_df = pd.DataFrame({'segment_id': hashed_segments})

# Add tent count to base panel
base_panel = segment_df.merge(month_df, how='cross')
base_panel = base_panel.merge(
    tent_vectors[['segment_id', 'segment_date', 'count']],
    how='left', on=['segment_id', 'segment_date'], validate='one_to_one')

# Add urban index to base panel
base_panel = base_panel.merge(
    urban_index[['segment_id', 'segment_date', 'index', 'tent']],
    how='left', on=['segment_id', 'segment_date'], validate='one_to_one')

# Modify zeros in base panel: We need to identify cases where zero tents
# were detected, as these are currently fake "nan"s
base_panel['tent_count'] = base_panel.apply(
    lambda row: 0 if pd.isnull(row['count']) and pd.notnull(row['index'])
    else row['count'],
    axis=1)

# Save base panel
base_panel[['segment_id', 'segment_date', 'tent_count', 'index']].\
    to_csv(os.path.join(OUTPUT_DIR, 'base_panel.csv'), index=False)
