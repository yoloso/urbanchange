# object_distributions.py
# This is an exploratory script to visualize object distributions.

from datetime import date
import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import os
import osmnx as ox
import pandas as pd
from shapely.geometry import Point

from DataScripts.locations import LOCATIONS
from DataScripts.object_classes import CLASSES_TO_LABEL
from DataScripts.read_files import prep_object_vectors_with_dates
from DataScripts.urbanchange_utils import generate_location_graph


# Parameters
object_vectors_dir = os.path.join(
    '..', '..', 'Outputs', 'Detection', 'Res_640',
    'SFTenderloin_full_2009_2021')
images_dir = os.path.join(
    '..', '..', 'Data', 'ProcessedData', 'SFStreetView', 'Res_640',
    'SFTenderloin_full_2009_2021')
URBAN_INDEX_FILE = os.path.join(
    '..', '..', 'Outputs', 'Urban_quality', 'Res_640',
    'SFTenderloin_full_2009_2021', 'indices_count_pano_adjustment_50.csv')
min_confidence_level = 50
SELECTED_NEIGHBORHOOD = 'SFTenderloin'
output_path = os.path.join(
    '..', '..', 'Outputs', 'Detection', 'Res_640',
    'SFTenderloin_full_2009_2021', 'Maps')
TIMESTAMPED_NEIGHBORHOOD = True

neighborhood = LOCATIONS[SELECTED_NEIGHBORHOOD]


def color_marker(obj_class):
    color_dict = {
        'facade': '#999999',
        'graffiti': '#E69F00',
        'weed': '#56B4E9',
        'garbage': '#009E73',
        'pothole': '#F0E442',
        'tent': '#0072B2',
        'window': '#D55E00',
        'graffiti2': '#CC79A7',
        'outdoor-establishment': '#FFFFFF'
    }
    return color_dict[obj_class]


# Set up output directory
if not os.path.exists(output_path):
    os.makedirs(output_path)

# Load detected objects and urban index
object_locations = prep_object_vectors_with_dates(object_vectors_dir, images_dir)

try:
    urban_index = pd.read_csv(URBAN_INDEX_FILE)
except FileNotFoundError:
    raise Exception('[ERROR] Urban index file not found.')

# Filter objects for minimum confidence level
object_locations = object_locations[
    object_locations['confidence'] >= min_confidence_level / 100]

# Filter for missing location values
object_locations = object_locations[
    (object_locations['pano_lat'].notnull()) & (object_locations['pano_lng'].notnull())]

# Set up dates
object_locations['img_date'] = pd.to_datetime(object_locations['img_date'])
object_locations['img_date'] = object_locations['img_date'].apply(
    lambda x: x.date())

urban_index['segment_date'] = pd.to_datetime(urban_index['segment_date'])
urban_index['segment_date'] = urban_index['segment_date'].apply(lambda x: x.date())

# Set up GeoDataFrame
object_locations['geometry'] = object_locations.apply(
    lambda x: Point(x['pano_lng'], x['pano_lat']), axis=1)
gdf = gpd.GeoDataFrame(object_locations, geometry='geometry')
gdf.crs = "EPSG:4326"

# Interactive maps ---------------------------------------
neighborhood_map = folium.Map(
    location=neighborhood['start_location'], zoom_start=12,
    tiles='CartoDb dark_matter')
interactive_gdf = gdf[['segment_id', 'geometry', 'class']]

for obj_class in list(CLASSES_TO_LABEL.keys()):
    # Filter class objects
    points = folium.GeoJson(interactive_gdf[interactive_gdf['class'] == obj_class])

    # Create period layer and add its markers
    layer = folium.FeatureGroup(name=obj_class, show=False)
    for feature in points.data['features']:
        if feature['geometry']['type'] == 'Point':
            folium.CircleMarker(
                location=list(reversed(feature['geometry']['coordinates'])),
                radius=1,
                color=color_marker(obj_class)).add_to(layer)
    layer.add_to(neighborhood_map)

# Add Layer control and save map
folium.LayerControl().add_to(neighborhood_map)
neighborhood_map.save(os.path.join(output_path, 'obj_distributions.html'))

# Static maps ---------------------------------------------
if TIMESTAMPED_NEIGHBORHOOD:
    gdf['year'] = gdf['img_date'].apply(lambda x: x.year)
    YEARS = range(gdf['year'].min(), gdf['year'].max() + 1)
else:
    gdf['year'] = 'fixed'
    YEARS = ['fixed']

neighborhood = LOCATIONS[SELECTED_NEIGHBORHOOD]
G = generate_location_graph(neighborhood=neighborhood, simplify=True)
_, edges = ox.graph_to_gdfs(G)

edges = edges[['geometry']].copy()
edges.reset_index(inplace=True)
edges = edges.drop_duplicates(subset=['u', 'v'])
gdf_edges = gpd.GeoDataFrame(edges, geometry='geometry')

# Color edges according to imagery availability
urban_index['year'] = urban_index['segment_date'].apply(lambda x: x.year)


def check_nodes(u, v, seg_set):
    if '{}-{}'.format(u, v) in seg_set or '{}-{}'.format(v, u) in seg_set:
        return 'black'
    else:
        return 'lightgray'


for year in YEARS:
    # Get imagery availability
    annual_segments = set(
        urban_index[urban_index['year'] == year]['segment_id'].to_list())
    gdf_edges['color'] = gdf_edges.apply(
        lambda row: check_nodes(row['u'], row['v'], annual_segments), axis=1)

    for obj_class in list(CLASSES_TO_LABEL.keys()):
        current_gdf = gdf[(gdf['class'] == obj_class) & (gdf['year'] == year)].copy()
        if len(current_gdf) == 0:
            continue

        fig, ax = plt.subplots(figsize=(10, 10))
        gdf_edges.plot(ax=ax, color=gdf_edges['color'])
        current_gdf.plot(ax=ax, color='crimson')
        plt.axis('off')
        plt.savefig(os.path.join(
            output_path, 'StaticMap_{}_{}.png'.format(obj_class, year)))
