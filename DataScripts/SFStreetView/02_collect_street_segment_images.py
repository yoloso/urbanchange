# 02_collect_street_segment_images.py
#
# Collects the GSV imagery along the street segments of a selected location
# and for a selected time period.
#
# Usage: Add selected location to the LOCATIONS dictionary in locations.py and
# replace the SELECTED_LOCATION parameter in with the dictionary key.
# Script 01_generate_street_segments.py must already be run on the selected
# location in order to collect the imagery. Modify the TIME_PERIOD parameter
# by indicating whether to download the Google default images, a single panorama
# per location ('selected'), or all panoramas available for a location during
# a specified time period ('full'). If you wish to download images for a
# particular time period ('selected' or 'full'), modify the PERIOD_SELECTION
# dictionary. The 'optimal_date' key should be a date object (year, month, day)
# representing the # optimal timestamp the images should have if TIME_PERIOD is
# equal to 'selected'. The 'min' and 'max' keys represent the
# appropriate time period for the images' timestamp; any locations without
# panoramas for these dates will have missing images.
# If you wish to only download imagery for specific segments, you can use the
# images.txt file of another image collection run. This will download imagery
# only for segments with available imagery in the other run.
#
# Inputs:
#       - LOCATIONS dictionary including a dictionary for the selected location.
#       - JSON dictionary containing the street segments for the selected
#         location at SEGMENT_DICTIONARY
# Outputs:
#       - GSV Images for the selected time period and location at OUTPUT_PATH
#       - TXT file recording the image retrieval process at each coordinate.


from datetime import date, timedelta
import json
import os
import streetview
from tqdm import tqdm

import DataScripts.CONFIG as CONFIG
from DataScripts.urbanchange_utils import get_SV_image, get_SV_metadata
from DataScripts.urbanchange_utils import AppendLogger, Logger
from DataScripts.read_files import load_segment_dict, prep_image_log


# Parameters
SELECTED_LOCATION = 'MissionDistrictBlock'
SEGMENT_DICTIONARY = os.path.join(
    '..', '..', 'Data', 'ProcessedData', 'SFStreetView',
    'segment_dictionary_{}.json'.format(SELECTED_LOCATION))

TIME_PERIOD = ['google_default', 'selected', 'full'][1]
PERIOD_SELECTION = {
    'optimal_date': date(2014, 2, 1),
    'min': date(2014, 1, 1),
    'max': date(2014, 12, 31)
}
SEGMENT_RESTRICTION = None

# Set up image parameters and output directory
if TIME_PERIOD == 'google_default':
    OUTPUT_PATH = os.path.join(
        '..', '..', 'Data', 'ProcessedData', 'SFStreetView', 'Res_640',
        SELECTED_LOCATION)
elif TIME_PERIOD == 'selected':
    OUTPUT_PATH = os.path.join(
        '..', '..', 'Data', 'ProcessedData', 'SFStreetView', 'Res_640',
        '{}_{}'.format(
            SELECTED_LOCATION, str(PERIOD_SELECTION['optimal_date'])))
elif TIME_PERIOD == 'full':
    OUTPUT_PATH = os.path.join(
        '..', '..', 'Data', 'ProcessedData', 'SFStreetView', 'Res_640',
        '{}_full_{}_{}'.format(
            SELECTED_LOCATION, str(PERIOD_SELECTION['min'].year),
            str(PERIOD_SELECTION['max'].year)))
else:
    raise Exception('[INFO] TIME_PERIOD should be one of '
                    '[google_default, selected, full]')

IMG_PARAMS = {
    'size': '640x640',
    'key': CONFIG.SV_api_key,
    'source': 'outdoor'
}


# Helper functions
def return_optimal_panoid(lat, lng):
    """
    Returns the panorama ID for a given location with the timestamp closest
    to the optimum date as specified in the PERIOD_SELECTION dict, if it falls
    within the specified minimum and maximum dates.
    :param lat: (float)
    :param lng: (float)
    :return: (dict) including the panorama ID and its timestamp, if available.
    """
    panoid_list = streetview.panoids(lat, lng)
    optimal_panoid = {'pano_id': None, 'date': None}
    current_optimum = timedelta(days=365 * 50)

    # Check availability for selected years
    for panoid in panoid_list:
        if 'year' in panoid.keys():
            pano_date = date(panoid['year'], panoid['month'], 1)
            if PERIOD_SELECTION['max'] >= pano_date >= PERIOD_SELECTION['min']:
                if abs(pano_date - PERIOD_SELECTION['optimal_date']) < current_optimum:
                    current_optimum = abs(pano_date - PERIOD_SELECTION['optimal_date'])
                    optimal_panoid['pano_id'] = panoid['panoid']
                    optimal_panoid['date'] = pano_date

    return optimal_panoid


