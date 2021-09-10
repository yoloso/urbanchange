# 05_explore_GSV_time_frequency.py
#
# Visualizes the quantity of GSV imagery that is available for a location
# during a specified time period.
#
# Usage: Add selected location to the LOCATIONS dictionary in locations.py and
# replace the SELECTED_NEIGHBORHOOD parameter with the dictionary key.
# Modify the LOCATION_TYPE parameter to 'random' if no segment
# dictionary has been generated for a location, or to 'segmentDictionary' to
# query along the location's street segments. If you wish to query along the
# street segments, script 01_generate_street_segments.py must already be run on
# the selected location. Modify the time periods for which to query in the
# PERIODS parameter.
#
# Inputs:
#       - LOCATIONS dictionary including a dictionary for the selected location.
#       - If you wish to generate a map along the street segments: JSON
#         dictionary containing the street segments for the selected location
#         at SEGMENT_DICTIONARY
# Outputs:
#       -


from datetime import date
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import os
import pandas as pd
import streetview
from tqdm import tqdm

from DataScripts.locations import LOCATIONS
from DataScripts.read_files import load_segment_dict


# Parameters
PERIOD = {'start': date(2007, 1, 1), 'end': date(2021, 7, 31)}
SELECTED_NEIGHBORHOOD = 'SFMarketStreet'
INPUT_PATH = os.path.join(
    '..', '..', 'Outputs', 'SFStreetView', 'Time_frequency',
    'GSV_locations_{}.csv'.format(SELECTED_NEIGHBORHOOD))
SEGMENT_DICTIONARY = os.path.join(
    '..', '..', 'Data', 'ProcessedData', 'SFStreetView',
    'segment_dictionary_{}.json'.format(SELECTED_NEIGHBORHOOD))
OUTPUT_PATH = os.path.join(
    '..', '..', 'Outputs', 'SFStreetView', 'Time_frequency')

# Get neighborhood
neighborhood = LOCATIONS[SELECTED_NEIGHBORHOOD]
grid = neighborhood['location']

# Get months covered by period
month_dict = {}
months = [ts.date() for ts in pd.date_range(PERIOD['start'], PERIOD['end'], freq='MS')]
for i, month in enumerate(months):
    month_dict[month] = i


# Helper functions
def query_location_frequency(lat, lng):
    """
    Verifies the frequency of GSV imagery for a particular location in the
    time frame specified by the PERIOD dictionary.
    NOTE: Some panoramas are not tagged with a date, and so we cannot be sure
    using this function that there is in fact no image for a given
    time-location pair.
    :param lat: (float)
    :param lng: (float)
    :return: (list) indicating whether an image is available for each
    month in the time frame specified by PERIOD for this location.
    """
    # Get panoramas for the location
    panoid_list = streetview.panoids(lat, lng)
    available_periods = [0] * len(months)

    # Check availability for selected periods
    for panoid in panoid_list:
        if 'year' in panoid.keys():
            # Get panoid date
            pano_date = date(panoid['year'], panoid['month'], 1)

            if PERIOD['start'] <= pano_date <= PERIOD['end']:
                date_index = month_dict[pano_date]
                available_periods[date_index] = 1

    return available_periods


def save_histogram(data, date_col, y_col, y, title, fig_name):
    fig, ax = plt.subplots(figsize=(15, 7))
    ax = data.set_index(
        data[date_col].map(lambda s: s.strftime('%m-%Y'))).plot.bar(
            ax=ax, y=y_col, legend=False, title=title)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax.set_xlabel('Date')
    ax.set_ylabel(y)
    fig.savefig(os.path.join(OUTPUT_PATH, fig_name))


# Track progress
tqdm.pandas()

# Check output directory
if not os.path.exists(OUTPUT_PATH):
    print('[INFO] Creating output directory: {}'.format(OUTPUT_PATH))
    os.makedirs(OUTPUT_PATH)

# Read in segment dictionary
segments = load_segment_dict(SEGMENT_DICTIONARY)

# Query locations
if not os.path.exists(INPUT_PATH):
    # Create DataFrame of locations
    print('[INFO] Creating DataFrame with location coordinates.')
    locations = pd.DataFrame({'segment_id': [], 'lat': [], 'lng': []})
    for key, segment in tqdm(segments.items()):
        for (lat, lng), h1, h2 in segment['coordinates']:
            locations = locations.append(
                {'segment_id': segment['segment_id'],
                 'lat': lat, 'lng': lng}, ignore_index=True)

    # Query each location
    print('[INFO] Querying each location to check availability.')
    locations[list(month_dict.keys())] = \
        locations.progress_apply(
            lambda x: query_location_frequency(x['lat'], x['lng']), axis=1).tolist()

    locations.to_csv(INPUT_PATH)
else:
    print('[INFO] Loading locations file from input path.')

locations = pd.read_csv(INPUT_PATH)
locations.drop(['Unnamed: 0'], axis=1, inplace=True)

# Melt data
locations_melted = pd.melt(
    locations, id_vars=['segment_id', 'lat', 'lng'], var_name='date',
    value_name='available', ignore_index=True)
locations_melted['date'] = pd.to_datetime(locations_melted['date'], format='%Y-%m-%d')
locations_melted['date'] = locations_melted['date'].apply(lambda x: x.date())

# Histogram of date availability
locations_sum = locations_melted[['date', 'available']].\
    groupby('date').sum().reset_index()
save_histogram(data=locations_sum, date_col='date', y_col='available',
               y='Number of available images in the neighborhood',
               title='Image availability for {}'.format(SELECTED_NEIGHBORHOOD),
               fig_name='{}_total_images.png'.format(SELECTED_NEIGHBORHOOD))

# Histogram of date availability percentage
locations_sum['percentage_av'] = locations_sum['available'] / len(locations)
save_histogram(data=locations_sum, date_col='date', y_col='percentage_av',
               y='Percentage',
               title='Percentage of locations with available '
                     'imagery for {}'.format(SELECTED_NEIGHBORHOOD),
               fig_name='{}_perc_images.png'.format(SELECTED_NEIGHBORHOOD))

# Histogram of segment availability
segment_sum = locations_melted[locations_melted['available'] == 1].copy()
segment_sum = segment_sum[['segment_id', 'date', 'available']].\
    groupby(['segment_id', 'date']).sum().reset_index()
segment_sum = segment_sum[segment_sum['available'] >= 5]
segment_sum = segment_sum.groupby('date').count().reset_index()
segment_sum['percentage_av'] = segment_sum['available'] / len(segments)

full_dates = pd.DataFrame({'month': months})
full_dates = full_dates.merge(
    segment_sum, how='left', left_on='month', right_on='date')

save_histogram(data=full_dates, date_col='month', y_col='percentage_av',
               y='Percentage',
               title='Percentage of available segments for '
                     ' {}'.format(SELECTED_NEIGHBORHOOD),
               fig_name='{}_segment_percentage.png'.format(SELECTED_NEIGHBORHOOD))

# Compute GSV imagery cost estimate
print('[INFO] Imagery cost estimate for the selected period: {}'.format(
    round(locations_sum['available'].sum() * 5.6 / 1000 * 2, 2)))
