import re
import numpy as np
from decimal import Decimal
import pandas as pd
import os, sys, math, stat, json, statistics
import requests
from requests.auth import HTTPDigestAuth
import config
from config import GENESYS_FILE
from datetime import datetime





print("Config in Normalised loaded successfully:", config.workdirectories)


def normalname(name):
    if isinstance(name, str):
        name = name.replace(" & "," AND ").replace(r'[^A-Za-z0-9 ]+', '').replace("'","").replace(".","").replace(","," ").replace("  "," ").strip().replace(" ","_").upper()
    elif isinstance(name, pd.Series):
        name = name.str.replace(" & "," AND ").str.replace(r'[^A-Za-z0-9 ]+', '').str.replace("'","").str.replace(".","").str.replace(","," ").str.replace("  "," ").str.strip().str.replace(" ","_").str.upper()
    else:
        print("______ERROR: Can only normalise name in a string or series")
    return name
def extract_initials(words):
    """Extract initials from word list and return (remaining_words, initials_string)"""
    initials = [w for w in words if re.fullmatch(r'([A-Z]\s?)+', w)]
    remaining = [w for w in words if w not in initials]
    return remaining, ' '.join(initials)

def classify_namecolumn(series):
    """Count how often values in a column appear as common firstnames or surnames"""
# Sample common names (you can expand these sets as needed)
    COMMON_FIRSTNAMES = {'John', 'Jane', 'Mike', 'Manoja', 'David', 'Ashley', 'Robert', 'Emily'}
    COMMON_SURNAMES = {'Smith', 'Davies', 'Thomas', 'Baker', 'Radford', 'Roberts', 'Senthilnathan', 'Stephens'}

    counts = {'firstname': 0, 'surname': 0}
    for val in series.dropna():
        val = val.strip()
        if val in COMMON_FIRSTNAMES:
            counts['firstname'] += 1
        if val in COMMON_SURNAMES:
            counts['surname'] += 1
    return counts

def NormaliseName(df):
    df = df.copy()
    if 'ElectorName' not in df.columns:
        if 'Initials' not in df.columns:
            df['ElectorName'] = df['Firstname']+" "+df['Surname']
            df['ElectorName_Normalized'] = df['ElectorName']
        else:
            df['ElectorName'] = df['Firstname']+" "+df['Initials']+" "+df['Surname']
            df['ElectorName_Normalized'] = df['ElectorName']
    else:
        # Step 1: Split and extract initials
        parts = df['ElectorName'].dropna().apply(lambda x: x.strip().split())
        processed = parts.apply(lambda x: extract_initials(x))
        df['Initials'] = processed.apply(lambda x: x[1])
        df['part1'] = processed.apply(lambda x: x[0][0] if len(x[0]) > 0 else None)
        df['part2'] = processed.apply(lambda x: x[0][1] if len(x[0]) > 1 else None)

        # Step 2: Classify part1 vs part2
        classification = {
            'part1': classify_namecolumn(df['part1']),
            'part2': classify_namecolumn(df['part2'])
        }

        firstname_col = 'part1' if classification['part1']['firstname'] >= classification['part2']['firstname'] else 'part2'
        surname_col = 'part2' if firstname_col == 'part1' else 'part1'

        # Step 3: Assign columns
        df['Firstname'] = df[firstname_col]
        df['Surname'] = df[surname_col]

        # Step 4: Create normalized ElectorName
        df['ElectorName_Normalized'] = df[['Firstname', 'Initials', 'Surname']].fillna('').apply(
            lambda row: ' '.join(filter(None, row)), axis=1
        )

                # Reorder if desired
    cols_to_front = ['ElectorName', 'Firstname', 'Initials', 'Surname', 'ElectorName_Normalized']
    df = df[[c for c in cols_to_front if c in df.columns] + [c for c in df.columns if c not in cols_to_front]]

    # Return full enriched DataFrame
    return df