def return_period_panoids(lat, lng):
    """
    Returns the panorama IDs for a given location with the timestamps falling
    within the specified minimum and maximum dates of the PERIOD_SELECTION dict.
    :param lat: (float)
    :param lng: (float)
    :return: (list) including the panorama IDs and timestamps, if available.
    """
    panoid_list = streetview.panoids(lat, lng)
    period_panoid_list = []

    # Check availability for selected years
    for panoid in panoid_list:
        if 'year' in panoid.keys():
            pano_date = date(panoid['year'], panoid['month'], 1)
            if PERIOD_SELECTION['max'] >= pano_date >= PERIOD_SELECTION['min']:
                period_panoid_list.append(
                    {'pano_id': panoid['panoid'], 'date': pano_date})

    return period_panoid_list


PANOID_RETURN_DICT = {'selected': return_optimal_panoid,
                      'full': return_period_panoids}

# Load street segment information
segment_dictionary = load_segment_dict(SEGMENT_DICTIONARY)

# Check output directory and create logger
if not os.path.exists(OUTPUT_PATH):
    print('[INFO] Creating output path: {}'.format(OUTPUT_PATH))
    os.makedirs(OUTPUT_PATH)
logger = AppendLogger(os.path.join(OUTPUT_PATH, 'images.txt'))

# Record image dates
if TIME_PERIOD == 'selected':
    date_logger = Logger(os.path.join(OUTPUT_PATH, 'image_dates.txt'))
    date_logger.write(
        'Loading one panorama per location.\n'
        'Optimal date: {}\nMinimum date: {} \nMaximum date: {}'.format(
            PERIOD_SELECTION['optimal_date'], PERIOD_SELECTION['min'],
            PERIOD_SELECTION['max']))
    print('[INFO] Saving one panorama per location.')
elif TIME_PERIOD == 'full':
    date_logger = Logger(os.path.join(OUTPUT_PATH, 'image_dates.txt'))
    date_logger.write(
        'Loading all available panoramas per location.\n'
        'Minimum date: {} \nMaximum date: {}'.format(
            PERIOD_SELECTION['min'], PERIOD_SELECTION['max']))
    print('[INFO] Saving all available panoramas per location.')

# Determine restricted segments. These are segments that are 'out of bounds'
# and for which we will not collect imagery.
restricted_segments = []
if SEGMENT_RESTRICTION is not None:
    print('[INFO] Determining unrestricted segments based on '
          'SEGMENT_RESTRICTION file')
    restricted_segment_image_log = prep_image_log(SEGMENT_RESTRICTION)
    restricted_segment_image_log = restricted_segment_image_log[
        restricted_segment_image_log['img_id'] != 'NotSaved']
    unrestricted_segments = set(restricted_segment_image_log['segment_id'].unique())

    for key, segment in tqdm(segment_dictionary.items()):
        # Hash segment ID
        segment_id = json.loads(segment['segment_id'])
        segment_id = '{}-{}'.format(segment_id[0], segment_id[1])

        if segment_id not in unrestricted_segments:
            restricted_segments.append(segment_id)

    print('[INFO] Dropped {} segments based on specified restriction.'.format(
        len(restricted_segments)))

# Start key and counters
start_key = 0
main_counter, image_unavailable_counter = 0, 0
heading_unavailable_counter, coordinate_unavailable_counter = 0, 0

# Identify remaining street segments to collect
if os.path.exists(os.path.join(OUTPUT_PATH, 'images.txt')):
    print('[INFO] Identifying past image collection progress.')
    with open(os.path.join(OUTPUT_PATH, 'images.txt')) as file:
        images_file = file.readlines()
    collected_keys = [line.split(' ')[0] for line in images_file]
    collected_keys = set(collected_keys)
    start_key = len(collected_keys) - 1

    # Reset counters
    for log in tqdm(images_file):
        try:
            img_id, panoid = log.split(' ')[1], log.split(' ')[2]
            if img_id == 'UnavailableCoordinates':
                coordinate_unavailable_counter += 1
            elif img_id == 'UnavailableFirstHeading':
                heading_unavailable_counter += 1
            elif img_id == 'NotSaved' and panoid == 'None':
                image_unavailable_counter += 1
            elif img_id != 'NotSaved':
                main_counter += 1
        except IndexError:  # This indicates a blank line
            continue

# Save images for each street segment
print('[INFO] Saving images for {} street segments.'.format(
    len(segment_dictionary) - start_key))

