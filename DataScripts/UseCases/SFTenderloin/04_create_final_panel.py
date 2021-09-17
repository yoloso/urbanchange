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
    'Data', 'ProcessedData', 'UseCases', 'SFTenderloin', 'base_panel.csv')


# Helper functions
def aggregate_tent_presence(x):
    if x.empty:
        return None
    else:
        if np.isnan(x).sum() == len(x):
            return np.nan
        else:
            tent_sum = np.nansum(x)
            tent_indicator = 1 if tent_sum > 0 else 0
            return tent_indicator


def aggregate_urban_index(x):
    if x.empty:
        return None
    else:
        if np.isnan(x).sum() == len(x):
            return np.nan
        else:
            return np.nanmean(x)


def generate_treatment(row):
    pass # TODO


# Load files
try:
    with open(BASE_PANEL, 'r') as file:
        base_panel = pd.read_csv(file)
except FileNotFoundError:
    print('[ERROR] Base panel not found.')

# Add adjacent-segment (2-degree) tent exposure
base_panel['node1'] = base_panel['segment_id'].apply(lambda z: z.split('-')[0])
base_panel['node2'] = base_panel['segment_id'].apply(lambda z: z.split('-')[1])

base_panel_cp = base_panel.copy()
base_panel_cp.rename(
    columns={'node1': 'node1r', 'node2': 'node2r', 'tent_count': 'tent_countr'},
    inplace=True)

# * Generate panel with the tent values of all adjacent street segments
extended_panel = pd.DataFrame(
    {'segment_id': [], 'segment_date': [], 'tent_count': [], 'index': [],
     'node1': [], 'node2': [], 'node1r': [], 'node2r': [], 'tent_countr': []})

for x in range(1, 3):
    for y in range(1, 3):
        merged_panel = base_panel.merge(
            base_panel_cp[['segment_date', 'node1r', 'node2r', 'tent_countr']],
            how='left', left_on=['node{}'.format(x), 'segment_date'],
            right_on=['node{}r'.format(y), 'segment_date'])
        if x == 1 and y == 1:
            merged_panel = merged_panel[
                ~((merged_panel['node{}'.format(x)] == merged_panel['node{}r'.format(y)]) &
                  (merged_panel['node{}'.format(2 if x == 1 else 1)] == merged_panel[
                      'node{}r'.format(2 if y == 1 else 1)]))]
        extended_panel = pd.concat([extended_panel, merged_panel], axis=0)

# * Compute aggregate exposure to tents (including adjacent segments)
extended_panel = extended_panel.\
    groupby(['segment_id', 'segment_date', 'tent_count', 'index'], dropna=False).\
    sum().reset_index()
# TODO when we sum over adj segments, do we want missing if at least 1 is missing?
extended_panel.rename(columns={'tent_countr': 'tent_count_2d'}, inplace=True)

# TODO ----------------------------------------------------------
# Aggregate observations on a quarterly basis
quarterly_panel = base_panel[
    ['segment_id', 'segment_date', 'tent_indicator', 'index']].copy()
quarterly_panel['quarter'] = pd.PeriodIndex(
    quarterly_panel['segment_date'], freq='Q')

quarterly_panel = quarterly_panel.groupby(['segment_id', 'quarter']).\
    agg({'tent_indicator': aggregate_tent_presence,
         'index': aggregate_urban_index}).reset_index()

# Generate final panel
final_panel = quarterly_panel.copy()

# Generate lagged columns
shifted_panels = [final_panel]
for lag in range(1, TREATMENT + 1):
    # Change column names
    lagged_panel = final_panel[['tent_indicator', 'index']].copy()
    lagged_panel.rename(
        columns={'tent_indicator': 'tent_indicator{}'.format(lag),
                 'index': 'index_indicator{}'.format(lag)}, inplace=True)
    lagged_panel = lagged_panel.shift(lag)
    shifted_panels.append(lagged_panel)

final_panel = pd.concat(shifted_panels, axis=1)
final_panel.to_csv(os.path.join(OUTPUT_DIR, 'lagged_panel_quarters.csv'), index=False)

# Generate treatment column
final_panel['treatment'] = final_panel.apply(lambda row: generate_treatment(row), axis=1)


