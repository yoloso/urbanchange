import json
import os
from PIL import Image, ImageChops

import CONFIG
from utils import get_SV_image

# Parameters
SEGMENT_DICTIONARY = os.path.join(
    '..', '..', 'Data', 'ProcessedData', 'SFStreetView',
    'segment_dictionary_MDblock.json')
OUTPUT_PATH = os.path.join(
    '..', '..', 'Data', 'ProcessedData', 'SFStreetView', 'MDblock')

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
print('[INFO] Saving images for {} street segments.'.format(len(segment_dictionary)))
main_counter = 0

for key, segment in segment_dictionary.items():
    if int(key) % 1000 == 0:
        print('[INFO] Processing segment {}/{}'.format(key, len(segment_dictionary)))

    # Hash segment ID and get headings
    segment_id = json.loads(segment['segment_id'])
    segment_id = '{}-{}'.format(segment_id[0], segment_id[1])
    headings = (segment['heading1'], segment['heading2'])

    # Check segment coordinates
    if len(segment['coordinates']) == 0:
        print('[WARNING] No coordinates for segment {}: {}'.format(
            key, segment['name']))
    # TODO MODIFY FOR CURVED STREETS
    # Get images for each heading and coordinate
    for heading_num, heading in enumerate(headings):
        previous_image = Image.new('RGB', (1, 1))
        heading_counter = 0
        img_params['heading'] = heading

        for coordinate in segment['coordinates']:
            # TODO check image dates?
            img_params['location'] = '{},{}'.format(coordinate[0], coordinate[1])
            image = get_SV_image(params=img_params)

            # Check if image is unique (we only have to check the previous image)
            img_difference = ImageChops.difference(image, previous_image)
            if img_difference.getbbox():
                previous_image = image
                file_name = 'img_{}_h{}_{}.png'.format(
                    segment_id, heading_num, str(heading_counter).zfill(3))
                image.save(os.path.join(OUTPUT_PATH, file_name))
                heading_counter += 1
                main_counter += 1

print('[INFO] Image collection complete. Loaded {} images for {} street segments.'.format(
    main_counter, len(segment_dictionary)))
