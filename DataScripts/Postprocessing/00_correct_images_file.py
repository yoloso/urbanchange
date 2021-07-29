# 00_correct_images_file.py

import argparse
import os
import pandas as pd
import shutil
from tqdm import tqdm

from DataScripts.urbanchange_utils import Logger


# Parameters
IMAGE_LOG_NAMES = ['segment_id', 'img_id', 'panoid', 'img_date']

# Set up command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-i', '--images_dir', required=True,
                    help='Path to the directory containing images.txt')


if __name__ == '__main__':
    # Capture command line arguments
    args = vars(parser.parse_args())
    images_dir = args['images_dir']

    # Get number of columns
    num_columns_image_log = len(IMAGE_LOG_NAMES)

    # Load images.txt file for neighborhood
    try:
        print('[INFO] Reading images.txt file with {} columns'.format(
            num_columns_image_log))
        with open(os.path.join(images_dir, 'images.txt'), 'r') as file:
            image_log = pd.read_csv(
                file, sep=' ', header=0, names=IMAGE_LOG_NAMES,
                na_values=['None'])
    except FileNotFoundError:
        raise Exception('[ERROR] images.txt file not found.')
    except pd.errors.ParserError:
        print('[INFO] Generating corrected images.txt file.'
              ' Saving original file to images_raw.txt')

        # Save original file to images_raw.txt
        shutil.copyfile(
            os.path.join(images_dir, 'images.txt'),
            os.path.join(images_dir, 'images_raw.txt'))

        # Find the lines with multiple image logs
        with open(os.path.join(images_dir, 'images_raw.txt'), 'r') as file:
            image_log = file.readlines()
        new_image_log = Logger(os.path.join(images_dir, 'images.txt'))

        for i, log in enumerate(tqdm(image_log)):
            if len(log.split(' ')) == num_columns_image_log:
                new_image_log.write(log.rstrip())
            elif len(log.split(' ')) <= num_columns_image_log:
                raise Exception('[ERROR] Too few columns in row {}: {}.'.format(
                    i, len(log.split(' '))))
            else:
                print('[INFO] Fixing line {}'.format(i))

                # Split the row with two image logs
                comps = log.split(' ')
                log1 = ' '.join([comps[0], comps[1], comps[2], comps[3][0:10]])
                log2 = ' '.join([comps[3][10:], comps[4], comps[5], comps[6]])
                new_image_log.write(log1)
                new_image_log.write(log2.rstrip())

    print('[INFO] images.txt file ready to be used in Postprocessing pipeline.')
