# image_dates.py
# This is merely an exploratory script to analyze the object detection results.


from datetime import date
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd


# Parameters
images_file = os.path.join(
    '..', '..', 'Data', 'ProcessedData', 'SFStreetView', 'Res_640',
    'MissionTenderloinAshburyCastroChinatown_2021-02-01', 'images.txt')
segment_vectors_dir = os.path.join(
    '..', '..', 'Outputs', 'Detection', 'Res_640',
    'MissionTenderloinAshburyCastroChinatown_2021-02-01')

# Read images file
try:
    with open(images_file, 'r') as file:
        image_log = pd.read_csv(
            file, sep=' ', header=0,
            names=['segment_id', 'img_id', 'panoid', 'img_date'],
            na_values=['None'])
except FileNotFoundError:
    raise Exception('[ERROR] images.txt file not found.')

# Read detections file
try:
    with open(os.path.join(segment_vectors_dir, 'detections.csv'), 'r') as file:
        object_vectors = pd.read_csv(
            file, dtype={'segment_id': object, 'img_id': object,
                         'object_id': object, 'confidence': float,
                         'bbox_size': float, 'class': object},
            na_values=['None'])
except FileNotFoundError:
    raise Exception('[ERROR] Segment vectors file not found.')

# Filter for saved images
image_log = image_log[image_log['img_id'] != 'NotSaved']
image_log = image_log[image_log['img_date'].notnull()]
image_log['img_date'] = image_log['img_date'].apply(
    lambda x: date(int(x.split('-')[0]), int(x.split('-')[1]), 1)
)

# View histogram of dates
image_log['img_date'].hist()
plt.show()

# Check correlation between image dates and number of objects counted
# * Get image date
object_counts = object_vectors[['segment_id', 'img_id', 'object_id']].\
    groupby(['segment_id', 'img_id']).count().reset_index()
object_counts.rename(columns={'object_id': 'num_objects'}, inplace=True)

object_counts['full_img_id'] = object_counts.apply(
    lambda x: 'img_{}_{}.png'.format(x['segment_id'], x['img_id']),
    axis=1)

object_counts_dates = image_log.merge(
    object_counts, how='left', left_on='img_id', right_on='full_img_id',
    validate='many_to_one')

# Assign zero to NA cases as there were no detections for these images
object_counts_dates['num_objects'] = object_counts_dates['num_objects'].apply(
    lambda x: 0 if np.isnan(x) else x)

# Convert date to float
min_date = object_counts_dates['img_date'].min()
object_counts_dates['date_float'] = object_counts_dates['img_date'].apply(
    lambda x: (x - min_date).total_seconds() / 10000)

object_counts_dates[['num_objects', 'date_float']].corr()

object_counts_dates.groupby(['img_date']).mean()