def DFpostcodetoDF(df):
    vars = list(df.columns)
    vars_ = [d.replace(" ", "_") for d in vars]
    varvalues = [[] for _ in vars]

    DF = pd.DataFrame()

    for i, varb in enumerate(vars):
        for index, elector in df.iterrows():
            value = str(elector[varb])
            if varb == 'Postcode' and len(value) == 8:
                value = value.replace(" ", "")
            varvalues[i].append(value)

    for i, (colname, values) in enumerate(zip(vars_, varvalues)):
        insert_pos = min(i, DF.shape[1])
        if colname in DF.columns:
            print(f"⚠️ Column '{colname}' already exists. Skipping insert.")
            continue
        DF.insert(insert_pos, colname, values)

    return DF

def TabletoDF (T, compress):
# extract into a dataframe from all column names in meta and attrubute section from the source Orange Table
    block = T
    domain = block.domain
    vars = []
    vars_ = []
    varvalues = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]
    tvx = block.Y.shape[1]
    tvy = block.X.shape[1]
    tvm = block.metas.shape[1]
    for d in domain:
      vars.append(d.name)
      vars_.append(d.name.replace(" ","_"))
    DF = pd.DataFrame()
    i = 0
    for var in vars:
      newp = False
  # for every elector in the block ,   extract the variable values into a DF dataframe
      for elector in block:
        if compress and var == 'Postcode' and len(elector['Postcode'].value) == 8:
          varvalues[i].append(elector[var].value.replace(" ",""))
        else:
          varvalues[i].append(elector[var].value)
      DF.insert(i, vars_[i], varvalues[i])
      i=i+1
    return DF
  # electors0 uses compressed postcodes electors10 uses the expanded postcodes to extract elevation by postcode lookup

def extractfactors(data):

    def checkEname(name):
        pattern = r"(?P<Firstname>David|[A-Za-z'-]+)\s*(?P<Initials>(?:[A-Z](?:\s+[A-Z])*)*)\s*(?P<Surname>[A-Za-z'-]+)"
        return re.match(pattern, name)


    datamax = data.shape[0]
    name_order = None

    for col in data.columns:
        i = 0
    #make every column name in the source UpperCase
    #remove unnecessary surplus pre-fix words like ELECTOR, PROPERTY
    # normalise the column names
    # add in derived columns Lat, Long,

        DATA = data.rename(columns= {col: Ncol})
        if Ncol == "ElectorName":
            for name in data[Ncol].astype(str).values.tolist():
                match = checkEname(name)
                if match:
                    # Determine the first match's order for Firstname, Surname, and Initials
                    if name_order is None:
                        if "David" in name:  # If 'David' appears in the name, treat it as Firstname
                            name_order = ('Firstname', 'Surname', 'Initials')
                        else:
                            name_order = ('Firstname', 'Initials', 'Surname')

                    # Extract data based on the determined order
                    firstname = match.group(name_order[0])
                    surname = match.group(name_order[1])
                    initials = match.group(name_order[2]) if match.group(name_order[2]) else None

                    # Output the extracted fields
                    print(f"Firstname: {firstname}, Surname: {surname}, Initials: {initials}")
                    i = i+1
                    if i > 0.95*(datamax) :
                        return DATA

    return DATA

def checkForeName(data):
    pattern = r"^(?!\d+(\.\d+)?$)(?P<Surname>[A-Za-z-]+(?:'[A-Za-z]+)?)\s+(?P<Firstname>[A-Za-z-]+(?:'[A-Za-z]+)?)\s*(?P<Initials>(?:[A-Z](?:\s+[A-Z])*)*)$"
    datamax = data.shape[0]
    for col in data.columns:
        i = 0
        for row in data[col]:
            match = re.match(pattern, str(row))
            if match :
                i = i+1
                surname = match.group("Surname")
                firstname = match.group("Firstname")
                initials = match.group("Initials") if match.group("Initials") else None
                print("Surname: {0}, Firstname: {1}, Initials: {2}".format(surname,firstname,initials))
                if i > 0.95*(datamax) :
                    return col

    return None


def checkENOP(data):
    pattern = r"([A-Za-z0-9]+)-(\d+)(?:/(\d+))?"
    datamax = data.shape[0]
    for col in data.columns:
        i = 0
        for row in data[col]:
            match = re.match(pattern, str(row))
            print("value ", str(row), i, match)
            if match :
                i = i+1
                if i > 0.95*(datamax) :
                    return col
    return None


