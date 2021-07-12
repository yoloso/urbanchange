# visualize_urban_quality.py
#
# PENDING


import branca.colormap as cm
import folium
import geopandas as gpd
import json
import matplotlib.pyplot as plt
import numpy as np
import os
import osmnx as ox
import pandas as pd

from locations import LOCATIONS
from utils import generate_location_graph


# Parameters
SELECTED_LOCATION = 'MissionDistrict'
INPUT_PATH = os.path.join(
    'DataScripts', '..', 'Outputs', 'SFStreetView', 'Urban_quality',
    'Segments_{}.csv'.format(SELECTED_LOCATION))
OUTPUT_PATH = os.path.join(
    'DataScripts', '..', 'Outputs', 'SFStreetView', 'Urban_quality')
CMAP = cm.LinearColormap(
    colors=['lightcoral', 'royalblue'], vmin=0, vmax=1)


# Define the neighborhood and get graph
neighborhood = LOCATIONS[SELECTED_LOCATION]
G = generate_location_graph(neighborhood=neighborhood, simplify=True)
nodes, edges = ox.graph_to_gdfs(G)

# Create toy data (this will later be replaced by the outputs of the CNN)
# TODO Replace --------------------------------
np.random.seed(42)
SEGMENT_DICTIONARY = os.path.join(
    'DataScripts', '..', 'Data', 'ProcessedData', 'SFStreetView',
    'segment_dictionary_{}.json'.format(SELECTED_LOCATION))
try:
    print('[INFO] Loading segment dictionary for {}'.format(SELECTED_LOCATION))
    with open(SEGMENT_DICTIONARY, 'r') as segment_file:
        segment_dictionary = json.load(segment_file)
except FileNotFoundError:
    raise Exception('[ERROR] Segment dictionary not found.')

toy_data = pd.DataFrame({'node0': [], 'node1': [], 'value': []})
for key, segment in segment_dictionary.items():
    # Hash segment ID
    segment_id = json.loads(segment['segment_id'])
    node0, node1 = segment_id[0], segment_id[1]
    random_value = np.random.rand(1)[0]

    # Append twice to DataFrame with random value
    # (one time for each direction of the edge)
    toy_data = toy_data.append(
        {'node0': node0, 'node1': node1, 'value': random_value},
        ignore_index=True)
    toy_data = toy_data.append(
        {'node0': node1, 'node1': node0, 'value': random_value},
        ignore_index=True)

segment_values = toy_data
# TODO End Replace --------------------------------

# Prepare edge data for merge
edges = edges[['osmid', 'name', 'geometry']]
edges.reset_index(inplace=True)

# Merge segment data and graph data
edges = pd.merge(edges, segment_values, how='left', left_on=['u', 'v'],
                 right_on=['node0', 'node1'], validate='many_to_one')

# Check for missing values
# TODO is this needed?

# Interactive map
style_fun = lambda x: {'color': CMAP(x['properties']['value']), 'weight': '1'}

interactive_map = folium.Map(
    neighborhood['start_location'], zoom_start=13, tiles='CartoDb dark_matter')
folium.GeoJson(edges, style_function=style_fun).add_to(interactive_map)
interactive_map.save(os.path.join(
    OUTPUT_PATH, 'Segments_Map_{}.html'.format(SELECTED_LOCATION)))

# Static map
gdf = gpd.GeoDataFrame(edges, geometry='geometry')
gdf['color'] = gdf.apply(lambda row: CMAP(row['value']), axis=1)

fig, ax = plt.subplots(figsize=(10, 10))
gdf.plot(ax=ax, color=gdf['color'])
plt.axis('off')
plt.title('Mission District')
plt.savefig(os.path.join(
    OUTPUT_PATH, 'Segments_StaticMap_{}.png'.format(SELECTED_LOCATION)))
