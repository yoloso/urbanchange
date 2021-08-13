# 03_explore_GSV_time_availability.py
#
# Generates maps for a selected location reflecting the availability of GSV
# imagery for different periods.
#
# Usage: Add selected location to the LOCATIONS dictionary in locations.py and
# replace the SELECTED_NEIGHBORHOOD parameter with the dictionary key.
# Modify the LOCATION_TYPE parameter to 'random' if no segment
# dictionary has been generated for a location, or to 'segmentDictionary' to
# query along the location's street segments. If you wish to query along the
# street segments, script 01_generate_street_segments.py must already be run on
# the selected location. Modify the time periods for which to query in the
# PERIODS parameter. If you wish to query randomly, modify the number of
# random locations to generate NUM_LOCATIONS.
#
# Inputs:
#       - LOCATIONS dictionary including a dictionary for the selected location.
#       - If you wish to generate a map along the street segments: JSON
#         dictionary containing the street segments for the selected location
#         at SEGMENT_DICTIONARY
# Outputs:
#       - CSV file containing a list of coordinates (either random or along the
#         street segments), and True/False values for each year reflecting
#         image availability. This is used as an input to generate the maps and
#         is saved because querying for availability is time consuming.
#       - HTML file containing the map for the selected location and coordinate
#         location type at OUTPUT_PATH


from datetime import date
import folium
import geopandas as gpd
import json
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
from shapely.geometry import Point
import streetview
from tqdm import tqdm

from DataScripts.locations import LOCATIONS


# Parameters
PERIODS = {
    '2007': {'start': date(2007, 1, 1), 'end': date(2007, 12, 31)},
    '2008': {'start': date(2008, 1, 1), 'end': date(2008, 12, 31)},
    '2011': {'start': date(2011, 1, 1), 'end': date(2011, 12, 31)},
    '2012': {'start': date(2012, 1, 1), 'end': date(2012, 12, 31)},
    '2013': {'start': date(2013, 1, 1), 'end': date(2013, 12, 31)},
    '2014': {'start': date(2014, 1, 1), 'end': date(2014, 12, 31)},
    '2015': {'start': date(2015, 1, 1), 'end': date(2015, 12, 31)},
    '2016': {'start': date(2016, 1, 1), 'end': date(2016, 12, 31)},
    '2017': {'start': date(2017, 1, 1), 'end': date(2017, 12, 31)},
    '2018': {'start': date(2018, 1, 1), 'end': date(2018, 12, 31)},
    '2019': {'start': date(2019, 1, 1), 'end': date(2019, 12, 31)},
    '2020': {'start': date(2020, 1, 1), 'end': date(2020, 12, 31)},
    'lastyear': {'start': date(2020, 6, 1), 'end': date(2021, 5, 31)}
}
SELECTED_NEIGHBORHOOD = 'MissionTenderloinAshburyCastroChinatown'
LOCATION_TYPE = ['random', 'segmentDictionary'][1]
NUM_LOCATIONS = 5000
INPUT_PATH = os.path.join(
    '..', '..', 'Outputs', 'SFStreetView', 'Time_availability',
    'GSV_{}_locations_{}.csv'.format(LOCATION_TYPE, SELECTED_NEIGHBORHOOD))
SEGMENT_DICTIONARY = os.path.join(
    '..', '..', 'Data', 'ProcessedData', 'SFStreetView',
    'segment_dictionary_{}.json'.format(SELECTED_NEIGHBORHOOD))
OUTPUT_PATH = os.path.join(
    '..', '..', 'Outputs', 'SFStreetView', 'Time_availability')

# Get neighborhood
neighborhood = LOCATIONS[SELECTED_NEIGHBORHOOD]
grid = neighborhood['location']


# Helper functions
def query_location(lat, lng):
    """
    Verifies the availability of GSV imagery for a particular location for
    the selected time periods in the PERIODS dictionary.
    NOTE: Some panoramas are not tagged with a date, and so we cannot be sure
    using this function that there is in fact no image for a given year-location pair.
    :param lat: (float)
    :param lng: (float)
    :return: (list of bool) indicating whether an image is available for each
    period in the PERIODS list for this location.
    """
    # Get panoramas for the location
    panoid_list = streetview.panoids(lat, lng)
    available_periods = [0] * len(PERIODS)

    # Check availability for selected periods
    for panoid in panoid_list:
        if 'year' in panoid.keys():
            # Get panoid date
            pano_date = date(panoid['year'], panoid['month'], 1)

            for t, period in enumerate(list(PERIODS.keys())):
                if PERIODS[period]['start'] <= pano_date <= PERIODS[period]['end']:
                    available_periods[t] += 1

    # Check availability for selected periods
    selected_period_availability = [1 if p > 0 else 0 for p in available_periods]

    return selected_period_availability


