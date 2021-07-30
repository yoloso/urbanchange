# object_distributions.py
# This is an exploratory script to visualize object distributions.

import folium
import geopandas as gpd
import os
import pandas as pd
from shapely.geometry import Point

from DataScripts.locations import LOCATIONS
from DataScripts.object_classes import CLASSES_TO_LABEL
from DataScripts.read_files import prep_object_vectors, prep_image_log


# Parameters
object_vectors_dir = os.path.join(
    'Outputs', 'Detection', 'Res_640', 'MissionDistrictBlock_2011-02-01')
images_dir = os.path.join(
    'Data', 'ProcessedData', 'SFStreetView', 'Res_640',
    'MissionDistrictBlock_2011-02-01')
min_confidence_level = 50
neighborhood = LOCATIONS['MissionDistrictBlock']
output_path = os.path.join(
    'Outputs', 'Detection', 'Res_640', 'MissionDistrictBlock_2011-02-01',
    'obj_distributions.html')


def color_marker(obj_class):
    color_dict = {
        'facade': '#999999',
        'graffiti': '#E69F00',
        'weed': '#56B4E9',
        'garbage': '#009E73',
        'pothole': '#F0E442',
        'tent': '#0072B2',
        'window': '#D55E00',
        'graffiti2': '#CC79A7'
    }
    return color_dict[obj_class]


# Load detected objects and image log
object_vectors = prep_object_vectors(object_vectors_dir)
image_log = prep_image_log(images_dir)

# Filter for saved images
image_log = image_log[image_log['img_id'] != 'NotSaved']

# Filter objects for minimum confidence level
object_vectors = object_vectors[
    object_vectors['confidence'] >= min_confidence_level / 100]

# Merge object_vectors and image_log
object_vectors['full_img_id'] = object_vectors.apply(
    lambda x: 'img_{}_{}.png'.format(x['segment_id'], x['img_id']),
    axis=1)
object_locations = object_vectors.merge(
    image_log[['img_id', 'img_date', 'pano_lat', 'pano_lng']],
    how='left', left_on='full_img_id', right_on='img_id', validate='many_to_one')

# Plot
object_locations['geometry'] = object_locations.apply(
    lambda x: Point(x['pano_lng'], x['pano_lat']), axis=1)
gdf = gpd.GeoDataFrame(object_locations, geometry='geometry')
gdf.crs = "EPSG:4326"

# Visualize objects for each class
neighborhood_map = folium.Map(
    location=neighborhood['start_location'], zoom_start=12)

for obj_class in list(CLASSES_TO_LABEL.keys()):
    # Filter class objects
    points = folium.GeoJson(gdf[gdf['class'] == obj_class])

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
neighborhood_map.save(os.path.join(output_path))
