import json
import os
from PIL import Image, ImageChops

import CONFIG
from utils import get_SV_image


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

for key, segment in segment_dictionary.items():
    if int(key) % 1000 == 0:
        print('[INFO] Processing segment {}/{}'.format(
            key, len(segment_dictionary)))

    # Hash segment ID
    segment_id = json.loads(segment['segment_id'])
    segment_id = '{}-{}'.format(segment_id[0], segment_id[1])

    # Check segment coordinates
    if len(segment['coordinates']) == 0:
        print('[WARNING] No coordinates for segment {}: {}'.format(
            key, segment['name']))

    # Set up images for comparison (this is to verify that a GSV call
    # returns a new image)
    previous_image_1 = Image.new('RGB', (1, 1))
    previous_image_2 = Image.new('RGB', (1, 1))
    temporary_images = [None, None]

    # Get images for each coordinate and heading
    location_counter = 0
    for (lat, lng), heading1, heading2 in segment['coordinates']:
        for heading_num, heading in enumerate([heading1, heading2]):
            img_params['heading'] = heading

            # TODO check image dates?
            img_params['location'] = '{},{}'.format(lat, lng)
            image = get_SV_image(params=img_params)

            # Check if image is unique (we only have to check the 2 previous
            # images in case the bearing was in the opposite direction)
            img_difference_1 = ImageChops.difference(image, previous_image_1)
            img_difference_2 = ImageChops.difference(image, previous_image_2)

            # If image is different from both previous images, we save it
            if img_difference_1.getbbox() and img_difference_2.getbbox():
                file_name = 'img_{}_h{}_{}.png'.format(
                    segment_id, heading_num, str(location_counter).zfill(3))
                image.save(os.path.join(OUTPUT_PATH, file_name))

                # Update temporary image list and increase counters
                temporary_images[heading_num] = image
                location_counter += 1
                main_counter += 1

        # Update previous images
        previous_image_1, previous_image_2 = temporary_images

print('[INFO] Image collection complete.'
      'Loaded {} images for {} street segments.'.format(
    main_counter, len(segment_dictionary)))
