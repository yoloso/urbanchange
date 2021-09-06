import branca.colormap as cm
import geopandas as gpd
from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt
import os
import osmnx as ox
from shapely.geometry import Point
import pandas as pd

from DataScripts.locations import LOCATIONS
from DataScripts.urbanchange_utils import generate_location_graph, generate_urbanindex_gdf


# Parameters
PROJECT_DATA = os.path.join(
    'Data', 'ProcessedData', 'UseCases', 'MexicoCity',
    'cuauhtemoc_presupuesto_long.csv')
URBAN_INDEX = os.path.join(
    'Outputs', 'Urban_quality', 'Res_640',
    'MexicoCityCentroDoctores_2017-08-01_2019-03-01',
    'indices_count_pano_adjustment_50.csv')
SELECTED_NEIGHBORHOOD = 'MexicoCityCentroDoctores'
OUTPUT_PATH = os.path.join(
    'Outputs', 'UseCases', 'MexicoCityCentroDoctores'
)


# Helper functions
def plot_index_project_selection(
        edge_data, index_data, project_data, selected_projects, selected_index,
        plot_name):
    # Set up segment data (merge edge and index data)
    index_data['index'] = index_data[selected_index]
    complete = generate_urbanindex_gdf(edge_data, index_data)
    gdf_segments = gpd.GeoDataFrame(complete, geometry='geometry')

    # Set up project data
    project_data = project_data[project_data['Type'].isin(selected_projects)]
    gdf_projects = gpd.GeoDataFrame(project_data, geometry='geometry')

    # Set up color map
    quantiles = complete['index'].quantile([0.20, 0.40, 0.6, 0.80, 1])
    CMAP_dark = cm.StepColormap(
        colors=['#15068a', '#b02a8f', '#ed7b51', '#fde724'],
        vmin=complete['index'].min(),
        vmax=complete['index'].max(),
        index=[quantiles[0.20], quantiles[0.40], quantiles[0.60],
               quantiles[0.80], quantiles[1.00]]
    )

    # Generate static map
    gdf_segments['color'] = gdf_segments.apply(lambda row: CMAP_dark(row['index']), axis=1)
    gdf_projects['color'] = gdf_projects.apply(lambda row: color_projects(row['Type']), axis=1)

    fig, ax = plt.subplots(figsize=(10, 10))
    gdf_segments.plot(ax=ax, color=gdf_segments['color'])
    gdf_projects.plot(ax=ax, column='Type', categorical=True, legend=True,
                      legend_kwds={'title': 'Project types', 'edgecolor': 'white',
                                   'facecolor': 'white',
                                   'loc': 'lower center', 'ncol': 2}, cmap='Pastel2')
    plt.axis('off')
    plt.savefig(os.path.join(
        OUTPUT_PATH, 'StaticMap_{}_{}.png'.format(
            plot_name, selected_index)))


def color_projects(geom_type):
    project_colors = {
        'segments': 'gray',
        'Painting, waterproofing or other': 'turquoise',
        'Public lighting': 'khaki',
        'Street planter installation': 'palegreen',
        'Street repair': 'crimson'
    }
    return project_colors[geom_type]


# Load files
try:
    projects = pd.read_csv(PROJECT_DATA, encoding='latin-1')
except FileNotFoundError:
    raise Exception('[ERROR] Project file not found.')

try:
    urban_index = pd.read_csv(URBAN_INDEX)
except FileNotFoundError:
    raise Exception('[ERROR] Urban index file not found.')

# Generate location graph
neighborhood = LOCATIONS[SELECTED_NEIGHBORHOOD]
G = generate_location_graph(neighborhood=neighborhood, simplify=True)
_, edges = ox.graph_to_gdfs(G)

# Map projects standalone
loc_edges = edges[['geometry']].copy()
loc_edges.reset_index(inplace=True)
loc_edges = loc_edges.drop_duplicates(subset=['u', 'v'])
loc_edges['Type'] = 'segments'

projects['geometry'] = projects['processed_locations'].apply(
    lambda x: Point(float(x.split(',')[1]), float(x.split(',')[0])))

gdf_edges = gpd.GeoDataFrame(loc_edges, geometry='geometry')
gdf_projects = gpd.GeoDataFrame(projects, geometry='geometry')

gdf_edges['color'] = gdf_edges.apply(lambda row: color_projects(row['Type']), axis=1)
gdf_projects['color'] = gdf_projects.apply(lambda row: color_projects(row['Type']), axis=1)

cmap = ListedColormap([color_projects(proj_type) for proj_type in gdf_projects['Type'].unique()])

fig, ax = plt.subplots(figsize=(10, 10))
gdf_edges.plot(ax=ax, color=gdf_edges['color'])
gdf_projects.plot(ax=ax, column='Type', categorical=True, legend=True,
                  legend_kwds={'title': 'Project types', 'edgecolor': 'white',
                               'facecolor': 'white',
                               'loc': 'lower center', 'ncol': 2}, cmap='Pastel2')
plt.axis('off')
plt.savefig(os.path.join(OUTPUT_PATH, 'StaticMap_ProjectLocations.png'))

# Remove the projects that are out of scope
projects = projects[~projects['COLONIA'].isin(['Centro III', 'Centro IV'])]

# Map projects and urban indices
plot_index_project_selection(
    edges, urban_index, projects,
    ['Painting, waterproofing or other', 'Public lighting',
     'Street planter installation', 'Street repair'],
    'weighted_sum_absoluteChange', 'all')

plot_index_project_selection(
    edges, urban_index, projects,
    ['Painting, waterproofing or other'],
    'facade_absoluteChange', 'facades')

plot_index_project_selection(
    edges, urban_index, projects,
    ['Street repair'],
    'pothole_absoluteChange', 'potholes')

plot_index_project_selection(
    edges, urban_index, projects,
    ['Painting, waterproofing or other', 'Public lighting',
     'Street planter installation', 'Street repair'],
    'weighted_sum_log_absoluteChange', 'all')

plot_index_project_selection(
    edges, urban_index, projects,
    ['Painting, waterproofing or other'],
    'facade_log_absoluteChange', 'facades')

plot_index_project_selection(
    edges, urban_index, projects,
    ['Street repair'],
    'pothole_log_absoluteChange', 'potholes')