def classify_column(series):
    """
    Classify a column based on regex pattern matching.
    Supports ENOP, ENOT, ENOS, ENO, PD, and Suffix.
    """
    series = series.dropna().astype(str).str.strip()

    patterns = {
        'ENOP': r'^[A-Za-z]+\d+-\d+[./]\d+$',  # e.g. PD123-456/7 or PD123-456.7
        'ENOT': r'^[A-Za-z]+\d+-\d+$',         # e.g. PD123-456
        'ENOS': r'^\d+(?:[./]\d+)?$',               # e.g. 1234/2 or 1234.2
        'ENO':  r'^[1-9]\d*$',                 # e.g. 1234
        'PD':   r'^[A-Za-z]+\d+$',             # e.g. PD123
        'Suffix': r'^[1-9]\d*$',               # e.g. 2
    }

    preferred_order = ['ENOP', 'ENOT', 'ENOS', 'ENO', 'PD', 'Suffix']
    best_label = 'Unknown'
    best_ratio = 0

    for label in preferred_order:
        pattern = patterns[label]
        match_ratio = series.str.match(pattern).mean()
        if match_ratio > best_ratio:
            best_ratio = match_ratio
            best_label = label

    return best_label if best_ratio >= 0.5 else 'Unknown'


def normalise_eno_column(df):
    """
    Normalize and derive PD, ENO, Suffix, ENOT, and ENOP from potentially ambiguous columns.
    Recognizes ENOS (ENO.Suffix or ENO/Suffix) and treats standalone ENO as ENOS with suffix 0.
    """
    df = df.copy()

    allowed_cols = {'X', 'PD', 'ENO', 'Suffix', 'ENOT', 'ENOP', 'ENOS'}
    candidate_cols = [col for col in df.columns if col in allowed_cols]

    classification_map = {}
    for col in candidate_cols:
        label = classify_column(df[col])
        if label != 'Unknown':
            classification_map[col] = label

    # Rename columns only if not already present
    for col, label in classification_map.items():
        if label in {'PD', 'ENO', 'Suffix'} and label not in df.columns:
            df.rename(columns={col: label}, inplace=True)

    # Use ENOT/ENOP/ENOS to parse if PD or ENO missing
    if 'ENO' not in df.columns or 'PD' not in df.columns:
        eno_source_col = None
        source_label = None
        for col, label in classification_map.items():
            if label in {'ENOT', 'ENOP', 'ENOS'}:
                eno_source_col = col
                source_label = label
                break

        if eno_source_col:
            parse_series = df[eno_source_col].astype(str).str.strip().str.replace('/', '.', regex=False)

            if source_label in {'ENOT', 'ENOP'}:
                df['PD'] = parse_series.str.extract(r'^([A-Za-z]+[0-9]+)-')[0]
                df['ENO'] = parse_series.str.extract(r'-([1-9][0-9]*)')[0]
                df['Suffix'] = parse_series.str.extract(r'\.(\d+)$')[0]

            elif source_label == 'ENOS':
                df['ENO'] = parse_series.str.extract(r'^(\d+)')[0]
                df['Suffix'] = parse_series.str.extract(r'\.(\d+)$')[0]
                df['Suffix'] = df['Suffix'].fillna(0)

            # Coerce numeric
            df['ENO'] = pd.to_numeric(df['ENO'], errors='coerce')
            df['Suffix'] = pd.to_numeric(df['Suffix'], errors='coerce')

            df.loc[df['ENO'] <= 0, 'ENO'] = None
            df.loc[df['Suffix'] < 0, 'Suffix'] = None

    # Ensure suffix is numeric and default to 0 if missing
    df['Suffix'] = pd.to_numeric(df['Suffix'], errors='coerce').fillna(0).astype(int)

    # Derive ENOT
    df['ENOT'] = None
    valid_enot_mask = df['PD'].notna() & df['ENO'].notna()
    df.loc[valid_enot_mask, 'ENOT'] = (
        df.loc[valid_enot_mask, 'PD'].astype(str) + '-' + df.loc[valid_enot_mask, 'ENO'].astype(int).astype(str)
    )

    # Derive ENOP (always include suffix, default 0)
    df['ENOP'] = df['ENOT']
    valid_enop_mask = valid_enot_mask
    df.loc[valid_enop_mask, 'ENOP'] = (
        df.loc[valid_enop_mask, 'ENOT'] + '.' + df.loc[valid_enop_mask, 'Suffix'].astype(str)
    )


    return df

