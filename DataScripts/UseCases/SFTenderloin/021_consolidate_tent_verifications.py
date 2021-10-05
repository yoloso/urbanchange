import pandas as pd
import os


# Load files
f3 = os.path.join(
    'Data', 'ProcessedData', 'UseCases', 'SFTenderloin', 'Tent_verification', 'tent_checks_Joe.csv')
f2 = os.path.join(
    'Data', 'ProcessedData', 'UseCases', 'SFTenderloin', 'Tent_verification', 'tent_checks_Jesu.csv')
f1 = os.path.join(
    'Data', 'ProcessedData', 'UseCases', 'SFTenderloin', 'Tent_verification', 'tent_checks_Jack.csv')
files = [f1, f2, f3]

file_dict = {}
for i, file in enumerate(files):
    with open(file, 'r', encoding="ascii") as f:
        file_dict['{}'.format(i)] = pd.read_csv(f)

# Select relevant rows from each file
# Jack 1-1800
file_dict['0'] = file_dict['0'].iloc[0:1800]

# Joe 1801-3600
file_dict['2'] = file_dict['2'].iloc[1800:3600]

# Jesu 3601-4614
file_dict['1'] = file_dict['1'].iloc[3600:4613]

# Concatenate
selected_cols = list(file_dict['1'].columns)[0:13]
consolidated = pd.concat([
    file_dict['0'][selected_cols], file_dict['1'][selected_cols],
    file_dict['2'][selected_cols]])

# Save file
consolidated.to_csv(
    os.path.join('Data', 'ProcessedData', 'UseCases', 'SFTenderloin',
                 'Tent_verification','tent_checks_consolidated.csv'),
    index=False)
