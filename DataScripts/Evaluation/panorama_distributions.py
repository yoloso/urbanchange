# panorama_distributions.py
# This is an exploratory script to analyze the frequency of panoramas

import folium
import geopandas as gpd
import json
import matplotlib.pyplot as plt
import os
import pandas as pd
import plotly.express as px
from shapely.geometry import Point


from DataScripts.locations import LOCATIONS
from DataScripts.read_files import prep_object_vectors, prep_image_log
from DataScripts.read_files import load_segment_dict


# Parameters
object_vectors_dir = os.path.join(
    'Outputs', 'Detection', 'Res_640', 'MissionDistrictBlock_2011-02-01')
images_dir = os.path.join(
    'Data', 'ProcessedData', 'SFStreetView', 'Res_640',
    'MissionDistrictBlock_2011-02-01')
min_confidence_level = 50
neighborhood = LOCATIONS['MissionDistrictBlock']
output_path = os.path.join(
    'Outputs', 'SFStreetView', 'Panorama_distributions',
    'MissionDistrictBlock_2011-02-01.html')
segment_dictionary_file = os.path.join(
    'Data', 'ProcessedData', 'SFStreetView',
    'segment_dictionary_MissionDistrictBlock.json')

# Load files
object_vectors = prep_object_vectors(object_vectors_dir)
image_log = prep_image_log(images_dir)
segment_dictionary = load_segment_dict(segment_dictionary_file)

# Filter for saved images
image_log = image_log[image_log['img_id'] != 'NotSaved']

# Filter objects for minimum confidence level
object_vectors = object_vectors[
    object_vectors['confidence'] >= min_confidence_level / 100]

# Drop missing object vectors
object_vectors = object_vectors.dropna()

# Plot panorama geographic distribution
image_log['geometry'] = image_log.apply(
    lambda x: Point(x['pano_lng'], x['pano_lat']), axis=1)
gdf = gpd.GeoDataFrame(image_log, geometry='geometry')
gdf.crs = "EPSG:4326"

neighborhood_map = folium.Map(
    location=neighborhood['start_location'], zoom_start=12)
points = folium.GeoJson(gdf)

# Create period layer and add its markers
for feature in points.data['features']:
    if feature['geometry']['type'] == 'Point':
        folium.CircleMarker(
            location=list(reversed(feature['geometry']['coordinates'])),
            radius=1,
            color='blue').add_to(neighborhood_map)

# Save map
if not os.path.exists(os.path.dirname(output_path)):
    os.makedirs(os.path.dirname(output_path))
neighborhood_map.save(os.path.join(output_path))

# Relationship between available panoramas and object counts
available_panoramas = image_log[['segment_id', 'img_id']].\
    groupby('segment_id').count().reset_index()

num_objects = object_vectors[['segment_id', 'object_id']].\
    groupby('segment_id').count().reset_index()

counts = available_panoramas.merge(
    num_objects, how='left', on='segment_id', validate='one_to_one')

counts.plot.scatter(x='img_id', y='object_id')
plt.xlabel('Number of panoramas per street segment')
plt.ylabel('Number of objects counted per street segment')
plt.show()

# Relationship between number of panoramas and street segment length
segment_df = pd.DataFrame({'segment_id': [], 'length': []})
for key, value in segment_dictionary.items():
    # Hash segment ID
    segment_id = json.loads(value['segment_id'])
    segment_id = '{}-{}'.format(segment_id[0], segment_id[1])

    segment_df = segment_df.append(
        {'segment_id': segment_id, 'length': value['length']},
        ignore_index=True)

counts = counts.merge(segment_df, on='segment_id', validate='one_to_one')

counts.plot.scatter(x='length', y='img_id')
plt.xlabel('Street segment length')
plt.ylabel('Number of panoramas per street segment')
plt.show()

# 3d plot
fig = px.scatter_3d(counts, x='length', y='img_id', z='object_id')
fig.show()
