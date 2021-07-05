import folium
import geopandas
import math
import matplotlib.pyplot as plt
import numpy as np
import os
import osmnx as ox
import pandas as pd
from shapely.geometry import LineString

from utils import compute_heading, generate_new_latlng_from_distance


# Parameters
R = 6378.1  # Radius of the Earth
DIST = 0.005  # Distance between images (km)
OUTPUT_PATH = os.path.join('..', '..', 'Data', 'ProcessedData', 'SFStreetView')
OUTPUT_FILE = 'segment_dictionary_MDblock.json'
SELECTED_LOCATION = 'MissionDistrictBlock'

LOCATIONS = {
    'MissionDistrict': {
        'type': 'box',
        'location': [[37.76583204171835, -122.43090178068529],
                     [37.74947816540197, -122.40373636829808]],
        'start_location': [37.76583204171835, -122.43090178068529]
    },
    'MissionDistrictBlock': {
        'type': 'box',
        'location': [[37.76510958212885, -122.42461359879468],
                     [37.762898815227565, -122.42121402824374]],
        'start_location': [37.76510958212885, -122.42461359879468]
    },
    'SanFrancisco': {
        'type': 'place',
        'location': 'San Francisco, California',
        'start_location': [37.76510958212885, -122.42461359879468]
    },
    'GoldenGateHeights': {
        'type': 'box',
        'location': [[37.76144285680283, -122.47511505804738],
                     [37.75225352830853, -122.4671005110224]],
        'start_location': [37.76144285680283, -122.47511505804738]
    }
}


# Helper functions
def generate_location_graph(loc_type, location, simplify):
    if loc_type == 'box':
        graph = ox.graph_from_bbox(
            location[0][0], location[1][0], location[0][1], location[1][1],
            network_type='drive', simplify=simplify)
        return graph
    elif loc_type == 'place':
        graph = ox.graph_from_place(
            location, network_type='drive', simplify=simplify)
        return graph
    else:
        raise Exception('[ERROR] Location type must be one of [box, place]')


def check_coordinate_bounds(cur_lat, cur_lng, coords):
    """
    Verify that current coordinates are within the segment's length.
    :param cur_lat: (float)
    :param cur_lng: (float)
    :param coords: (list)
    :return: (tuple of boolean)
    """
    lat_in_bounds, lng_in_bounds = False, False

    # Get start and end points
    init_lat, init_lng = coords[0][1], coords[0][0]
    final_lat, final_lng = coords[-1][1], coords[-1][0]

    # Check bounds
    if init_lat <= cur_lat <= final_lat or final_lat <= cur_lat <= init_lat:
        lat_in_bounds = True
    if init_lng <= cur_lng <= final_lng or final_lng <= cur_lng <= init_lng:
        lng_in_bounds = True

    return lat_in_bounds and lng_in_bounds


def generate_latlng(geometry, bearing):
    """

    :param bearing: (float) bearing in degrees
    :param geometry: (shapely.geometry.LineString)
    :return: (list) of (lat, lng) tuples representing the segment
    """
    if pd.isna(bearing):
        return []
    # TODO handle curved streets
    # Get line segment coordinates
    coords = list(geometry.coords)
    cur_lat, cur_lng = coords[0][1], coords[0][0]

    # Generate pairs of new (lat, lng) coordinates
    coordinates = [(cur_lat, cur_lng)]
    in_bounds = True
    while in_bounds:
        new_lat, new_lng = generate_new_latlng_from_distance(
            cur_lat=cur_lat, cur_lng=cur_lng, segment_bearing=bearing,
            distance=DIST, radius=R)
        coordinates.append((new_lat, new_lng))

        # Update coordinates and check bounds
        cur_lat, cur_lng = new_lat, new_lng
        in_bounds = check_coordinate_bounds(
            cur_lat=cur_lat, cur_lng=cur_lng, coords=coords)

    return coordinates


# Define the neighborhood and generate the simplified and full graphs
neighborhood = LOCATIONS[SELECTED_LOCATION]
G = generate_location_graph(
    loc_type=neighborhood['type'], location=neighborhood['location'], simplify=True)
G_full = generate_location_graph(
    loc_type=neighborhood['type'], location=neighborhood['location'], simplify=False)
nodes, edges = ox.graph_to_gdfs(G)

# Visualize neighborhood
G_projected = ox.project_graph(G)
ox.plot_graph(G_projected)

# Count street segments
# Note: Street segments are unique (node1, node2) edges
basic_stats = ox.basic_stats(G)
num_street_segments = basic_stats['street_segment_count']

# Visualize street segments in the neighborhood
style = {'color': '#F7DC6F', 'weight': '1'}
Gmap = folium.Map(neighborhood['start_location'], zoom_start=15,
                  tiles='CartoDb dark_matter')
folium.GeoJson(edges, style_function=lambda x: style).add_to(Gmap)
Gmap.save('{}Edges.html'.format(SELECTED_LOCATION))

# Add street bearings
# Note: "Bearing represents angle in degrees (clockwise) between north and the
# geodesic line from from the origin node to the destination node"
# https://osmnx.readthedocs.io/en/stable/osmnx.html#module-osmnx.bearing
G_bearings = ox.add_edge_bearings(G)
nodes_b, edges_b = ox.graph_to_gdfs(G_bearings)

G_bearings_full = ox.add_edge_bearings(G_full)
nodes_b_full, edges_b_full = ox.graph_to_gdfs(G_bearings_full)

# Build dataset of street segments
street_segments = edges_b.copy()
street_segments.reset_index(inplace=True)

# Get unique (node1, node2) edges
street_segments['segment_id'] = street_segments[['u', 'v']].apply(list, axis=1)
street_segments['segment_id'] = street_segments['segment_id'].apply(sorted)
street_segments['segment_id'] = street_segments['segment_id'].apply(str)
street_segments.drop_duplicates(['segment_id'], inplace=True)
#assert (num_street_segments == len(street_segments))
# TODO For SF we compute 576 fewer segments

# Get 'heading' parameter for GSV call
# TODO: how to identify correct heading for a street like Guerrero?
# TODO curved streets
street_segments[['heading1', 'heading2']] = \
    street_segments['bearing'].apply(compute_heading).tolist()

# Generate (lat, lng) coordinates for each street segment
# Note: Segment representations can be normalized using street length
street_segments['coordinates'] = \
    street_segments.apply(lambda x: generate_latlng(x['geometry'], x['bearing']),
                          axis=1)

# Final dataset structure:
# (StreetSegment id, street name, street length (meters),
# street bearing (degrees), heading1, heading2, list of coordinates)
street_segments = street_segments[['segment_id', 'name', 'length', 'bearing',
                                   'heading1', 'heading2', 'coordinates']]
street_segments.reset_index(inplace=True, drop=True)

# Export dataset
if not os.path.exists(OUTPUT_PATH):
    os.makedirs(OUTPUT_PATH)
street_segments.to_json(os.path.join(OUTPUT_PATH, OUTPUT_FILE), orient='index')


# References
# https://geoffboeing.com/2016/11/osmnx-python-street-networks/
# https://towardsdatascience.com/retrieving-openstreetmap-data-in-python-1777a4be45bb
# https://stackoverflow.com/questions/7222382/get-lat-long-given-current-point-distance-and-bearing