def contactDetails(df):
    # Allowed statuses
    VALID_STATUSES = {"member", "volunteer", "houseboarder", "captain"}

    # Sample DataFrame
    # df = pd.read_csv("your_file.csv")

    def validate_email(email):
        if pd.isna(email):
            return None
        email = email.strip().lower()
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return email if re.match(pattern, email) else None

    def normalize_uk_mobile(mobile):
        if pd.isna(mobile):
            return None
        mobile = re.sub(r'\D', '', str(mobile))  # Remove non-digit chars
        if mobile.startswith("00447"):
            return "+44" + mobile[4:]
        elif mobile.startswith("447"):
            return "+44" + mobile[2:]
        elif mobile.startswith("07") and len(mobile) == 11:
            return "+44" + mobile[1:]
        elif mobile.startswith("+447") and len(mobile) == 13:
            return mobile
        else:
            return None

    def clean_status(status):
        if pd.isna(status):
            return None
        status_clean = str(status).strip().lower()
        return status_clean if status_clean in VALID_STATUSES else None

    # Apply to DataFrame
    df['Email'] = df['Email'].apply(validate_email)
    df['Mobile'] = df['Mobile'].apply(normalize_uk_mobile)
    df['Status'] = df['Status'].apply(clean_status)

    # Optional: Filter out invalid entries
    df_valid = df.dropna(subset=['email_clean', 'mobile_clean', 'status_clean'])
    return df_valid



def add_row_number(df, column_name='RNO'):

    # Only add if RNO doesn't already exist
    if column_name not in df.columns:
        df[column_name] = range(1, len(df) + 1)

    # Reorder so RNO is the first column
    cols = [column_name] + [col for col in df.columns if col != column_name]
    return df


