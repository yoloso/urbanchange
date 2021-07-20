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

# For GSV secret encoding
import hashlib
import hmac
import base64
import urllib.parse as urlparse


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


# Generating GSV images ----------------------------------
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


# The following function was derived from the Google Street View API
# https://developers.google.com/maps/documentation/streetview/get-api-key#server-side-signing
def sign_url(input_url=None, secret=None):
    """ Sign a request URL with a URL signing secret.
      Usage:
      from urlsigner import sign_url
      signed_url = sign_url(input_url=my_url, secret=SECRET)
      Args:
      input_url - The URL to sign
      secret    - Your URL signing secret
      Returns:
      The signed request URL
  """

    if not input_url or not secret:
        raise Exception("Both input_url and secret are required")

    url = urlparse.urlparse(input_url)

    # We only need to sign the path+query part of the string
    url_to_sign = url.path + "?" + url.query

    # Decode the private key into its binary format
    # We need to decode the URL-encoded private key
    decoded_key = base64.urlsafe_b64decode(secret)

    # Create a signature using the private key and the URL-encoded
    # string using HMAC SHA1. This signature will be binary.
    signature = hmac.new(decoded_key, str.encode(url_to_sign), hashlib.sha1)

    # Encode the binary signature into base64 for use within a URL
    encoded_signature = base64.urlsafe_b64encode(signature.digest())

    original_url = url.scheme + "://" + url.netloc + url.path + "?" + url.query

    # Return signed URL
    return original_url + "&signature=" + encoded_signature.decode()


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


# Processing images and annotations -----------------------
def get_image_name(image_path):
    image_name = image_path.split(os.path.sep)[-1]
    image_name = '.'.join(image_name.split('.')[:-1])
    return image_name


def load_annotations(annotation_path):
    with open(annotation_path, 'r') as file:
        box_list = file.readlines()
    return box_list


def preprocess_box_list(box_list):
    num_objects = len(box_list)
    boxes = []

    for box in box_list:
        pass
    # TODO
    return num_objects, labels, XXX
