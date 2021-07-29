import numpy as np
import os

import DataScripts.CONFIG as CONFIG
from DataScripts.urbanchange_utils import save_SV_image, reverse_geocode


# Test set parameters
TARGET_NUM_TEST_IMAGES = 100
OUTPUT_DIR = os.path.join('..', '..', 'Data', 'RawData',
                          'ObjectDetection', 'Res_640', 'MissionDistrictTestSet')
# Define the grid cell from which we will sample our locations
GRID = [[37.76583204171835, -122.43090178068529],  # Mission District
        [37.74947816540197, -122.40373636829808]]

# Set up a parameter dictionary for each image and reverse geocode request
img_params = {
    'size': '640x640',
    'key': CONFIG.SV_api_key,
}

geo_params = {
    'key': CONFIG.SV_api_key
}


if __name__ == '__main__':
    # Verify output directory
    if not os.path.exists(OUTPUT_DIR):
        print('[INFO] Creating output directory')
        os.makedirs(OUTPUT_DIR)

    # Random sample (2 x TARGET_NUM_TEST_IMAGES) locations within the neighborhood
    print('[INFO] Generating random locations...')
    np.random.seed(42)
    lats = np.random.uniform(low=GRID[1][0], high=GRID[0][0],
                             size=TARGET_NUM_TEST_IMAGES * 2)
    lngs = np.random.uniform(low=GRID[1][1], high=GRID[0][1],
                             size=TARGET_NUM_TEST_IMAGES * 2)

    # Save test images
    test_counter = 0
    print('[INFO] Saving images for each location...')
    for i, (lat, lng) in enumerate(zip(lats, lngs)):
        # Geocode location to addresses if available
        geo_params['latlng'] = '{},{}'.format(lat, lng)
        geo_request = reverse_geocode(params=geo_params)
        if geo_request['status'] != 'OK':
            continue
        elif len(geo_request['results']) == 0:
            continue
        else:
            address = geo_request['results'][0]['formatted_address']

        # Verify that the address is within the neighborhood
        address_lat = geo_request['results'][0]['geometry']['location']['lat']
        address_lng = geo_request['results'][0]['geometry']['location']['lng']
        lat_OK = abs(GRID[0][0]) >= abs(address_lat) >= abs(GRID[1][0])
        lng_OK = abs(GRID[0][1]) >= abs(address_lng) >= abs(GRID[1][1])
        if not lat_OK and lng_OK:
            continue

        # Get image of the location
        img_params['location'] = address
        save_SV_image(params=img_params, output_dir=OUTPUT_DIR,
                      file_name='test_{}'.format(str(test_counter).zfill(3)))
        test_counter += 1

print('[INFO] {} Test images generated.'.format(test_counter))
