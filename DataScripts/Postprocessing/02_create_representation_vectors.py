# 02_create_representation_vectors.py
# Computes a vector representation of each street segment.
#
# Usage: Run the following command in terminal (modified to your neighborhood of choice)
#   python 02_create_representation_vectors.py
#   -v Outputs/Detection/Res_640/MissionDistrictBlock_2011-02-01_3/
#   -s 640
#   -d Data/ProcessedData/SFStreetView/segment_dictionary_MissionDistrict.json
#   -i Data/ProcessedData/SFStreetView/Res_640/MissionDistrictBlock_2011-02-01_3/
#   -m mark_missing
#   -c 50
#
# Data inputs:
#   - CSV file including one row per detected object instance (generated
#     using 01_detect_segments.py on the selected neighborhoods)
#   - Segment dictionary for the selected neighborhood
#   - Image log for the selected neighborhood generated during the image
#   collection process
#
# Outputs:
#   - CSV file including a representation of each street segment (exported to
#     the same directory as the input file) for each aggregation type


import argparse
import json
import numpy as np
import os
import pandas as pd
from tqdm import tqdm

from DataScripts.object_classes import CLASSES_TO_LABEL
from DataScripts.read_files import prep_image_log, prep_object_vectors
from DataScripts.read_files import load_segment_dict
from DataScripts.urbanchange_utils import AppendLogger

from DataScripts.vector_aggregations import MISSING_IMAGE_NORMALIZATION
from DataScripts.vector_aggregations import AGGREGATIONS


# Set up command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-v', '--object_vectors_dir', required=True,
                    help='Input directory for object vectors '
                         'produced by 01_detect_segments.py')
parser.add_argument('-s', '--image_size', required=True, default=640, type=int,
                    help='Image resolution')
parser.add_argument('-d', '--segment_dictionary', required=True,
                    help='Path to segment dictionary for the location')
parser.add_argument('-i', '--images_dir', required=True,
                    help='Path to the directory containing images.txt')
parser.add_argument('-m', '--missing_image', required=True,
                    choices=MISSING_IMAGE_NORMALIZATION,
                    help='Choice of missing image normalization')
parser.add_argument('-c', '--confidence_level', required=True, type=int,
                    help='Minimum confidence level to filter '
                         'detections (in percent)')