for key in tqdm(range(start_key, len(segment_dictionary))):
    segment = segment_dictionary[str(key)]

    # Hash segment ID
    segment_id = json.loads(segment['segment_id'])
    segment_id = '{}-{}'.format(segment_id[0], segment_id[1])

    # Skip segment if segment is restricted
    if segment_id in restricted_segments:
        print('[INFO] Restricted segment {}: {}'.format(key, segment['name']))
        continue

    # Check segment coordinates
    if len(segment['coordinates']) == 0:
        print('[WARNING] No coordinates for segment {}: {}'.format(
            key, segment['name']))
        coordinate_unavailable_counter += 1
        image_log = '{} UnavailableCoordinates NA NA NA NA NA END'.format(segment_id)
        logger.write(image_log)
        continue

    # Get images for each coordinate and heading
    location_counter, query_counter = 0, 0
    panorama_dict = {}

    # These will be used in case a node has no heading information
    previous_headings = None, None

    # Drop segments with unavailable headings at first node
    if segment['coordinates'][0][1] is None or segment['coordinates'][0][2] is None:
        heading_unavailable_counter += 1
        image_log = '{} UnavailableFirstHeading NA NA NA NA NA END'.format(segment_id)
        logger.write(image_log)
        continue

    for i, ((lat, lng), heading1, heading2) in enumerate(segment['coordinates']):
        # Create a for list of panoramas to be processed. It will be of length 1
        # if TIME_PERIOD is not 'full')
        panos_to_process = []
        if TIME_PERIOD in ['selected', 'full']:
            time_panos = PANOID_RETURN_DICT[TIME_PERIOD](lat, lng)
            if isinstance(time_panos, dict):
                time_panos = [time_panos]

            for time_pano in time_panos:
                img_params = IMG_PARAMS.copy()
                img_params['pano'] = time_pano['pano_id']
                panos_to_process.append(img_params)

        elif TIME_PERIOD == 'google_default':
            img_params = IMG_PARAMS.copy()
            img_params['location'] = '{},{}'.format(lat, lng)
            panos_to_process.append(img_params)
        else:
            raise Exception('[ERROR] TIME_PERIOD should be one of '
                            '[google_default, selected, full]')

        for pano_params in panos_to_process:
            image_metadata = get_SV_metadata(params=pano_params)

            # Get image date, panoid and coordinates if imagery is available
            if image_metadata['status'] != 'OK':
                image_panoid, image_date, image_lat, image_lng = None, None, None, None
            else:
                image_date = date(int(image_metadata['date'].split('-')[0]),
                                  int(image_metadata['date'].split('-')[1]), 1)
                image_panoid = image_metadata['pano_id']
                image_lat = image_metadata['location']['lat']
                image_lng = image_metadata['location']['lng']

            # Get the image for each heading from this panorama
            for heading_num, heading in enumerate([heading1, heading2]):
                # Check if heading is None
                if heading is None:
                    heading = previous_headings[heading_num]
                pano_params['heading'] = heading

                # Missing imagery for the selected time-location
                save = True
                if image_panoid is None:
                    save = False
                    image_unavailable_counter += 1
                else:
                    # Check if the image's view of the location is unique by comparing
                    # to previously queried headings
                    if image_panoid in panorama_dict.keys():
                        # Check queried headings
                        for queried_heading in panorama_dict[image_panoid]:
                            if abs(queried_heading - heading) < 50:
                                save = False
                        # Add current heading if unique
                        if save:
                            panorama_dict[image_panoid].append(heading)
                    else:
                        panorama_dict[image_panoid] = [heading]

                # Save if available and unique
                if save:
                    image = get_SV_image(params=pano_params)
                    file_name = 'img_{}_h{}_{}.png'.format(
                        segment_id, heading_num, str(location_counter).zfill(3))
                    image.save(os.path.join(OUTPUT_PATH, file_name))

                    # Increase counters
                    location_counter += 1
                    main_counter += 1

                    image_log = '{} {} {} {} {} {} {} END'.format(
                        segment_id, file_name, image_panoid, image_date,
                        query_counter, image_lat, image_lng)
                else:
                    image_log = '{} NotSaved {} {} {} {} {} END'.format(
                        segment_id, image_panoid, image_date, query_counter,
                        image_lat, image_lng)

                # Log image metadata
                logger.write(image_log)
                query_counter += 1

        # Update headings if not None
        if heading1 is not None and heading2 is not None:
            previous_headings = heading1, heading2

print('[INFO] Image collection complete. '
      'Loaded {} images for {} street segments.\n'
      '[INFO] Encountered {} unavailable images.\n'
      '[INFO] Encountered {} segments with unavailable coordinates.\n'
      '[INFO] Encountered {} segments with unavailable first node heading'.format(
        main_counter, len(segment_dictionary), image_unavailable_counter,
        coordinate_unavailable_counter, heading_unavailable_counter))
