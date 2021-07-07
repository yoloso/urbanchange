import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import os
import osmnx as ox
import pandas as pd
from shapely.geometry import Point

from utils import compute_heading, generate_new_latlng_from_distance
from utils import generate_location_graph


# Parameters
R = 6378.1  # Radius of the Earth
DIST = 0.005  # Distance between images (km)
OUTPUT_PATH = os.path.join('..', '..', 'Data', 'ProcessedData', 'SFStreetView')
SELECTED_LOCATION = 'MissionDistrictBlock'
OUTPUT_FILE = 'segment_dictionary_{}.json'.format(SELECTED_LOCATION)
VISUALIZE = True

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
def get_unique_segments(street_data):
    """
    Generates a DataFrame of unique street segments by dropping duplicate edges,
    and generates and ID for each segment.
    :param street_data: pd.DataFrame
    :return: pd.DataFrame
    """
    # Reset the index to get node1, node2
    street_data.reset_index(inplace=True)

    # Get unique (node1, node2) edges for each graph
    street_data['segment_id'] = street_data[['u', 'v']].apply(list, axis=1)
    street_data['segment_id'] = street_data['segment_id'].apply(sorted)
    street_data['segment_id'] = street_data['segment_id'].apply(str)

    # Drop duplicate edges
    street_data.drop_duplicates(['segment_id'], inplace=True)

    return street_data


def check_coordinate_bounds(cur_lat, cur_lng, next_lat, next_lng, new_lat, new_lng):
    """
    Verify that current coordinates are within the segment's length.
    :param cur_lat: (float)
    :param cur_lng: (float)
    :param next_lng: (float)
    :param next_lat: (float)
    :param new_lng: (float)
    :param new_lat: (float)
    :return: (bool)
    """
    # Get current Point and next Points
    cur_point = Point(cur_lng, cur_lat)
    next_point = Point(next_lng, next_lat)
    new_point = Point(new_lng, new_lat)

    # Compare distances
    in_bound = False
    if cur_point.distance(new_point) < cur_point.distance(next_point):
        in_bound = True
    return in_bound


def get_edge_bearing(cur_lat, cur_lng, next_lat, next_lng):
    """
    Returns the bearing for a given edge defined by two nodes.
    :param cur_lng: (float)
    :param cur_lat: (float)
    :param next_lng: (float)
    :param next_lat: (float)
    :return: (float)
    """
    # Get current Point and next Points
    cur_point, next_point = Point(cur_lng, cur_lat), Point(next_lng, next_lat)

    # Filter street segment full data
    subsegments = street_segments_full.copy()
    subsegments = subsegments[
        (subsegments['node1'] == cur_point) & (subsegments['node2'] == next_point)]

    # Get bearing
    if len(subsegments) == 1:
        return subsegments.iloc[0]['bearing']
    else:
        return np.nan


