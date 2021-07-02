import math
import os


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

    return num_objects, labels, XXX


# Geocoding street segments
def compute_heading(bearing):
    """
    Computes a tuple of headings to be used in the 'heading' parameter of the
    Google Street View API such that the images for a given street segment
    face its buildings at a 90 degree angle.
    :param bearing: The street segment's orientation
    :return: (tuple)
    """
    if 90 >= bearing >= 0:
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