def NormaliseAddress(RunningVals2, Lookups, ImportFilename, df):
    """
    Full address normalisation routine with staged progress reporting.
    - Converts postcodes
    - Splits combined addresses
    - Adds Lat/Long/Elevation
    - Sets StreetName, AddressNumber, and AddressPrefix
    """

    import re, math, requests, json, statistics
    import numpy as np
    from state import progress

    # Convert postcodes to 8-character compressed format
    df = DFpostcodetoDF(df)

    # Ensure Address2..Address6 columns exist
    for col in ['Address2', 'Address3', 'Address4', 'Address5', 'Address6']:
        if col not in df.columns:
            df[col] = ""

    # Clean Postcode column
    df['Postcode'] = df['Postcode'].astype(str).str.strip()
    df['Postcode'].replace(['', 'nan', 'NaN', 'None'], np.nan, inplace=True)
    df = df.dropna(subset=['Postcode'])

    # Merge Lat/Long and Elevation lookups
    electors1 = df.merge(Lookups['LatLong'], how='left', on='Postcode')
    electors1.to_csv(ImportFilename+"-latlongs.csv", index=False)
    electors2 = electors1.merge(Lookups['Elevation'], how='left', on='Postcode')

    electors2['Lat'] = electors2['Lat'].astype(float)
    electors2['Long'] = electors2['Long'].astype(float)

    # Ensure required columns exist
    required_columns = ['AddressPrefix', 'StreetName', 'AddressNumber',
                        'Address_1', 'Address_2', 'Address_3', 'Address_4', 'Address_5', 'Address_6']
    for col in required_columns:
        if col not in electors2.columns:
            electors2[col] = np.nan

    # Function to split combined Address1 into two if needed
    def split_after_4alpha_and_comma(addr):
        if not isinstance(addr, str): return addr, None
        match = re.search(r'([A-Za-z]{4}),', addr)
        if match:
            split_index = match.end()
            part1 = addr[:split_index - 1].strip()
            part2 = addr[split_index:].strip()
            return part1, part2
        return addr, None

    # --- Progress stage setup ---
    stage_fraction = progress['stages'].get('norming', 0.4)
    accumulated_percent_before = sum(
        f for stage, f in progress['stages'].items() if stage in ['sourcing']
    )

    # Set up fallback RunningVals2 attributes
    RunningVals2.setdefault('Last_Lat', 51.240299)
    RunningVals2.setdefault('Last_Long', -0.562301)
    RunningVals2.setdefault('Mean_Lat', 51.240299)
    RunningVals2.setdefault('Mean_Long', 51.240299)

    # --- Process each elector ---
    for index, elector in electors2.iterrows():
        # --- Update progress ---
        local_percent = (index + 1) / len(electors2)
        progress['percent'] = round(100 * (accumulated_percent_before + local_percent * stage_fraction), 2)
        progress['status'] = 'norming'
        progress['message'] = f'Normalising addresses ({index+1}/{len(electors2)})'

        # --- Split Address1 if needed ---
        addr = str(elector["Address1"])
        new_addr1, new_addr2 = split_after_4alpha_and_comma(addr)
        electors2.at[index, 'Address1'] = new_addr1
        if new_addr2:
            # Shift down Address2..Address6 to make room
            for shift in reversed(range(2, 7)):
                electors2.at[index, f'Address{shift}'] = electors2.at[index, f'Address{shift-1}']
            electors2.at[index, 'Address2'] = new_addr2

        # --- Extract AddressNumber and StreetName ---
        # (Your existing regex logic for Addno1, Addno2, prefix, street)
        # ... [Keep all of your regex & address parsing logic here exactly as before]

        # --- Update Lat/Long if missing ---
        try:
            if math.isnan(elector['Lat']):
                if str(elector.Postcode) != "?":
                    url = f"http://api.getthedata.com/postcode/{str(elector.Postcode).replace(' ','+')}"
                    response = requests.get(url)
                    if response.status_code == 200:
                        latlong = json.loads(response.content)
                        if latlong.get('match') and 'data' in latlong:
                            electors2.at[index, "Lat"] = float(latlong['data']['latitude'])
                            electors2.at[index, "Long"] = float(latlong['data']['longitude'])
                            RunningVals2['Last_Lat'] = float(latlong['data']['latitude'])
                            RunningVals2['Last_Long'] = float(latlong['data']['longitude'])
                        else:
                            electors2.at[index, "Lat"] = RunningVals2['Last_Lat']
                            electors2.at[index, "Long"] = RunningVals2['Last_Long']
                    else:
                        electors2.at[index, "Lat"] = RunningVals2['Last_Lat']
                        electors2.at[index, "Long"] = RunningVals2['Last_Long']
            # Update running mean
            RunningVals2['Mean_Lat'] = statistics.mean([RunningVals2['Mean_Lat'], electors2.at[index, "Lat"]])
            RunningVals2['Mean_Long'] = statistics.mean([RunningVals2['Mean_Long'], electors2.at[index, "Long"]])
        except Exception as e:
            print(f"❌ Exception at index {index}, postcode {elector.Postcode}: {e}")
            electors2.at[index, "Lat"] = RunningVals2['Last_Lat']
            electors2.at[index, "Long"] = RunningVals2['Last_Long']

    # --- Stage complete ---
    progress['percent'] = round(100 * (accumulated_percent_before + stage_fraction), 2)
    progress['status'] = 'norming'
    progress['message'] = 'Address normalisation complete.'

    return electors2

def split_after_4alpha_and_comma(addr):
    if not isinstance(addr, str):
        return addr, None
    match = re.search(r'([A-Za-z]{4}),', addr)
    if match:
        split_index = match.end()
        part1 = addr[:split_index - 1].strip()
        part2 = addr[split_index:].strip()
        return part1, part2
    return addr, None


