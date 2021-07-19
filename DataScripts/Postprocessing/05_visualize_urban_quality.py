# 05_visualize_urban_quality.py
# Visualizes the indices of each street segment in a given location.
#
# Usage: Run the following command in terminal (modified to your neighborhood of choice)
#   python 05_visualize_urban_quality.py
#   -v Outputs/Detection/Res_640/MissionDistrictBlock_2011-02-01_3/
#   -s 640
#   -d Data/ProcessedData/SFStreetView/segment_dictionary_MissionDistrict.json
#   -i Data/ProcessedData/SFStreetView/Res_640/MissionDistrictBlock_2011-02-01_3/
#   -m mark_missing
#
# Data inputs:
#   - CSV file including an index of each street segment (generated using
#     03_create_segment_indices.py on the selected neighborhoods)
#
# Outputs:
#   - PNG and HTML files including the static and interactive maps saved to
#     the specified OUTPUT_PATH

import argparse
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
CMAP = cm.LinearColormap(
    colors=['lightcoral', 'royalblue'], vmin=0, vmax=1)

# Set up command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-d', '--indices_dir', required=True,
                    help='Input directory for urban quality indices produced '
                         'by 03_create_segment_indices.py and '
                         '04_indices_in_time.py',
                    default=os.path.join('..', '..', 'Outputs', 'Urban_quality', 'Res_640'))
parser.add_argument('-l', '--location-time', required=True,
                    help='Location/neighborhood and time period')
parser.add_argument('-i', '--index', required=True,
                    help='Index to plot (must match column name in indices.csv)')


if __name__ == '__main__':
    # Capture command line arguments
    args = vars(parser.parse_args())
    indices_dir = args['indices_dir']
    location_time = args['location-time']
    index = args['index']

    # Grab location and location attributes for plotting
    location = location_time.split('_')[0]
    neighborhood = LOCATIONS[location]

    # Generate graph and prepare edge data for merge
    G = generate_location_graph(neighborhood=neighborhood, simplify=True)
    nodes, edges = ox.graph_to_gdfs(G)

    edges = edges[['osmid', 'name', 'geometry']]
    edges.reset_index(inplace=True)

    # Load indices
    try:
        print('[INFO] Loading indices for {}'.format(location_time))
        with open(os.path.join(
                indices_dir, location_time, 'indices.csv'), 'r') as file:
            indices = pd.read_csv(file)
    except FileNotFoundError:
        raise Exception('[ERROR] Indices for location-time not found.')

    # Get nodes and index column from indices
    indices['node0'] = indices['segment_id'].str.split('-', expand=True)[0]
    indices['node1'] = indices['segment_id'].str.split('-', expand=True)[1]

    try:
        indices['index'] = indices[index]
    except KeyError:
        raise Exception('[ERROR] Index not found in Indices DataFrame.')

    indices = indices[['node0', 'node1', 'index']]
    indices = indices.astype({"node0": int, "node1": int})

    # Merge segment data and graph data
    edges = pd.merge(edges, indices, how='left', left_on=['u', 'v'],
                     right_on=['node0', 'node1'], validate='many_to_one')

    # Drop missing values
    edges.dropna(subset=['index'], inplace=True)

    print('[INFO] Generating maps.')
    output_path = os.path.join(indices_dir, location_time)

    # Interactive map
    style_fun = lambda x: {'color': CMAP(x['properties']['index']), 'weight': '1'}

    interactive_map = folium.Map(
        neighborhood['start_location'], zoom_start=13, tiles='CartoDb dark_matter')
    folium.GeoJson(edges, style_function=style_fun).add_to(interactive_map)
    interactive_map.save(os.path.join(output_path, 'IntMap_{}.html'.format(index)))

    # Static map
    gdf = gpd.GeoDataFrame(edges, geometry='geometry')
    gdf['color'] = gdf.apply(lambda row: CMAP(row['index']), axis=1)

    fig, ax = plt.subplots(figsize=(10, 10))
    gdf.plot(ax=ax, color=gdf['color'])
    plt.axis('off')
    plt.title(location)
    plt.savefig(os.path.join(
        output_path, 'StaticMap_{}.png'.format(index)))
