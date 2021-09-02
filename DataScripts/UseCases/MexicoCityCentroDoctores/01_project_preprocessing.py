import json
import os
import pandas as pd

from CONFIG import SV_api_key
from DataScripts.urbanchange_utils import geocode
from DataScripts.read_files import load_segment_dict
from locations import LOCATIONS


# Parameters
INPUT_DATA = os.path.join(
    'Data', 'ProcessedData', 'UseCases', 'MexicoCity',
    'cuauhtemoc_presupuesto4.csv')
SEGMENT_DICTIONARY_FILE = os.path.join(
    'Data', 'ProcessedData', 'SFStreetView',
    'segment_dictionary_MexicoCityCentroDoctores.json'
)
SELECTED_NEIGHBORHOOD = 'MexicoCityCentroDoctores'

neighborhood = LOCATIONS[SELECTED_NEIGHBORHOOD]
ADDRESS_PARAMS = {
    'key': SV_api_key,
    'bounds': '{}|{}'.format(
        ','.join(str(coord) for coord in neighborhood['location'][0]),
        ','.join(str(coord) for coord in neighborhood['location'][1]))
}


# Helper functions
def process_address(address):
    parsed_address = address.replace(' ', '+')

    address_params = ADDRESS_PARAMS.copy()
    address_params['address'] = parsed_address
    response = geocode(address_params)

    if response.ok:
        results = json.loads(response.text)
        if len(results['results']) > 1:
            print('[WARNING] Multiple results for: {}'.format(address))
        coordinate_pair = '{},{}'.format(
            results['results'][0]['geometry']['location']['lat'],
            results['results'][0]['geometry']['location']['lng']
        )
        return coordinate_pair
    else:
        print('[WARNING] No results for: {}'.format(address))
        return None


def process_locations(location):
    loc_type, locations = location.split(': ')

    # Process location according to type
    if loc_type == 'Segments':
        coordinates = []
        # Collect coordinates for each segment
        for segment in locations.split('; '):
            segment_id = '[{}, {}]'.format(segment.split('-')[0], segment.split('-')[1])
            # Find the segment in segment dictionary
            for key, value in segment_dict.items():
                if value['segment_id'] == segment_id:
                    for (lat, lng), h1, h2 in value['coordinates']:
                        coordinates.append('{},{}'.format(lat, lng))

        return coordinates
    elif loc_type == 'Addresses':
        addresses = locations.split('; ')
        coordinates = []
        for address in addresses:
            coordinate = process_address(address)
            if coordinate is not None:
                coordinates.append(coordinate)
        return coordinates
    else:
        raise Exception('[ERROR] Location type should be Segments or Adddresses')


# Load data
try:
    projects = pd.read_csv(INPUT_DATA, na_values='NA', encoding='latin-1')
except FileNotFoundError:
    raise Exception('[ERROR] Input file not found.')
segment_dict = load_segment_dict(SEGMENT_DICTIONARY_FILE)


# Filter for 2018 projects in neighborhoods within MexicoCityCentroDoctores scope
projects = projects[
    (projects['AÑO'] == 2018) & (projects['MexicoCityCentroDoctores'] == 1)]

# Filter for projects that have specific locations
projects = projects[projects['Locations'].notnull()]

# Obtain lat, lng coordinates for projects with addresses
projects['processed_locations'] = projects['Locations'].apply(process_locations)

# Convert to long format
projects = projects.explode('processed_locations', ignore_index=True)

# Select columns
projects = projects[[
    'COLONIA', 'NOMBRE DEL PROYECTO', 'MONTO', 'Start', 'End', 'Type',
    'processed_locations']]

# Save
projects.to_csv(os.path.join(
    os.path.dirname(INPUT_DATA), 'cuauhtemoc_presupuesto_long.csv'), index=False)