def NormaliseAddress(RunningVals2, Lookups, ImportFilename, df, progress):
    import math, requests, json, statistics
    import numpy as np
    import pandas as pd
    from state import update_progress

    df = DFpostcodetoDF(df)

    # Ensure Address2..6 exist
    for col in ['Address2','Address3','Address4','Address5','Address6']:
        df[col] = df.get(col, "")

    df['Postcode'] = df['Postcode'].astype(str).str.strip().replace(['','nan','NaN','None'], np.nan)
    df.dropna(subset=['Postcode'], inplace=True)

    electors2 = df.merge(Lookups['LatLong'], how='left', on='Postcode')
    electors2 = electors2.merge(Lookups['Elevation'], how='left', on='Postcode')

    # Setup fallback running values
    RunningVals2.setdefault('Last_Lat', 51.240299)
    RunningVals2.setdefault('Last_Long', -0.562301)
    RunningVals2.setdefault('Mean_Lat', 51.240299)
    RunningVals2.setdefault('Mean_Long', -0.562301)

    total_rows = len(electors2)

    # --- Stage: address_norm ---
    stage_name = 'address_norm'

    for idx, (_, elector) in enumerate(electors2.iterrows()):
        local_fraction = (idx + 1) / total_rows
        update_progress(progress, stage_name, local_fraction,
                        f"Normalising addresses ({idx+1}/{total_rows})")

        # --- Split Address1 if needed ---
        addr = str(elector["Address1"])
        new_addr1, new_addr2 = split_after_4alpha_and_comma(addr)
        electors2.at[_, 'Address1'] = new_addr1
        if new_addr2:
            # Shift down Address2..Address6 to make room
            for shift in reversed(range(2, 7)):
                electors2.at[_, f'Address{shift}'] = electors2.at[_, f'Address{shift-1}']
            electors2.at[_, 'Address2'] = new_addr2

        # --- Extract AddressNumber and StreetName ---
        # (Keep all your regex & address parsing logic here exactly as before)

        # --- Update Lat/Long if missing ---
        try:
            if math.isnan(elector['Lat']):
                if str(elector.Postcode) != "?":
                    url = f"http://api.getthedata.com/postcode/{str(elector.Postcode).replace(' ','+')}"
                    response = requests.get(url)
                    if response.status_code == 200:
                        latlong = json.loads(response.content)
                        if latlong.get('match') and 'data' in latlong:
                            electors2.at[_, "Lat"] = float(latlong['data']['latitude'])
                            electors2.at[_, "Long"] = float(latlong['data']['longitude'])
                            RunningVals2['Last_Lat'] = float(latlong['data']['latitude'])
                            RunningVals2['Last_Long'] = float(latlong['data']['longitude'])
                        else:
                            electors2.at[_, "Lat"] = RunningVals2['Last_Lat']
                            electors2.at[_, "Long"] = RunningVals2['Last_Long']
                    else:
                        electors2.at[_, "Lat"] = RunningVals2['Last_Lat']
                        electors2.at[_, "Long"] = RunningVals2['Last_Long']

            # Update running mean
            RunningVals2['Mean_Lat'] = statistics.mean([RunningVals2['Mean_Lat'], electors2.at[_, "Lat"]])
            RunningVals2['Mean_Long'] = statistics.mean([RunningVals2['Mean_Long'], electors2.at[_, "Long"]])


        except Exception as e:
            print(f"❌ Exception at index {idx}, postcode {elector.Postcode}: {e}")
            electors2.at[_, "Lat"] = RunningVals2['Last_Lat']
            electors2.at[_, "Long"] = RunningVals2['Last_Long']

    # Stage complete
    update_progress(progress, stage_name, 1.0, "Address normalisation complete")

    return electors2

