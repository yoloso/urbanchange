# locations.py
# Dictionary of locations for which to generate street segments, GSV imagery
# and visualizations.
# Usage: Add a location by inserting a new key and dictionary with the following
# items:
#       - 'type': one of ['box', 'place']. A 'box' is a bounding box specified
#         by four coordinates in the 'location' key. A 'place' is a location
#         that is automatically recognized on OpenStreetMap (OSM) such as a city
#       - 'location': Four coordinates representing a bounding box of the location
#       - 'start_location': A (lat, lng) pair to be used to center the map of
#         the location.
#       - 'name': The name of a 'place' type location as recognized in OSM


LOCATIONS = {
    'MissionDistrict': {
        'type': 'box',
        'location': [[37.76583204171835, -122.43090178068529],
                     [37.74947816540197, -122.40373636829808]],
        'start_location': [37.76583204171835, -122.43090178068529]
    },
    'MissionDistrictBlock': {
        'type': 'box',
        'location': [[37.76510958212885, -122.42461359879468],
                     [37.762898815227565, -122.42121402824374]],
        'start_location': [37.76510958212885, -122.42461359879468]
    },
    'SanFrancisco': {
        'type': 'place',
        'location': [[37.80566148176605, -122.51363914033222],
                     [37.70988986803049, -122.377542437462]],
        'name': 'San Francisco, California',
        'start_location': [37.76317373644425, -122.44651317628211]
    },
    'GoldenGateHeights': {
        'type': 'box',
        'location': [[37.76144285680283, -122.47511505804738],
                     [37.75225352830853, -122.4671005110224]],
        'start_location': [37.76144285680283, -122.47511505804738]
    },
    'MissionTenderloinAshburyCastroChinatown': {
        'type': 'box',
        'location': [[37.74551641104773, -122.45495578045093],
                     [37.799486835187444, -122.40447080875227]],
        'start_location': [37.772839440364585, -122.41986929780208]
    },
    'SouthBend': {
        'type': 'place',
        'location': [[41.75286541950123, -86.363433534086],
                     [41.59566756745622, -86.19314545442855]],
        'name': 'South Bend, Indiana',
        'start_location': [41.676494188484845, -86.26592987557245]
    },
    'Chicago': {
        'type': 'place',
        'location': [[42.024671102279264, -87.8326540363325],
                     [41.64109780317916, -87.49998447950928]],
        'name': 'Chicago, Illinois',
        'start_location': [41.85324738445851, -87.66353152420449]
    },
    'MexicoCity': {
        'type': 'place',
        'location': [[19.596516841651727, -99.32558215067766],
                     [19.179394348660736, -98.96097339947566]],
        'name': 'Mexico City, Mexico',
        'start_location': [19.452199533400194, -99.13332141558057]
    },
    'MexicoCityCenter': {
        'type': 'box',
        'location': [[19.416294852339142, -99.1762811231248],
                     [19.438352049598038, -99.12525478024558]],
        'start_location': [19.42641320456356, -99.14383712358155]
    },
    'MexicoCityCentroDoctores': {
        'type': 'box',
        'location': [[19.41325331862834, -99.15464836500303],
                     [19.437253473825134, -99.12924248222085]],
        'start_location': [19.42745957224932, -99.14078670936344]
    }
}
