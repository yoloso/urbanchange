import folium
import geopandas
import matplotlib.pyplot as plt
import numpy as np
import os
import osmnx as ox
from shapely.geometry import LineString


# Helper functions
def compute_heading(bearing):
    """
    Computes a tuple of headings to be used in the 'heading' parameter of the
    Google Street View API such that the images for a given street segment
    face its buildings at a 90 degree angle.
    :param bearing: The street segment's orientation
    :return: (tuple)
    """
    if 90 >= bearing >= 0:
        return [bearing + 90, bearing + 270]
    elif bearing <= 270:
        return [bearing + 90, bearing - 90]
    elif bearing <= 360:
        return [bearing - 90, bearing - 270]
    else:
        raise Exception('[ERROR] Bearing should be between 0 and 360.')


def generate_latlng(geometry, segment_length):
    """

    :param geometry: (shapely.geometry.LineString)
    :param segment_length:
    :return: (list) of (lat, lng) tuples representing the segment
    """
    # Get line segment bounds
    bounds = geometry.bounds
    # TODO
    pass


# Define the geographic location / neighborhood
neighborhood = {'name': 'MissionDistrict',
                'location': [[37.76583204171835, -122.43090178068529],
                             [37.74947816540197, -122.40373636829808]]}

# Mission District block (for testing)
neighborhood = {'name': 'MissionDistrictBlock',
                'location': [[37.76510958212885, -122.42461359879468],
                             [37.762898815227565, -122.42121402824374]]}

# Generate graph and visualize
G = ox.graph_from_bbox(neighborhood['location'][0][0],
                       neighborhood['location'][1][0],
                       neighborhood['location'][0][1],
                       neighborhood['location'][1][1],
                       network_type='drive')
G_projected = ox.project_graph(G)
ox.plot_graph(G_projected)
nodes, edges = ox.graph_to_gdfs(G)

# Count street segments
# Note: Street segments are unique (node1, node2) edges
basic_stats = ox.basic_stats(G)
num_street_segments = basic_stats['street_segment_count']

# Visualize street segments in the neighborhood
style = {'color': '#F7DC6F', 'weight': '1'}
Gmap = folium.Map(neighborhood['location'][0], zoom_start=15,
                  tiles='CartoDb dark_matter')
folium.GeoJson(edges, style_function=lambda x: style).add_to(Gmap)
Gmap.save('{}Edges.html'.format(neighborhood['name']))

# Add street bearings
# Note: "Bearing represents angle in degrees (clockwise) between north and the
# geodesic line from from the origin node to the destination node"
# https://osmnx.readthedocs.io/en/stable/osmnx.html#module-osmnx.bearing
G_bearings = ox.add_edge_bearings(G)
nodes_b, edges_b = ox.graph_to_gdfs(G_bearings)

# Build dataset of street segments
street_segments = edges_b.copy()
street_segments.reset_index(inplace=True)

# Get unique (node1, node2) edges
street_segments['segment_id'] = street_segments[['u', 'v']].apply(list, axis=1)
street_segments['segment_id'] = street_segments['segment_id'].apply(sorted)
street_segments['segment_id'] = street_segments['segment_id'].apply(str)
street_segments.drop_duplicates(['segment_id'], inplace=True)
assert(num_street_segments == len(street_segments))

# Get 'heading' parameter for GSV call
# Note: Heading should be perpendicular to street orientation
# TODO: how to identify correct heading for a street like Guerrero?
street_segments[['heading1', 'heading2']] = \
    street_segments['bearing'].apply(compute_heading).tolist()

street_segments = street_segments[['segment_id', 'name', 'length', 'geometry',
                                   'heading1', 'heading2']]

# Segment partitioning: Generate the (lat, lng) tuples for each
# street segment to be used in each GSV call
# Note: Segment representations can be normalized using street length
street_segments['coordinates'] = \
    street_segments[['geometry', 'length']].apply(generate_latlng)

# Camp Street tests
length = street_segments[street_segments['name'] == 'Camp Street']['length'][0]
geom = street_segments[street_segments['name'] == 'Camp Street']['geometry'][0]


# Final dataset structure:
# (StreetSegment id, ((lat,lng), headings, length)

# References
# https://geoffboeing.com/2016/11/osmnx-python-street-networks/
# https://towardsdatascience.com/retrieving-openstreetmap-data-in-python-1777a4be45bb