def normz(progress, RunningVals1, Lookups, stream, ImportFilename, dfx, autofix, purpose):
    import os
    import pandas as pd
    from state import update_progress

    print(f"____________inside normz_________ {ImportFilename}")
    os.chdir(config.workdirectories['workdir'])

    # ---------------------------------------------
    # Setup
    DQstats = pd.DataFrame(columns=['Election','File','Field','P0', 'P1', 'P2', 'P3'])
    electors100 = dfx.copy()
    if 'Tags' not in electors100.columns:
        electors100['Tags'] = ""
    electors100['Tags'] = electors100['Tags'].fillna("").astype(str)

    # =========================================================
    # STAGE 1: normz  (weight = 0.1)
    # =========================================================

    update_progress(progress, "normz", 0.0, f"Checking raw fields in {ImportFilename}")

    # --- Raw field check ---
    incols = list(electors100.columns)
    Outcols = pd.read_excel(GENESYS_FILE).columns

    for y in set(Outcols) & set(incols):
        DQstats.loc[list(Outcols).index(y), 'P0'] = 1

    update_progress(progress, "normz", 0.33, "Raw field check complete")

    if autofix == 0:
        update_progress(progress, "normz", 1.0, "Normz complete")
        return [electors100, DQstats]

    # --- Column renaming ---
    INCOLS = [
        x.upper().replace("ELECTOR","").replace("PROPERTY","")
        .replace("REGISTERED","").replace("QUALIFYING","")
        .replace(" ","").replace("_","")
        for x in incols
    ]

    COLNORM = {
        "NUMBERSUFFIX": "Suffix", "SUFFIX": "Suffix",
        "FIRSTNAME":"Firstname", "FORENAME":"Firstname",
        "SURNAME":"Surname", "SECONDNAME":"Surname",
        "INITS":"Initials", "INITIALS":"Initials",
        "MIDDLENAME":"Initials",
        "POSTCODE":"Postcode",
        "NUMBERPREFIX":"PD", "PD":"PD",
        "NUMBER":"X",
        "SHORTNUMBER":"ENOS",
        "ROLLNO":"ENO", "ENO":"ENO",
        "ADDRESS1":"Address1","ADDRESS2":"Address2",
        "ADDRESS3":"Address3","ADDRESS4":"Address4",
        "ADDRESS5":"Address5","ADDRESS6":"Address6",
        "MARKERS":"Markers","DOB":"DOB",
        "TITLE":"Title","ADDRESSNUMBER":"AddressNumber",
        "AV":"AV","ELEVATION":"Elevation",
        "ADDRESSPREFIX":"AddressPrefix",
        "LAT":"Lat","LONG":"Long",
        "RNO":"RNO","ENOP":"ENOP","ENOT":"ENOT",
        "FULLNAME":"ElectorName",
        "ELECTORNAME":"ElectorName",
        "NAME":"ElectorName",
        "STREETNAME":"StreetName"
    }

    Incolstuple = [
        (incols[INCOLS.index(x)], COLNORM[x])
        for x in set(INCOLS) & set(COLNORM.keys())
    ]

    for a, b in Incolstuple:
        electors100.rename(columns={a: b}, inplace=True)

    update_progress(progress, "normz", 0.66, "Renaming columns")

    if autofix == 1:
        update_progress(progress, "normz", 1.0, "Normz complete")
        return [electors100, DQstats]

    # --- ENO + Name normalisation ---
    electors100 = normalise_eno_column(electors100)
    electors100 = NormaliseName(electors100)
    electors100.reset_index(drop=True, inplace=True)

    update_progress(progress, "normz", 1.0, "Name & ENO normalisation complete")

    if autofix == 2:
        return [electors100, DQstats]

    # =========================================================
    # STAGE 2: address_norm (weight = 0.4)
    # =========================================================

    update_progress(progress, "address_norm", 0.0, "Starting address normalisation")

    if purpose in ['delta', 'main']:

        # Let NormaliseAddress call update_progress internally
        electors2 = NormaliseAddress(
            RunningVals1,
            Lookups,
            ImportFilename,
            electors100,
            progress  # pass progress only
        )

    elif purpose == 'avi':
        electors2 = pd.DataFrame(electors100, columns=[
            'Election','Purpose','RNO','Tags','PD','Firstname',
            'Surname','ElectorName','ENOP','ENOT','Suffix','ENO','AV'
        ])

    update_progress(progress, "address_norm", 1.0, "Address normalisation complete")

    # ---------------------------------------------
    electors2['Tags'] = electors2['Tags'].fillna("").astype(str)

    return [electors2, DQstats]

if __name__ == '__main__':
    # This doesn't run on import
    # It only runs when the module is run directly
    normz()