if __name__ == '__main__':
    # Capture command line arguments
    args = vars(parser.parse_args())
    object_vectors_dir = args['object_vectors_dir']
    image_size = args['image_size']
    segment_dict_file = args['segment_dictionary']
    images_dir = args['images_dir']
    missing_image_normalization = args['missing_image']
    min_confidence_level = args['confidence_level']

    # Load files
    print('[INFO] Loading segment dictionary, object vectors and image log.')
    object_vectors = prep_object_vectors(object_vectors_dir)
    segment_dictionary = load_segment_dict(segment_dict_file)
    image_log = prep_image_log(images_dir)

    # Get selected location-time and verify the three files match
    location_time = object_vectors_dir.split(os.path.sep)[-1]
    location = location_time.split('_')[0]
    segment_dict_location = \
        segment_dict_file.split(os.path.sep)[-1].split('.')[0].split('_')[-1]
    images_location_time = images_dir.split(os.path.sep)[-1]

    if not (location == segment_dict_location and location_time == images_location_time):
        raise Exception(
            '[ERROR] Input files point to different location-time '
            'selections: {}, {}, {}, {}'.format(
                location, segment_dict_location, location_time,
                images_location_time))
    print('[INFO] Creating representation vectors for {}'.format(location_time))

    # Set up aggregation files
    aggregation_files = {}
    for aggregation in AGGREGATIONS.keys():
        aggregation_files[aggregation] = AppendLogger(
            os.path.join(object_vectors_dir, '{}_{}_{}.txt'.format(
                aggregation, missing_image_normalization,
                str(min_confidence_level))))

    # Aggregate vectors
    print('[INFO] Computing segment vector representations.')

    # Recognize past progress
    last_modified_file = os.path.join(
        object_vectors_dir, 'ConfxBbox_weighted_{}_{}.txt'.format(
            missing_image_normalization, str(min_confidence_level)))
    if os.path.exists(last_modified_file):
        with open(last_modified_file, 'r') as file:
            processed_segments = file.readlines()
        processed_segments = [list(json.loads(segment).keys())[0] for segment in processed_segments]
        key_start = len(set(processed_segments)) - 1
    else:
        key_start = 0

    print('[INFO] Creating vectors for {} street segments.'.format(
        len(segment_dictionary) - key_start))
    for key in tqdm(range(key_start, len(segment_dictionary))):
        segment = segment_dictionary[str(key)]

        # Hash segment ID
        segment_id = json.loads(segment['segment_id'])
        segment_id = '{}-{}'.format(segment_id[0], segment_id[1])

        # Get segment length to normalize vectors
        segment_length = float(segment['length'])

        segment_df = \
            object_vectors[object_vectors['segment_id'] == segment_id].copy()

        # Get record of images for the segment to compute missing images.
        # Note: Missing images are recorded as {segment_id} {NotSaved} {None}
        # {None} in script 02_collect_street_segment_images.py. We can skip the
        # case of {segment_id} {UnavailableFirstHeading} {None} {None} and the
        # case of {segment_id} {UnavailableCoordinates} {None} {None} as they'll
        # be handled automatically in the 'segments with zero images' case below.
        segment_log = image_log[image_log['segment_id'] == segment_id].copy()
        segment_missing_images = segment_log[
            (segment_log['img_id'] == 'NotSaved') &
            (segment_log['panoid'].isnull()) & (segment_log['img_date'].isnull())]
        segment_missing_images = len(segment_missing_images)

        # Get number of captured images for the segment
        segment_captured_imgs = segment_log[
            ~segment_log['img_id'].isin(['NotSaved', 'UnavailableFirstHeading',
                                         'UnavailableCoordinates'])].copy()
        segment_captured_imgs = len(segment_captured_imgs)

        for aggregation in AGGREGATIONS.keys():
            # Compute aggregation and save to file
            agg_function = AGGREGATIONS[aggregation]

            # Handle segments with zero images (this type of row is generated in
            # 01_detect_segments.py line 152) and images with at least one
            # missing image if this is the selected missing_image normalization.
            if (segment_df['img_id'].iloc[0] is np.nan) or (
                    missing_image_normalization == 'mark_missing' and segment_missing_images > 0):
                segment_aggregation = {}
                for object_class in CLASSES_TO_LABEL.keys():
                    segment_aggregation[object_class] = None
            else:
                # Filter for minimum confidence level
                segment_df_filtered = segment_df[
                    segment_df['confidence'] >= min_confidence_level / 100].copy()

                segment_aggregation = agg_function(
                    df=segment_df_filtered, img_size=image_size,
                    length=segment_length,
                    num_missing_images=segment_missing_images,
                    num_captured_images=segment_captured_imgs,
                    missing_img_normalization=missing_image_normalization)

            # Tag with the segment ID
            segment_aggregation = {segment_id: segment_aggregation}
            row_str = json.dumps(segment_aggregation)

            # Save to file
            agg_logger = aggregation_files[aggregation]
            agg_logger.write(row_str)

    # Save temporary files as DataFrames
    print('[INFO] Segment representations generated. Exporting temporary files'
          ' to DataFrames.')
    for aggregation in AGGREGATIONS.keys():
        # Get temporary and CSV files for the aggregation
        agg_temporary_file = os.path.join(
            object_vectors_dir, '{}_{}_{}.txt'.format(
                aggregation, missing_image_normalization, str(min_confidence_level)))
        agg_new_file = os.path.join(object_vectors_dir, '{}_{}_{}.csv'.format(
            aggregation, missing_image_normalization, str(min_confidence_level)))

        # Check number of processed segments
        with open(agg_temporary_file, 'r') as file:
            vector_representations = file.readlines()
        processed_segments = [
            list(json.loads(segment).keys())[0] for segment in vector_representations]
        number_of_processed_segments = len(set(processed_segments))

        # Export if all segments have been processed
        if number_of_processed_segments == len(segment_dictionary):
            # Create base DataFrame
            df_cols = {'segment_id': []}
            for object_class in CLASSES_TO_LABEL.keys():
                df_cols[object_class] = []
            segment_representations = pd.DataFrame(df_cols)

            # Loop over each segment
            for segment in vector_representations:
                segment_dict = json.loads(segment)
                segment_id = list(segment_dict.keys())[0]
                new_segment_dict = {'segment_id': segment_id}
                for key, item in segment_dict[segment_id].items():
                    new_segment_dict[key] = item

                segment_representations = segment_representations.append(
                    new_segment_dict, ignore_index=True)

            # Save CSV
            segment_representations.to_csv(agg_new_file, index=False)

            # Delete temporary file
            os.remove(agg_temporary_file)

        else:
            raise Exception('[ERROR] Incomplete street segments representations'
                            ' temporary file.')
