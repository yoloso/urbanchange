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
overlap_jesu = file_dict['1'].copy()
file_dict['1'] = file_dict['1'].iloc[3600:4613]

# Check overlap on Jesu's file. As seen using file_dict['2'].info() Joe
# completed tent verifications so any additional information would be useful
# for Jack's tents.
overlap_jesu = overlap_jesu.iloc[0:1800]

for i in range(overlap_jesu.shape[0]):
    if pd.isna(overlap_jesu.iloc[i]['true_tent']):
        # Check if Jack has this tent
        if pd.notna(file_dict['0'].iloc[i]['true_tent']):
            overlap_jesu.at[i, 'true_tent'] = file_dict['0'].iloc[i]['true_tent']

# Replace Jack's file with the overlap file
file_dict['0'] = overlap_jesu.copy()

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
