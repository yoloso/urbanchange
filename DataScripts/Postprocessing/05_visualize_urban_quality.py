# 05_visualize_urban_quality.py
# Visualizes the indices of each street segment in a given location.
#
# Usage: Run the following command in terminal (modified to your neighborhood of choice)
#   python 05_visualize_urban_quality.py
#   -d Outputs/Urban_quality/Res_640/MissionDistrictBlock_2011-02-01_3/
#   -i garbage -m mark_missing -c 50 -a count
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
MIN_LENGTH = 0  # Filter segments for this minimum length

# Set up command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-d', '--indices_dir', required=True,
                    help='Input directory for urban quality indices produced '
                         'by 03_create_segment_indices.py and '
                         '04_indices_in_time.py')
parser.add_argument('-a', '--aggregation_type', required=True,
                    help='Aggregation type used to generate segment vectors')
parser.add_argument('-m', '--missing_image', required=True,
                    help='Image normalization used to generate segment vectors')
parser.add_argument('-i', '--index', required=True,
                    help='Index to plot (must match column name in indices.csv)')
parser.add_argument('-c', '--confidence_level', required=True, type=int,
                    help='Minimum confidence level to filter detections (in percent)')

if __name__ == '__main__':
    # Capture command line arguments
    args = vars(parser.parse_args())
    indices_dir = args['indices_dir']
    aggregation_type = args['aggregation_type']
    missing_image_normalization = args['missing_image']
    index = args['index']
    min_confidence_level = args['confidence_level']

    # Grab location and location attributes for plotting
    location_time = indices_dir.split(os.path.sep)[-1]
    location = location_time.split('_')[0]
    neighborhood = LOCATIONS[location]

    # Load indices and index column
    try:
        print('[INFO] Loading indices for {}'.format(location_time))
        with open(os.path.join(
                indices_dir, 'indices_{}_{}_{}.csv'.format(
                    aggregation_type, missing_image_normalization,
                    str(min_confidence_level))), 'r') as file:
            indices = pd.read_csv(file)
    except FileNotFoundError:
        raise Exception('[ERROR] Indices for location-time not found.')

    try:
        indices['index'] = indices[index]
    except KeyError:
        raise Exception('[ERROR] Index not found in Indices DataFrame.')

    # Generate graph and prepare edge data for merge
    G = generate_location_graph(neighborhood=neighborhood, simplify=True)
    _, edges = ox.graph_to_gdfs(G)

    edges = edges[['osmid', 'name', 'geometry', 'length']]
    edges.reset_index(inplace=True)
    edges = edges.drop_duplicates(subset=['u', 'v'])

    # Get nodes and index column from indices
    indices['node0'] = indices['segment_id'].str.split('-', expand=True)[0]
    indices['node1'] = indices['segment_id'].str.split('-', expand=True)[1]

    indices = indices[['node0', 'node1', 'index']]
    indices = indices.astype({"node0": np.int64, "node1": np.int64})

    # Merge segment data and graph data
    # Note: We need to merge twice, otherwise we get missing geometry values.
    # This is because in 01_generate_street_segments we ordered the node values
    # numerically, and some edges are only 1 directional.
    indices0 = pd.merge(indices, edges, how='left', left_on=['node0', 'node1'],
                        right_on=['u', 'v'], validate='many_to_one')
    indices1 = pd.merge(indices, edges, how='left', left_on=['node0', 'node1'],
                        right_on=['v', 'u'], validate='many_to_one')
    indices0.dropna(subset=['geometry'], inplace=True)
    indices1.dropna(subset=['geometry'], inplace=True)

    # Get complete data by concatenating both DataFrames and dropping duplicates
    indices_full = pd.concat([indices0, indices1])
    indices_full.drop_duplicates(subset=['node0', 'node1'], inplace=True)
    complete = pd.merge(indices, indices_full[['node0', 'node1', 'geometry', 'length']],
                        how='left', validate='one_to_one')

    # Drop missing index values
    complete.dropna(subset=['index'], inplace=True)

    # Filter for minimum length
    complete = complete[complete['length'] >= MIN_LENGTH]

    # Apply log for visualization purposes
    complete['index'] += complete['index'] + 0.0001
    complete['index'] = complete['index'].apply(np.log)

    print('[INFO] Generating maps.')
    output_path = os.path.join(indices_dir, 'Maps')
    if not os.path.exists(output_path):
        print('[INFO] Generating map output path.')
        os.makedirs(output_path)

    # Set up color map (red: higher urban decay; blue: lower urban decay)
    CMAP = cm.LinearColormap(
        colors=['royalblue', 'lightcoral'], vmin=complete['index'].min(),
        vmax=complete['index'].max())

    # Interactive map
    style_fun = lambda x: {'color': CMAP(x['properties']['index']), 'weight': '1'}

    gdf = gpd.GeoDataFrame(complete, geometry='geometry')
    interactive_map = folium.Map(
        neighborhood['start_location'], zoom_start=13, tiles='CartoDb dark_matter')
    folium.GeoJson(gdf, style_function=style_fun).add_to(interactive_map)
    interactive_map.save(os.path.join(output_path, 'IntMap_{}_{}_{}_{}.html'.format(
        index, aggregation_type, missing_image_normalization,
        str(min_confidence_level))))

    # Static map
    gdf['color'] = gdf.apply(lambda row: CMAP(row['index']), axis=1)

    fig, ax = plt.subplots(figsize=(10, 10))
    gdf.plot(ax=ax, color=gdf['color'])
    plt.axis('off')
    plt.title(location)
    plt.savefig(os.path.join(
        output_path, 'StaticMap_{}_{}_{}_{}.png'.format(
            index, aggregation_type, missing_image_normalization,
            str(min_confidence_level))))
