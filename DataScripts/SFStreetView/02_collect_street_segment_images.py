# 02_collect_street_segment_images.py
#
# Collects the GSV imagery along the street segments of a selected location
# and for a selected time period.
#
# Usage: Add selected location to the LOCATIONS dictionary in locations.py and
# replace the SELECTED_LOCATION parameter in line 38 with the dictionary key.
# Script 01_generate_street_segments.py must already be run on the selected
# location in order to collect the imagery. Modify the TIME_PERIOD parameter in
# line 43 by indicating whether to download the Google default images or the
# images for a selected time period. If you wish to download images for a
# particular time period, modify the PERIOD_SELECTION dictionary. The
# 'optimal_date' key should be a date object (year, month, day) representing the
# optimal timestamp the images should have. The 'min' and 'max' keys represent the
# appropriate time period for the images' timestamp; any locations without
# panoramas for these dates will have missing images.
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

import CONFIG
from utils import get_SV_image, get_SV_metadata, AppendLogger, Logger


# Parameters
SELECTED_LOCATION = 'MissionTenderloinAshburyCastroChinatown'
SEGMENT_DICTIONARY = os.path.join(
    '..', '..', 'Data', 'ProcessedData', 'SFStreetView',
    'segment_dictionary_{}.json'.format(SELECTED_LOCATION))

TIME_PERIOD = ['google_default', 'selected'][1]
PERIOD_SELECTION = {
    'optimal_date': date(2011, 2, 1),
    'min': date(2011, 1, 1),
    'max': date(2011, 12, 31)
}

if TIME_PERIOD == 'google_default':
    OUTPUT_PATH = os.path.join(
        '..', '..', 'Data', 'ProcessedData', 'SFStreetView', 'Res_640',
        SELECTED_LOCATION)
else:
    OUTPUT_PATH = os.path.join(
        '..', '..', 'Data', 'ProcessedData', 'SFStreetView', 'Res_640',
        '{}_{}'.format(
            SELECTED_LOCATION, str(PERIOD_SELECTION['optimal_date'])))

IMG_PARAMS = {
    'size': '640x640',
    'key': CONFIG.SV_api_key,
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


# Load street segment information
try:
    print('[INFO] Loading segment dictionary for {}'.format(SELECTED_LOCATION))
    with open(SEGMENT_DICTIONARY, 'r') as segment_file:
        segment_dictionary = json.load(segment_file)
except FileNotFoundError:
    raise Exception('[ERROR] Segment dictionary not found.')

# Check output directory and create logger
if not os.path.exists(OUTPUT_PATH):
    print('[INFO] Creating output path: {}'.format(OUTPUT_PATH))
    os.makedirs(OUTPUT_PATH)
logger = AppendLogger(os.path.join(OUTPUT_PATH, 'images.txt'))

# Record image dates
if TIME_PERIOD == 'selected':
    date_logger = Logger(os.path.join(OUTPUT_PATH, 'image_dates.txt'))
    date_logger.write(
        'Optimal date: {}\n Minimum date: {} \n Maximum date: {}'.format(
            PERIOD_SELECTION['optimal_date'], PERIOD_SELECTION['min'],
            PERIOD_SELECTION['max']))

# Identify remaining street segments to collect
if not os.path.exists(os.path.join(OUTPUT_PATH, 'images.txt')):
    start_key = 0
else:
    with open(os.path.join(OUTPUT_PATH, 'images.txt')) as file:
        images_file = file.readlines()
    collected_keys = [line.split(' ')[0] for line in images_file]
    collected_keys = set(collected_keys)
    start_key = len(collected_keys) - 1

# Save images for each street segment
print('[INFO] Saving images for {} street segments.'.format(
    len(segment_dictionary) - start_key))
main_counter = 0
image_unavailable_counter = 0
heading_unavailable_counter = 0

for key in tqdm(range(start_key, len(segment_dictionary))):
    segment = segment_dictionary[str(key)]

    # Hash segment ID
    segment_id = json.loads(segment['segment_id'])
    segment_id = '{}-{}'.format(segment_id[0], segment_id[1])

    # Check segment coordinates
    if len(segment['coordinates']) == 0:
        print('[WARNING] No coordinates for segment {}: {}'.format(
            key, segment['name']))

    # Get images for each coordinate and heading
    location_counter = 0
    panorama_dict = {}

    # These will be used in case a node has no heading information
    previous_headings = None, None

    # Drop segments with unavailable headings at first node
    if segment['coordinates'][0][1] is None or segment['coordinates'][0][2] is None:
        heading_unavailable_counter += 1
        image_log = '{} UnavailableFirstHeading NA NA'.format(segment_id)
        logger.write(image_log)
        continue

    for i, ((lat, lng), heading1, heading2) in enumerate(segment['coordinates']):
        img_params = IMG_PARAMS.copy()

        # Get the panorama belonging to a location-time combination
        if TIME_PERIOD == 'selected':
            image_metadata = return_optimal_panoid(lat, lng)
            image_date = image_metadata['date']
        elif TIME_PERIOD == 'google_default':
            img_params['location'] = '{},{}'.format(lat, lng)
            image_metadata = get_SV_metadata(params=img_params)
            image_date = date(int(image_metadata['date'].split('-')[0]),
                              int(image_metadata['date'].split('-')[1]), 1)
        else:
            raise Exception('[ERROR] TIME_PERIOD should be one of '
                            '[selected, google_default]')
        image_panoid = image_metadata['pano_id']

        # Get the image for each heading from this panorama
        for heading_num, heading in enumerate([heading1, heading2]):
            # Check if heading is None
            if heading is None:
                heading = previous_headings[heading_num]
            img_params['heading'] = heading

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
                if TIME_PERIOD == 'selected':
                    img_params['pano'] = image_panoid
                image = get_SV_image(params=img_params)
                file_name = 'img_{}_h{}_{}.png'.format(
                    segment_id, heading_num, str(location_counter).zfill(3))
                image.save(os.path.join(OUTPUT_PATH, file_name))

                # Increase counters
                location_counter += 1
                main_counter += 1

                image_log = '{} {} {} {}'.format(
                    segment_id, file_name, image_panoid, image_date)
            else:
                image_log = '{} NotSaved {} {}'.format(
                    segment_id, image_panoid, image_date)

            # Log image metadata
            logger.write(image_log)

        # Update headings
        previous_headings = heading1, heading2

print('[INFO] Image collection complete.'
      ' Loaded {} images for {} street segments. '
      ' Encountered {} unavailable images.'
      ' Encountered {} segments with unavailable first node heading'.format(
      main_counter, len(segment_dictionary), image_unavailable_counter,
      heading_unavailable_counter))