def generate_latlng(linestring, bearing, visualize):
    """
    Generate a list of (coordinate, headings) that traverses each street
    segment.
    :param visualize: (bool) indicate whether to visualize traversal along the
    street segment. IMPORTANT: Only visualize on a case by case basis, and not
    when applying to the entire DataFrame of street segments.
    :param bearing: (float) bearing in degrees
    :param linestring: (shapely.geometry.LineString)
    :return: (list) of ((lat, lng), heading1, heading2) tuples representing the segment
    """
    if pd.isna(bearing):
        return []

    # Get line segment coordinates and current bearing
    line_segment_coords = list(linestring.coords)

    # Set up the DataFrame used for visualization of the traversal
    if visualize:
        df = pd.DataFrame(line_segment_coords)
        df['color'] = 0
        df['geometry'] = df.apply(lambda x: Point(x[0], x[1]), axis=1)
        df = df[['geometry', 'color']]

    # Generate pairs of new ((lat, lng), heading1, heading2) tuples for GSV calls
    GSV_tuples = []
    for i, (lng, lat) in enumerate(line_segment_coords):
        cur_lat, cur_lng = lat, lng

        # Get an adjacent node in order to obtain a bearing
        if i == len(line_segment_coords) - 1:
            next_lng, next_lat = line_segment_coords[i - 1]
        else:
            next_lng, next_lat = line_segment_coords[i + 1]

        # Get the headings for the current node
        cur_bearing = get_edge_bearing(cur_lat, cur_lng, next_lat, next_lng)
        heading1, heading2 = compute_heading(cur_bearing)

        # Add the current node to the list of coordinates
        GSV_tuples.append(((cur_lat, cur_lng), heading1, heading2))

        # Take straight steps in the direction of the current bearing while
        # we reach the next node
        in_bounds = True if i < len(line_segment_coords) - 1 else False

        while in_bounds:
            new_lat, new_lng = generate_new_latlng_from_distance(
                cur_lat=cur_lat, cur_lng=cur_lng, segment_bearing=cur_bearing,
                distance=DIST, radius=R)

            # Check bounds
            in_bounds = check_coordinate_bounds(
                cur_lat=cur_lat, cur_lng=cur_lng, next_lat=next_lat,
                next_lng=next_lng, new_lat=new_lat, new_lng=new_lng)

            if visualize:
                df = df.append(
                    {'geometry': Point(new_lng, new_lat), 'color': 2},
                    ignore_index=True)
                plot_traversal(df)

            # If the step is within bounds, we add it to the list of tuples
            if in_bounds:
                cur_lat, cur_lng = new_lat, new_lng
                GSV_tuples.append(((cur_lat, cur_lng), heading1, heading2))

                if visualize:
                    df = df.append(
                        {'geometry': Point(cur_lng, cur_lat), 'color': 1},
                        ignore_index=True)
                    plot_traversal(df)

    return GSV_tuples


def plot_traversal(df):
    """
    Plots a DataFrame of Points as specified by the 'geometry' column, colored
    by the 'color' column (taking on values in [0, 1, 2].
    :param df: (DataFrame)
    :return: None (generates plot)
    """
    gdf = gpd.GeoDataFrame(df, geometry='geometry')
    fig, ax = plt.subplots()
    gdf[gdf['color'] == 0].plot(ax=ax, color='red')
    gdf[gdf['color'] == 1].plot(ax=ax, color='blue')
    gdf[gdf['color'] == 2].plot(ax=ax, color='green', alpha=0.5)
    fig.show()


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

# Count street segments (unique (node1, node2) edges)
basic_stats = ox.basic_stats(G)
num_street_segments = basic_stats['street_segment_count']

# Visualize street segments in the neighborhood
if VISUALIZE:
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
street_segments, street_segments_full = edges_b.copy(), edges_b_full.copy()

# Get unique (node1, node2) edges for the simplified graph
street_segments = get_unique_segments(street_segments)
# assert (num_street_segments == len(street_segments))
# TODO For SF we compute 576 fewer segments
# TODO: how to identify correct heading for a street like Guerrero?

# Get the (begin, end) nodes from the full street data for each subsegment
street_segments_full[['node1']] = street_segments_full['geometry'].apply(
    lambda x: Point(np.array(x.coords[0], dtype=object)))
street_segments_full[['node2']] = street_segments_full['geometry'].apply(
    lambda x: Point(np.array(x.coords[1], dtype=object)))

# Generate (lat, lng) coordinates for each street segment
# Note: Segment representations can be normalized using street length
street_segments['coordinates'] = street_segments.apply(
    lambda x: generate_latlng(x['geometry'], x['bearing'],
                              visualize=False), axis=1)

# Final dataset structure:
# (segment id, street name, street length (meters), street bearing (degrees),
# list of coordinates and headings)
street_segments = street_segments[
    ['segment_id', 'name', 'length', 'bearing', 'coordinates']]
street_segments.reset_index(inplace=True, drop=True)

# Export dataset
if not os.path.exists(OUTPUT_PATH):
    os.makedirs(OUTPUT_PATH)
street_segments.to_json(os.path.join(OUTPUT_PATH, OUTPUT_FILE), orient='index')

# References
# https://geoffboeing.com/2016/11/osmnx-python-street-networks/
# https://towardsdatascience.com/retrieving-openstreetmap-data-in-python-1777a4be45bb
# https://stackoverflow.com/questions/7222382/get-lat-long-given-current-point-distance-and-bearing