def color_marker(year_bool):
    return 'blue' if year_bool else 'gray'


# Track progress
tqdm.pandas()

# Check output directory
if not os.path.exists(OUTPUT_PATH):
    print('[INFO] Creating output directory: {}'.format(OUTPUT_PATH))
    os.makedirs(OUTPUT_PATH)

# Generate random locations to query if input path is not specified
if not os.path.exists(INPUT_PATH):
    if LOCATION_TYPE == 'random':
        print('[INFO] Generating random locations...')
        np.random.seed(42)
        lats = np.random.uniform(
            low=grid[1][0], high=grid[0][0], size=NUM_LOCATIONS)
        lngs = np.random.uniform(
            low=grid[1][1], high=grid[0][1], size=NUM_LOCATIONS)
        locations = pd.DataFrame({'lat': lats, 'lng': lngs})

    elif LOCATION_TYPE == 'segmentDictionary':
        # Read in segment dictionary
        print('[INFO] Loading {} segment dictionary.'.format(SELECTED_NEIGHBORHOOD))
        try:
            with open(SEGMENT_DICTIONARY, 'r') as file:
                segments = json.load(file)
        except FileNotFoundError:
            raise Exception('[ERROR] Segment dictionary not found.')

        # Create DataFrame of locations
        print('[INFO] Creating DataFrame with location coordinates.')
        locations = pd.DataFrame({'lat': [], 'lng': []})
        for key, segment in tqdm(segments.items()):
            for (lat, lng), h1, h2 in segment['coordinates']:
                locations = locations.append(
                    {'lat': lat, 'lng': lng}, ignore_index=True)

    else:
        raise Exception(
            '[ERROR] Location type must be one of [random, segmentDictionary]')

    # Query each location
    print('[INFO] Querying each location to check annual availability.')
    locations[list(PERIODS.keys())] = \
        locations.progress_apply(
            lambda x: query_location(x['lat'], x['lng']), axis=1).tolist()

    locations.to_csv(os.path.join(
        OUTPUT_PATH, 'GSV_{}_locations_{}.csv'.format(
            LOCATION_TYPE, SELECTED_NEIGHBORHOOD)))
else:
    print('[INFO] Loading locations file from input path.')
    locations = pd.read_csv(INPUT_PATH)

# Generate Point objects and GeoDataFrame
locations['geometry'] = locations.apply(
    lambda x: Point(x['lng'], x['lat']), axis=1)
gdf = gpd.GeoDataFrame(locations, geometry='geometry')
gdf.crs = "EPSG:4326"
points = folium.GeoJson(gdf)

# Visualize image availability for each year
print('[INFO] Generating map with yearly layers.')
neighborhood_map = folium.Map(
    location=neighborhood['start_location'], zoom_start=12)

for period in list(PERIODS.keys()):
    # Create period layer and add its markers
    layer = folium.FeatureGroup(name=period, show=False)
    for feature in points.data['features']:
        if feature['geometry']['type'] == 'Point':
            folium.CircleMarker(
                location=list(reversed(feature['geometry']['coordinates'])),
                radius=1,
                color=color_marker(feature['properties'][period])).add_to(layer)
    layer.add_to(neighborhood_map)

# Add Layer control and save map
folium.LayerControl().add_to(neighborhood_map)
neighborhood_map.save(os.path.join(
    OUTPUT_PATH, '{}_{}.html'.format(SELECTED_NEIGHBORHOOD, LOCATION_TYPE)))

# Static maps
for period in list(PERIODS.keys()):
    fig, ax = plt.subplots(figsize=(15, 15))
    if len(gdf[gdf[period] == 1]) > 0:
        gdf[gdf[period] == 1].plot(
            ax=ax, markersize=2, color='#C0C0C0', label='Available')
    if len(gdf[gdf[period] == 0]) > 0:
        gdf[gdf[period] == 0].plot(
            ax=ax, markersize=2, color='#AC0000', label='Unavailable')
    # plt.legend(prop={'size': 15}, frameon=False, loc='lower center', ncol=2)
    ax.axis("off")
    plt.savefig(os.path.join(OUTPUT_PATH, 'StaticMap{}_{}_{}.png'.format(
        SELECTED_NEIGHBORHOOD, LOCATION_TYPE, period)))
