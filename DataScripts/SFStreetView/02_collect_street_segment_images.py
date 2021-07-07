import json
import os
from tqdm import tqdm

import CONFIG
from utils import get_SV_image, get_SV_metadata


# Parameters
SELECTED_LOCATION = 'GoldenGateHeights'
SEGMENT_DICTIONARY = os.path.join(
    '..', '..', 'Data', 'ProcessedData', 'SFStreetView',
    'segment_dictionary_{}.json'.format(SELECTED_LOCATION))
OUTPUT_PATH = os.path.join(
    '..', '..', 'Data', 'ProcessedData', 'SFStreetView', SELECTED_LOCATION)

img_params = {
    'size': '640x640',
    'key': CONFIG.SV_api_key,
}

# Load street segment information and check output directory
try:
    with open(SEGMENT_DICTIONARY, 'r') as segment_file:
        segment_dictionary = json.load(segment_file)
except FileNotFoundError:
    raise Exception('[ERROR] Segment dictionary not found.')

if not os.path.exists(OUTPUT_PATH):
    print('[INFO] Creating output path: {}'.format(OUTPUT_PATH))
    os.makedirs(OUTPUT_PATH)

# Save images for each street segment
print('[INFO] Saving images for {} street segments.'.format(
    len(segment_dictionary)))
main_counter = 0

for key, segment in tqdm(segment_dictionary.items()):
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
    previous_headings = 0, 0

    for (lat, lng), heading1, heading2 in segment['coordinates']:
        for heading_num, heading in enumerate([heading1, heading2]):
            # Check if heading is None
            if heading is None:
                heading = previous_headings[heading_num]

            # Get image meta data
            img_params['heading'] = heading
            img_params['location'] = '{},{}'.format(lat, lng)
            image_metadata = get_SV_metadata(params=img_params)
            image_panoid = image_metadata['pano_id']
            # TODO check image dates?

            # Check if the image's view of the location is unique by comparing
            # to previously queried headings
            save = True
            if image_panoid in panorama_dict.keys():
                # Check queried headings
                for queried_heading in panorama_dict[image_panoid]:
                    if abs(queried_heading - heading) < 50:
                        save = False
                # Add current heading if unique
                panorama_dict[image_panoid].append(heading)
            else:
                panorama_dict[image_panoid] = [heading]

            # Save if unique
            if save:
                image = get_SV_image(params=img_params)
                file_name = 'img_{}_h{}_{}.png'.format(
                    segment_id, heading_num, str(location_counter).zfill(3))
                image.save(os.path.join(OUTPUT_PATH, file_name))

                # Increase counters
                location_counter += 1
                main_counter += 1

        # Update headings
        previous_headings = heading1, heading2


print('[INFO] Image collection complete.'
      ' Loaded {} images for {} street segments.'.format(
    main_counter, len(segment_dictionary)))
