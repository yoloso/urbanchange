# Functions to read in segment dictionaries, object detections, image log files
# and other.

import json
import os
import pandas as pd


# Segment dictionary
def load_segment_dict(segment_dictionary_file):
    try:
        print('[INFO] Loading segment dictionary.')
        with open(segment_dictionary_file, 'r') as seg_file:
            segment_dictionary = json.load(seg_file)
    except FileNotFoundError:
        raise Exception('[ERROR] Segment file dictionary not found.')

    return segment_dictionary


# Object vectors from detections.csv
def prep_object_vectors(obj_vectors_dir):
    print('[INFO] Loading object detection vectors.')
    try:
        with open(os.path.join(obj_vectors_dir, 'detections.csv'), 'r') as file:
            object_vectors = pd.read_csv(
                file, dtype={'segment_id': object, 'img_id': object,
                             'object_id': object, 'confidence': float,
                             'bbox_size': float, 'class': object},
                na_values=['None'])
    except FileNotFoundError:
        raise Exception('[ERROR] Object vectors file not found.')

    # Drop duplicate objects (this may be driven by the 01_detect_segments.py
    # process stopping and restarting)
    object_vectors.drop_duplicates(
        subset=['segment_id', 'img_id', 'object_id'], inplace=True)

    return object_vectors


# Image log from images.txt
def prep_image_log(images_dir):
    print('[INFO] Loading image log.')
    try:
        with open(os.path.join(images_dir, 'images.txt'), 'r') as file:
            image_log = pd.read_csv(
                file, sep=' ', header=0,
                names=['segment_id', 'img_id', 'panoid', 'img_date', 'query_id',
                       'pano_lat', 'pano_lng', 'END'],
                na_values=['None'])
    except FileNotFoundError:
        raise Exception('[ERROR] images.txt file not found.')

    # Remove duplicate lines in images log (driven by interrupting the image
    # collection process)
    image_log = image_log.drop_duplicates(subset=['segment_id', 'query_id'])

    return image_log


def prep_object_vectors_with_dates(obj_vectors_dir, images_dir):
    object_vectors = prep_object_vectors(obj_vectors_dir)
    image_log = prep_image_log(images_dir)

    # Get image dates
    image_dates = image_log.copy()
    image_dates['image_name'] = image_dates['img_id'].apply(
        lambda x: '_'.join(x.split('_')[2:4]).split('.')[0] if 'img' in x else None)
    image_dates = image_dates[[
        'segment_id', 'image_name', 'img_date', 'pano_lat', 'pano_lng']]
    image_dates = image_dates[image_dates['image_name'].notnull()]

    # Merge
    object_vectors = object_vectors.merge(
        image_dates, how='left', left_on=['segment_id', 'img_id'],
        right_on=['segment_id', 'image_name'], validate='many_to_one')

    return object_vectors
