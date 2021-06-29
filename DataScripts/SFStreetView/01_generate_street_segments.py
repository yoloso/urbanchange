import folium
import geopandas
import matplotlib.pyplot as plt
import numpy as np
import os
import osmnx as ox


# Neighborhood graph
neighborhood = {'name': 'MissionDistrict',
                'location': [[37.76583204171835, -122.43090178068529],
                             [37.74947816540197, -122.40373636829808]]}

G = ox.graph_from_bbox(neighborhood['location'][0][0], neighborhood['location'][1][0],
                       neighborhood['location'][0][1], neighborhood['location'][1][1],
                       network_type='drive')
G_projected = ox.project_graph(G)
ox.plot_graph(G_projected)
nodes, edges = ox.graph_to_gdfs(G)

# Count street segments
basic_stats = ox.basic_stats(G)
num_street_segments = basic_stats['street_segment_count'] # TODO Why is this less?

# Visualize street segments in the neighborhood
style = {'color': '#F7DC6F', 'weight':'1'}
Gmap = folium.Map(neighborhood['location'][0], zoom_start=15,
                  tiles='CartoDb dark_matter')
folium.GeoJson(edges, style_function=lambda x: style).add_to(Gmap)
Gmap.save('{}Edges.html'.format(neighborhood['name']))

# Geocode street segments

# TODO Define true street segments

# TODO get street orientation

# TODO partition segments

# (StreetSegment id, ((lat,lng) tuples for GSV images, street orientation)


# References
# https://geoffboeing.com/2016/11/osmnx-python-street-networks/
# https://towardsdatascience.com/retrieving-openstreetmap-data-in-python-1777a4be45bb
