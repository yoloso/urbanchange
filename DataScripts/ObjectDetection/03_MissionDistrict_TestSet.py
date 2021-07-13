import glob
import os
import random
import shutil


# Parameters
INPUT_DIR = os.path.join('..', '..', 'Data', 'ProcessedData', 'SFStreetView',
                         'Res_640', 'MissionDistrict_2021-02-01_2')
OUTPUT_DIR = os.path.join('..', '..', 'Data', 'RawData', 'ObjectDetection',
                          'Res_640', 'MissionDistrictTestSet')
NUM_RANDOM_TEST_IMAGES = 100
SEGMENT_IDS = ['65307093-65307098'] # evaluate an entire street segment

if not os.path.exists(OUTPUT_DIR):
    print('[INFO] Creating output directory: {}'.format(OUTPUT_DIR))
    os.makedirs(OUTPUT_DIR)

# Grab images from specific segments
print('[INFO] Grabbing images from specific segments.')
for segment_id in SEGMENT_IDS:
    specific_image_paths = glob.glob(os.path.join(INPUT_DIR, 'img_{}*'.format(segment_id)))
    for image_path in specific_image_paths:
        new_image_path = os.path.join(OUTPUT_DIR, image_path.split(os.path.sep)[-1])
        shutil.copyfile(image_path, new_image_path)

# Grab NUM_RANDOM_TEST_IMAGES and copy to output directory
print('[INFO] Adding {} random images'.format(NUM_RANDOM_TEST_IMAGES))
image_paths = glob.glob(os.path.join(INPUT_DIR, '*'))

if len(image_paths) >= NUM_RANDOM_TEST_IMAGES:
    # Add images from NUM_SEGMENTS specific segments
    indices = list(range(len(image_paths)))
    random.seed(42)
    random.shuffle(indices)

    # Add randomly chosen images
    image_counter = 0
    while image_counter < 99:
        image_path = image_paths[indices[image_counter]]

        # Check if image belongs to one of the specific segment IDs and save if not
        img_segment_id = image_path.split(os.path.sep)[-1].split('_')[1]
        if img_segment_id not in SEGMENT_IDS:
            new_image_path = os.path.join(OUTPUT_DIR, image_path.split(os.path.sep)[-1])
            shutil.copyfile(image_path, new_image_path)
            image_counter += 1

else:
    raise Exception('[ERROR] Number of test images cannot be less than number of images.')
