import folium
import geopandas as gpd
import json
import numpy as np
import os
import pandas as pd
from shapely.geometry import Point
import streetview
from tqdm import tqdm

from locations import LOCATIONS

# Parameters
YEARS = [2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021]
SELECTED_NEIGHBORHOOD = 'GoldenGateHeights'
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
years_str = [str(year) for year in YEARS]


# Helper functions
def query_location(lat, lng):
    """
    Verifies the availability of GSV imagery for a particular location for
    the selected years in the YEARS list.
    NOTE: Some panoramas are not tagged with a date, and so we cannot be sure
    using this function that there is in fact no image for a given year-location pair.
    :param lat: (float)
    :param lng: (float)
    :return: (list of bool) indicating whether an image is available for each
    year in the YEARS list for this location.
    """
    # Get panoramas for the location
    panoid_list = streetview.panoids(lat, lng)
    available_years = []

    # Check availability for selected years
    for panoid in panoid_list:
        if 'year' in panoid.keys():
            available_years.append(panoid['year'])

    # Check availability for selected years
    available_years = set(available_years)
    selected_year_availability = []
    for year in YEARS:
        selected_year_availability.append(year in available_years)

    return selected_year_availability


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
    locations[years_str] = \
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

for year in years_str:
    # Create annual layer and add its markers
    layer = folium.FeatureGroup(name=year, show=False)
    for feature in points.data['features']:
        if feature['geometry']['type'] == 'Point':
            folium.CircleMarker(
                location=list(reversed(feature['geometry']['coordinates'])),
                radius=1,
                color=color_marker(feature['properties'][year])).add_to(layer)
    layer.add_to(neighborhood_map)

# Add Layer control and save map
folium.LayerControl().add_to(neighborhood_map)
neighborhood_map.save(os.path.join(
    OUTPUT_PATH, '{}_{}.html'.format(SELECTED_NEIGHBORHOOD, LOCATION_TYPE)))
