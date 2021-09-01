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
#
# Note: This script cannot be used for timestamped neighborhoods. Each segment
# ID must have a unique index row with a single date.


import argparse
import branca.colormap as cm
import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import os
import osmnx as ox
import pandas as pd

from DataScripts.locations import LOCATIONS
from DataScripts.urbanchange_utils import generate_location_graph, generate_urbanindex_gdf


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

    # Check that neighborhood is not timestamped
    if '_full_' in location_time:
        raise Exception('[ERROR] This script cannot be used for timestamped'
                        ' locations.')

    # Load indices and index column
    try:
        print('[INFO] Loading indices for {}'.format(location_time))
        with open(os.path.join(
                indices_dir, 'indices_{}_{}_{}.csv'.format(
                    aggregation_type, missing_image_normalization,
                    str(min_confidence_level))), 'r') as file:
            index_data = pd.read_csv(file)
    except FileNotFoundError:
        raise Exception('[ERROR] Indices for location-time not found.')

    try:
        index_data['index'] = index_data[index]
    except KeyError:
        raise Exception('[ERROR] Index not found in Indices DataFrame.')

    # Generate graph and prepare edge data for merge
    G = generate_location_graph(neighborhood=neighborhood, simplify=True)
    _, edge_data = ox.graph_to_gdfs(G)

    complete = generate_urbanindex_gdf(edge_data, index_data)

    # Filter for minimum length
    complete = complete[complete['length'] >= MIN_LENGTH]

    # Add segment id to include in map
    complete['segment_id'] = complete.apply(
        lambda row: '{}-{}'.format(row['node0'], row['node1']), axis=1)

    print('[INFO] Generating maps.')
    output_path = os.path.join(indices_dir, 'Maps')
    if not os.path.exists(output_path):
        print('[INFO] Generating map output path.')
        os.makedirs(output_path)

    # Set up color map
    quantiles = complete['index'].quantile([0.20, 0.40, 0.6, 0.80, 1])
    CMAP_dark = cm.StepColormap(
        colors=['#15068a', '#b02a8f', '#ed7b51', '#fde724'],
        vmin=complete['index'].min(),
        vmax=complete['index'].max(),
        index=[quantiles[0.20], quantiles[0.40], quantiles[0.60],
               quantiles[0.80], quantiles[1.00]]
    )

    CMAP_light = cm.StepColormap(
        colors=['#15068a', '#b02a8f', '#ed7b51', '#fde724'],
        vmin=complete['index'].min(),
        vmax=complete['index'].max(),
        index=[quantiles[0.20], quantiles[0.40], quantiles[0.60],
               quantiles[0.80], quantiles[1.00]]
    )

    # Interactive map
    style_fun = lambda x: {'color': CMAP_dark(x['properties']['index']), 'weight': '1'}
    marker_popup = folium.GeoJsonPopup(fields=['segment_id'])
    gdf = gpd.GeoDataFrame(complete, geometry='geometry')
    interactive_map = folium.Map(
        neighborhood['start_location'], zoom_start=13, tiles='CartoDb dark_matter')
    folium.GeoJson(gdf, style_function=style_fun, popup=marker_popup).add_to(interactive_map)
    interactive_map.save(os.path.join(output_path, 'IntMap_{}_{}_{}_{}.html'.format(
        index, aggregation_type, missing_image_normalization,
        str(min_confidence_level))))

    # Static map
    gdf['color'] = gdf.apply(lambda row: CMAP_light(row['index']), axis=1)

    fig, ax = plt.subplots(figsize=(10, 10))
    gdf.plot(ax=ax, color=gdf['color'])
    plt.axis('off')
    plt.savefig(os.path.join(
        output_path, 'StaticMap_{}_{}_{}_{}.png'.format(
            index, aggregation_type, missing_image_normalization,
            str(min_confidence_level))))
