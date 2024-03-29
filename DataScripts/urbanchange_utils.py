from datetime import date
from io import BytesIO
import json
import math
import numpy as np
import os
import osmnx as ox
import pandas as pd
from PIL import Image
import requests


# Geocoding street segments --------------------------------
def compute_heading(bearing):
    """
    Computes a tuple of headings to be used in the 'heading' parameter of the
    Google Street View API such that the images for a given street segment
    face its buildings at a 90 degree angle.
    :param bearing: The street segment's orientation
    :return: (tuple)
    """
    if pd.isna(bearing):
        return None, None
    elif 90 >= bearing >= 0:
        return [bearing + 90, bearing + 270]
    elif bearing <= 270:
        return [bearing + 90, bearing - 90]
    elif bearing <= 360:
        return [bearing - 90, bearing - 270]
    else:
        raise Exception('[ERROR] Bearing should be between 0 and 360.')


def generate_new_latlng_from_distance(cur_lat,
                                      cur_lng,
                                      segment_bearing,
                                      distance, radius):
    """

    :param radius: (float) radius of the Earth
    :param distance: (float) Distance in km between the two coordinates
    :param segment_bearing: (float) Bearing in degrees
    :param cur_lat: (float) Starting latitude in degrees
    :param cur_lng: (float) Starting longitude in degrees
    :return: (tuple of float) Ending latitude, longitude coordinates at a
    selected distance and bearing from the starting coordinates
    """
    # Convert to radians
    cur_lat, cur_lng = math.radians(cur_lat), math.radians(cur_lng)
    bearing_rad = math.radians(segment_bearing)

    # Compute new coordinates
    new_lat = math.sin(cur_lat) * math.cos(distance / radius) + \
              math.cos(cur_lat) * math.sin(distance / radius) * math.cos(bearing_rad)
    new_lat = math.asin(new_lat)

    new_lng = math.atan2(
        math.sin(bearing_rad) * math.sin(distance / radius) * math.cos(cur_lat),
        math.cos(distance / radius) - math.sin(cur_lat) * math.sin(new_lat))
    new_lng = cur_lng + new_lng

    # Convert back to degrees and append to coordinate list
    new_lat, new_lng = math.degrees(new_lat), math.degrees(new_lng)

    return new_lat, new_lng


# Google APIs ----------------------------------
def save_SV_image(params, output_dir, file_name):
    """
    Saves the Google Street View image for a particular location as specified
    by the params dictionary to the chosen output directory.
    :param params: (dict)
    :param output_dir: (str)
    :param file_name: (str)
    :return: Null (saves image to file)
    """
    # Request and get image
    img_base_url = 'https://maps.googleapis.com/maps/api/streetview?'
    img_request = requests.get(img_base_url, params)
    img = Image.open(BytesIO(img_request.content))

    # Save image
    output_file = os.path.join(output_dir, '{}.png'.format(file_name))
    img.save(output_file)


def get_SV_image(params):
    """
    Returns the Google Street View image for a particular location as specified
    by the params dictionary.
    :param params: (dict)
    :return: PIL.Image
    """
    # Request and get image
    img_base_url = 'https://maps.googleapis.com/maps/api/streetview?'
    img_request = requests.get(img_base_url, params)
    img = Image.open(BytesIO(img_request.content))
    return img


def get_SV_metadata(params):
    """
    Returns the Google Street View metadata for an image at a particular
    location specified by the params dictionary.
    Note: the metadata endpoint incurs no charges
    :param params: (dict)
    :return: (dict)
    """
    meta_base_url = 'https://maps.googleapis.com/maps/api/streetview/metadata?parameters'
    meta_request = requests.get(meta_base_url, params)
    content = json.loads(meta_request.content)
    return content


def reverse_geocode(params):
    """
    Generate a list of addresses for a given (lat, lon) coordinate pair.
    :param params: (dict) a dictionary including the API key and latlng
    coordinates for which to generate the addresses
    :return: (dict) a dictionary including the information generated by
    the request to the Geocode API for the location.
    """
    geo_base_url = 'https://maps.googleapis.com/maps/api/geocode/json?'
    return requests.get(geo_base_url, params).json()


def geocode(params):
    """
    Converts an address into a (lat, lng) coordinate pair.
    :param params: (dict) a dictionary including the API key and the address
    :return:  (dict) a dictionary including the information generated by the
    request to the Geocode API for the address.
    """
    geo_base_url = 'https://maps.googleapis.com/maps/api/geocode/json?'
    return requests.get(geo_base_url, params)


# Street network graphs ----------------------------------
def generate_location_graph(neighborhood, simplify):
    """
    Generates a networkx.MultiDiGraph of a location's street network.
    :param neighborhood: (dict)
    :param simplify: (bool) whether the street network should be simplified
    (e.g. to include nodes along a curved street)
    :return: (networkx.MultiDiGraph)
    """
    if neighborhood['type'] == 'box':
        graph = ox.graph_from_bbox(
            neighborhood['location'][0][0], neighborhood['location'][1][0],
            neighborhood['location'][0][1], neighborhood['location'][1][1],
            network_type='drive', simplify=simplify)
        return graph
    elif neighborhood['type'] == 'place':
        graph = ox.graph_from_place(
            neighborhood['name'], network_type='drive', simplify=simplify)
        return graph
    else:
        raise Exception('[ERROR] Location type must be one of [box, place]')


# Urban index plotting
def generate_urbanindex_gdf(edges, indices):
    """
    Generates a GeoDataFrame for an urban index.
    :param edges: pd.DataFrame resulting from calling ox.graph_to_gdfs on the
    location's graph.
    :param indices: pd.DataFrame generated from reading in an urban index CSV;
    contains an 'index' column which is the specific index to plot.
    :return: (GeoDataFrame)
    """
    # Process edges
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

    return complete


# Logger -------------------------------------------------
class Logger:
    def __init__(self, path):
        """
        Instantiates the logger as a .txt file at the specified path
        :param path: (str) path to model outputs
        """
        self.path = path

        with open(self.path, 'w') as file:
            file.write('')

    def write(self, text):
        """
        Writes text to logger.
        :param text: (str)
        :return: void
        """
        with open(self.path, 'a+') as file:
            file.write(text + '\n')


class AppendLogger:
    def __init__(self, path):
        """
        Instantiates the logger as a .txt file at the specified path
        :param path: (str) path to model outputs
        """
        self.path = path

    def write(self, text):
        """
        Writes text to logger.
        :param text: (str)
        :return: void
        """
        with open(self.path, 'a+') as file:
            file.write(text + '\n')


# Processing images -------------------------
def get_image_name(image_path):
    image_name = image_path.split(os.path.sep)[-1]
    image_name = '.'.join(image_name.split('.')[:-1])
    return image_name
