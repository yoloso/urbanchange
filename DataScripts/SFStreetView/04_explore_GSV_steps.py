# 04_explore_GSV_steps.py
#
# Generates maps for a selected location reflecting the availability of GSV
# imagery for different years.
#
# Usage: Add selected location to the LOCATIONS dictionary in locations.py and
# replace the SELECTED_NEIGHBORHOOD parameter in line 45 with the dictionary key.
# Modify the LOCATION_TYPE parameter in line 46 to 'random' if no segment
# dictionary has been generated for a location, or to 'segmentDictionary' to
# query along the location's street segments. If you wish to query along the
# street segments, script 01_generate_street_segments.py must already be run on
# the selected location. Modify the years for which to query in the YEARS
# parameter on line 44. If you wish to query randomly, modify the number of
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


from datetime import date, timedelta
import folium
import geopandas as gpd
import json
import matplotlib.pyplot as plt
import os
import pandas as pd
from shapely.geometry import Point
from tqdm import tqdm

import CONFIG
from locations import LOCATIONS
from urbanchange_utils import get_SV_metadata


# Parameters
SELECTED_NEIGHBORHOOD = 'MissionTenderloinAshburyCastroChinatown'
INPUT_PATH = os.path.join(
    '..', '..', 'Outputs', 'SFStreetView', 'GSV_Steps',
    'Steps_{}.csv'.format(SELECTED_NEIGHBORHOOD))
SEGMENT_DICTIONARY = os.path.join(
    '..', '..', 'Data', 'ProcessedData', 'SFStreetView',
    'segment_dictionary_{}.json'.format(SELECTED_NEIGHBORHOOD))
OUTPUT_PATH = os.path.join(
    '..', '..', 'Outputs', 'SFStreetView', 'GSV_Steps')

# Image params
img_params = {
    'size': '640x640',
    'key': CONFIG.SV_api_key}

# Get neighborhood
neighborhood = LOCATIONS[SELECTED_NEIGHBORHOOD]
grid = neighborhood['location']


def color_marker(year_bool):
    return 'blue' if year_bool else 'gray'


# Track progress
tqdm.pandas()

# Check output directory
if not os.path.exists(OUTPUT_PATH):
    print('[INFO] Creating output directory: {}'.format(OUTPUT_PATH))
    os.makedirs(OUTPUT_PATH)

# Query segment dictionary coordinates if temporary file does not exist
if not os.path.exists(INPUT_PATH):
    # Read in segment dictionary
    print('[INFO] Loading {} segment dictionary.'.format(SELECTED_NEIGHBORHOOD))
    try:
        with open(SEGMENT_DICTIONARY, 'r') as file:
            segments = json.load(file)
    except FileNotFoundError:
        raise Exception('[ERROR] Segment dictionary not found.')

    # Create DataFrame of unique panoramas
    print('[INFO] Creating DataFrame with unique panoramas.')
    panoramas = pd.DataFrame({'pano_id': [], 'lat': [], 'lng': []})
    for key, segment in tqdm(segments.items()):
        for (lat, lng), h1, h2 in segment['coordinates']:
            img_params['location'] = '{},{}'.format(lat, lng)
            pano_metadata = get_SV_metadata(params=img_params)
            panoramas = panoramas.append(
                {'pano_id': pano_metadata['pano_id'],
                 'lat': pano_metadata['location']['lat'],
                 'lng': pano_metadata['location']['lng']}, ignore_index=True)

    panoramas.to_csv(INPUT_PATH)
else:
    print('[INFO] Loading locations file from input path.')
    panoramas = pd.read_csv(INPUT_PATH)

# Generate Point objects and GeoDataFrame
panoramas['geometry'] = panoramas.apply(
    lambda x: Point(x['lng'], x['lat']), axis=1)
gdf = gpd.GeoDataFrame(panoramas, geometry='geometry')
gdf.crs = "EPSG:4326"
points = folium.GeoJson(gdf)

# Visualize GSV steps
print('[INFO] Generating map of GSV steps.')
neighborhood_map = folium.Map(
    location=neighborhood['start_location'], zoom_start=12)

for feature in points.data['features']:
    if feature['geometry']['type'] == 'Point':
        folium.CircleMarker(
            location=tuple(reversed(feature['geometry']['coordinates'])),
            radius=1,
            color='#336699').add_to(neighborhood_map)

neighborhood_map.save(os.path.join(
    OUTPUT_PATH, '{}.html'.format(SELECTED_NEIGHBORHOOD)))

# Static map
fig, ax = plt.subplots(figsize=(15, 15))
gdf.plot(ax=ax, markersize=2, color='#336699')
ax.axis("off")
plt.savefig(os.path.join(OUTPUT_PATH, 'StaticMap_{}.png'.format(
    SELECTED_NEIGHBORHOOD)))
