# 01_urban_changes.py
# Generates the time period vectors for Tenderloin as an annual average
# of the segment's monthly representation vectors

import os
import pandas as pd


# Parameters
URBAN_VECTORS = os.path.join('..', '..', '..',
    'Outputs', 'Detection', 'Res_640', 'SFTenderloin_full_2009_2021',
    'count_pano_adjustment_50.csv')
OUTPUT_T0 = os.path.join('..', '..', '..',
    'Outputs', 'Detection', 'Res_640', 'SFTenderloin_2011-MM-01',
    'count_pano_adjustment_50.csv')
OUTPUT_T1 = os.path.join('..', '..', '..',
    'Outputs', 'Detection', 'Res_640', 'SFTenderloin_2021-MM-01',
    'count_pano_adjustment_50.csv')

# Create output directories
for output_file in [OUTPUT_T0, OUTPUT_T1]:
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

# Read in the vectors and adjust the date column
vectors = pd.read_csv(URBAN_VECTORS)
vectors['date'] = pd.to_datetime(vectors['segment_date'])
vectors['date'] = vectors['date'].apply(lambda x: x.date())
vectors['year'] = vectors['date'].apply(lambda x: x.year)

# Aggregate the monthly vectors
annual_vectors = vectors.groupby(['segment_id', 'year']).mean().reset_index()

# Export vectors for 2009 and 2021
annual_vectors.rename(columns={'year': 'segment_date'})
annual_vectors[annual_vectors['year'] == 2011].to_csv(OUTPUT_T0, index=False)
annual_vectors[annual_vectors['year'] == 2021].to_csv(OUTPUT_T1, index=False)
