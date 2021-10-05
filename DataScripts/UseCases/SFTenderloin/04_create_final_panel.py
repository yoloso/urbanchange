# 04_create_final_panel.py
# Generates a final panel for a specific location and time period containing
# treatment and outcome variables, at the quarterly/street-segment level
#
# Usage: Run the following command in terminal after modifying the parameters
#   python 04_create_final_panel.py
#
# Data inputs:
#   - Base panel
#
# Outputs:
#   - CSV file

import datetime
from datetime import date
import json
import numpy as np
import os
import pandas as pd

# Parameters
BASE_PANEL = os.path.join(
    'Data', 'ProcessedData', 'UseCases', 'SFTenderloin', 'base_panel_combined.csv')
OUTPUT_PANEL = os.path.join(
    'Data', 'ProcessedData', 'UseCases', 'SFTenderloin', 'final_panel_combined.csv')
LAGS = 1  # Number of period lags
URBAN_INDEX_COLS = [
    'facade', 'graffiti', 'weed', 'garbage',
    'pothole', 'tent', 'window', 'graffiti2', 'outdoor-establishment',
    'sum', 'weighted_sum', 'facade_log', 'graffiti_log', 'weed_log',
    'garbage_log', 'pothole_log', 'tent_log', 'window_log', 'graffiti2_log',
    'outdoor-establishment_log', 'sum_log', 'weighted_sum_log']


# Helper functions
def aggregate_sum(x):
    if x.empty:
        return None
    else:
        # If all values are NA, return NA
        if np.isnan(x).sum() == len(x):
            return np.nan
        else:
            return np.nansum(x)


def aggregate_mean(x):
    if x.empty:
        return None
    else:
        # If all values are NA, return NA
        if np.isnan(x).sum() == len(x):
            return np.nan
        # Else return mean excluding NA values
        else:
            return np.nanmean(x)


def generate_indicator(x):
    if np.isnan(x):
        return np.nan
    else:
        if x > 0:
            return 1
        else:
            return 0


# Load files
try:
    with open(BASE_PANEL, 'r') as file:
        base_panel = pd.read_csv(file)
except FileNotFoundError:
    print('[ERROR] Base panel not found.')

# Convert dates to DateTime
base_panel['segment_date'] = pd.to_datetime(base_panel['segment_date'])
base_panel['segment_date'] = base_panel['segment_date'].apply(
    lambda z: z.date())

# Add adjacent-segment (2-degree) tent exposure ----------------
base_panel['node1'] = base_panel['segment_id'].apply(lambda z: z.split('-')[0])
base_panel['node2'] = base_panel['segment_id'].apply(lambda z: z.split('-')[1])

base_panel_cp = base_panel.copy()
base_panel_cp.rename(
    columns={'node1': 'node1r', 'node2': 'node2r', 'tent_count': 'tent_countr'},
    inplace=True)

# * Generate panel with the tent values of all adjacent street segments
extended_panel = pd.DataFrame(
    {col: [] for col in list(base_panel.columns) + ['node1r', 'node2r', 'tent_countr']})

# We have to merge four times, twice for each of the two end nodes, as the
# nodes may appear in the left or right hand-side of the hashed street segment
# ID
for x in range(1, 3):
    for y in range(1, 3):
        merged_panel = base_panel.merge(
            base_panel_cp[['segment_date', 'node1r', 'node2r', 'tent_countr']],
            how='left', left_on=['node{}'.format(x), 'segment_date'],
            right_on=['node{}r'.format(y), 'segment_date'])
        # We will double count the current street segment's tent exposure, as
        # this combination will appear twice: one for x==y==1 and another for
        # x==y==2. So we drop it from one of these cases.
        if x == 1 and y == 1:
            merged_panel = merged_panel[
                ~((merged_panel['node{}'.format(x)] == merged_panel['node{}r'.format(y)]) &
                  (merged_panel['node{}'.format(2 if x == 1 else 1)] == merged_panel[
                      'node{}r'.format(2 if y == 1 else 1)]))]
        extended_panel = pd.concat([extended_panel, merged_panel], axis=0)

# * Compute aggregate exposure to tents (including adjacent segments)
extended_panel = extended_panel. \
    groupby(['segment_id', 'segment_date', 'tent_count'] + URBAN_INDEX_COLS,
            dropna=False). \
    agg({'tent_countr': aggregate_sum}).reset_index()
extended_panel.rename(columns={'tent_countr': 'tent_count_2d'}, inplace=True)

# Aggregate observations on a quarterly basis -------------------
# * Generate quarters
quarterly_panel = extended_panel.copy()
quarterly_panel['quarter'] = pd.PeriodIndex(
    quarterly_panel['segment_date'], freq='Q')

# * Aggregate on a quarterly basis by summing over tents and averaging the
# urban index
quarter_aggregations = {
    'tent_count': aggregate_sum, 'tent_count_2d': aggregate_sum}
for col in URBAN_INDEX_COLS:
    quarter_aggregations[col] = aggregate_mean

quarterly_panel = quarterly_panel.groupby(['segment_id', 'quarter']). \
    agg(quarter_aggregations).reset_index()

# Generate final panel with all treatments and outcomes -----------
final_panel = quarterly_panel.copy()

# * Generate treatment lags
for lag in range(1, LAGS + 1):
    final_panel['tent_count_{}'.format(lag)] = final_panel.groupby(
        ['segment_id'])['tent_count'].shift(lag)
    final_panel['tent_count_2d_{}'.format(lag)] = final_panel.groupby(
        ['segment_id'])['tent_count_2d'].shift(lag)

# * Generate tent indicators
final_panel['tent_indicator'] = final_panel['tent_count']. \
    apply(generate_indicator)
final_panel['tent_indicator_2d'] = final_panel['tent_count_2d']. \
    apply(generate_indicator)
final_panel['tent_indicator_1'] = final_panel['tent_count_1']. \
    apply(generate_indicator)
final_panel['tent_indicator_2d_1'] = final_panel['tent_count_2d_1']. \
    apply(generate_indicator)

# Save to output directory ----------------------------------------
final_panel.to_csv(OUTPUT_PANEL, index=False)
