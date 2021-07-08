import folium
import numpy as np
import os
import pandas as pd
import streetview
from tqdm import tqdm

from locations import LOCATIONS


# Parameters
YEARS = [2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021]
SELECTED_NEIGHBORHOOD = 'MissionDistrict'
NUM_LOCATIONS = 5000
INPUT_PATH = os.path.join(
    '..', '..', 'Outputs', 'SFStreetView', 'Time_availability',
    'GSV_locations_{}.csv'.format(SELECTED_NEIGHBORHOOD))
OUTPUT_PATH = os.path.join(
    '..', '..', 'Outputs', 'SFStreetView', 'Time_availability')

# Get neighborhood
neighborhood = LOCATIONS[SELECTED_NEIGHBORHOOD]
grid = neighborhood['location']


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


def add_marker(lat, lng, year_bool, location_map):
    """
    Add a marker to a map and color it according to a boolean variable (year_bool).
    :param location_map: (folium.Map)
    :param lat: (float)
    :param lng: (float)
    :param year_bool: (bool)
    :return: folium.CircleMarker
    """
    # Get color
    color = 'blue' if year_bool == 1 else 'gray'

    # Add to map
    folium.CircleMarker(
        location=[lat, lng], radius=1, color=color, alpha=0.6).add_to(location_map)


# Track progress
tqdm.pandas()

# Check output directory
if not os.path.exists(OUTPUT_PATH):
    print('[INFO] Creating output directory: {}'.format(OUTPUT_PATH))
    os.makedirs(OUTPUT_PATH)

# Generate random locations to query if input path is not specified
if not os.path.exists(INPUT_PATH):
    print('[INFO] Generating random locations...')
    np.random.seed(42)
    lats = np.random.uniform(
        low=grid[1][0], high=grid[0][0], size=NUM_LOCATIONS)
    lngs = np.random.uniform(
        low=grid[1][1], high=grid[0][1], size=NUM_LOCATIONS)
    locations = pd.DataFrame({'lat': lats, 'lng': lngs})

    # Query each location
    years_str = [str(year) for year in YEARS]
    locations[years_str] = \
        locations.progress_apply(
        lambda x: query_location(x['lat'], x['lng']), axis=1).tolist()

    locations.to_csv(os.path.join(
        OUTPUT_PATH, 'GSV_locations_{}.csv'.format(SELECTED_NEIGHBORHOOD)))
else:
    print('[INFO] Loading locations file from input path.')
    locations = pd.read_csv(INPUT_PATH)


# Visualize image availability for each year
print('[INFO] Generating yearly maps.')
for year in years_str:
    # Load map centred on average coordinates
    neighborhood_map = folium.Map(location=neighborhood['start_location'], zoom_start=12)
    locations.apply(
        lambda x: add_marker(x['lat'], x['lng'], x[year], neighborhood_map), axis=1)

    # Save map
    neighborhood_map.save(os.path.join(
        OUTPUT_PATH, '{}_{}.html'.format(SELECTED_NEIGHBORHOOD, year)))
