import geopandas as gpd
import matplotlib.pyplot as plt
import os
import osmnx as ox

from DataScripts.locations import LOCATIONS
from DataScripts.urbanchange_utils import generate_location_graph, AppendLogger

OUTPUT_PATH = os.path.join('..', '..', 'Outputs', 'Writeup')
SELECTED_LOCATION = 'MissionTenderloinAshburyCastroChinatown'
WIDER_LOCATION = 'SanFrancisco'
OUTPUT_FILE = 'segmentsmap_{}.png'.format(SELECTED_LOCATION)

if not os.path.exists(OUTPUT_PATH):
    os.makedirs(OUTPUT_PATH)

neighborhood = LOCATIONS[SELECTED_LOCATION]
neighborhood_wider = LOCATIONS[WIDER_LOCATION]

print('[INFO] loading neighborhood graph')
G = generate_location_graph(neighborhood=neighborhood, simplify=True)
_, edges = ox.graph_to_gdfs(G)

print('[INFO] loading wider neighborhood graph')
Gw = generate_location_graph(neighborhood=neighborhood_wider, simplify=True)
_, edgesw = ox.graph_to_gdfs(Gw)

gdf = gpd.GeoDataFrame(edges, geometry='geometry')
gdfw = gpd.GeoDataFrame(edgesw, geometry='geometry')

print('[INFO] Plotting')
fig, ax = plt.subplots(figsize=(10, 10))
gdfw.plot(ax=ax, color='gray')
gdf.plot(ax=ax, color='crimson')
plt.axis('off')
plt.savefig(os.path.join(OUTPUT_PATH, OUTPUT_FILE))
