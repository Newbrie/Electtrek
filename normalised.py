import re
import numpy as np
from decimal import Decimal
import pandas as pd
import os, sys, math, stat, json, statistics
import requests
from requests.auth import HTTPDigestAuth
import config
from datetime import datetime


print("Config in Normalised loaded successfully:", config.workdirectories)

def normz(RunningVals,Lookups, stream,ImportFilename,dfx,autofix,purpose):
    print ("____________inside normz_________", ImportFilename)
    templdir = config.workdirectories['templdir']
    workdir = config.workdirectories['workdir']
    testdir = config.workdirectories['testdir']
    bounddir = config.workdirectories['bounddir']
    datadir = config.workdirectories['datadir']
    os.chdir(workdir)
    os.chdir(workdir)


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

    def DFpostcodetoDF (df):
        vars = []
        vars_ = []
        varvalues = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]
        for d in df.columns:
          vars.append(d)
          vars_.append(d.replace(" ","_"))
        DF = pd.DataFrame()
        i = 0
        for varb in vars:
        # for every elector in the block extract the variable values into a DF dataframe
          for index, elector in df.iterrows():
            if varb == 'Postcode' and len(str(elector[varb])) == 8:
              varvalues[i].append(str(elector[varb]).replace(" ",""))
            else:
              varvalues[i].append(str(elector[varb]))
          DF.insert(i, vars_[i], varvalues[i])
          i=i+1
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
        Classifies a column based on regex pattern matching,
        requiring ENO and Suffix to be positive integers (no leading zeros).
        """
        series = series.dropna().astype(str).str.strip()

    #    patterns = {
    #        'ENOP': r'^[A-Za-z]+[0-9]*-[1-9][0-9]*[./][1-9][0-9]*$',  # PD-ENO.Suffix or PD-ENO/Suffix
    #        'ENOT': r'^[A-Za-z]+[0-9]*-[1-9][0-9]*$',                 # PD-ENO
    #        'ENO': r'^[1-9][0-9]*$',                                  # positive integer ENO only
    #        'PD': r'^[A-Za-z]+[0-9]*$',                               # alphanumeric PD
    #        'Suffix': r'^[1-9][0-9]*$',                               # positive integer suffix
    #    }

        patterns = {
            'ENOP': r'^[A-Za-z]+\d+-\d+[./]\d+$',
            'ENOT': r'^[A-Za-z]+\d+-\d+$',
            'ENO': r'^[1-9]\d*$',
            'PD': r'^[A-Za-z]+\d+$',
            'Suffix': r'^[1-9]\d*$',
        }
        best_label = 'Unknown'
        best_ratio = 0

        for label, pattern in patterns.items():
            match_ratio = series.str.match(pattern).mean()
            if match_ratio > best_ratio:
                best_ratio = match_ratio
                best_label = label

        return best_label if best_ratio >= 0.5 else 'Unknown'


    def normalise_eno_column(df):
#In the normalize_eno_column(df) logic:
#Only classify columns named X, PD, ENO, ENOT, ENOP, or Suffix (if they exist in the input df).
#Classify each column using regex based on:
#PD: alphanumeric prefix starting with letters and ending with digits
#ENO: integer > 0
#Suffix: integer > 0 or empty
#ENOT: PD-ENO
#ENOP: PD-ENO.Suffix or PD-ENO/Suffix (with / normalized to .)
#Rename columns according to classification only if classified as PD, ENO, or Suffix — and only if there is no existing PD, ENO, or Suffix column (i.e. these values are not present already).
#If a column is classified as ENOT or ENOP, use it to derive PD, ENO, Suffix, ENOT, and ENOP.
#Always normalize ENOP to use . instead of /.
#Keep X column unless it is renamed due to classification.
        df = df.copy()

        allowed_cols = {'X', 'PD', 'ENO', 'Suffix', 'ENOT', 'ENOP'}
        candidate_cols = [col for col in df.columns if col in allowed_cols]

        classification_map = {}
        for col in candidate_cols:
            label = classify_column(df[col])
            if label != 'Unknown':
                classification_map[col] = label

        # Rename columns based on classification (only if not already present)
        for col, label in classification_map.items():
            if label in {'PD', 'ENO', 'Suffix'} and label not in df.columns:
                df.rename(columns={col: label}, inplace=True)

        # Use ENOT/ENOP for parsing only if PD, ENO, and Suffix are not already present
        if 'PD' not in df.columns or 'ENO' not in df.columns:
            eno_source_col = None
            for col, label in classification_map.items():
                if label in {'ENOT', 'ENOP'}:
                    eno_source_col = col
                    break

            if eno_source_col:
                parse_series = df[eno_source_col].astype(str).str.strip().str.replace('/', '.', regex=False)

                df['PD'] = parse_series.str.extract(r'^([A-Za-z]+[0-9]+)-')[0]
                df['ENO'] = parse_series.str.extract(r'-([1-9][0-9]*)')[0]
                df['Suffix'] = parse_series.str.extract(r'\.(\d+)$')[0]

                # Clean types
                df['ENO'] = pd.to_numeric(df['ENO'], errors='coerce')
                df['Suffix'] = pd.to_numeric(df['Suffix'], errors='coerce')
                df.loc[df['ENO'] <= 0, 'ENO'] = None
                df.loc[df['Suffix'] == 0, 'Suffix'] = None

        # Derive ENOT and ENOP if PD and ENO exist
        df['ENOT'] = None
        valid_enot_mask = df['PD'].notna() & df['ENO'].notna()
        df.loc[valid_enot_mask, 'ENOT'] = (
            df.loc[valid_enot_mask, 'PD'] + '-' + df.loc[valid_enot_mask, 'ENO'].astype(int).astype(str)
        )

        df['ENOP'] = df['ENOT']
        valid_enop_mask = valid_enot_mask & df['Suffix'].notna()
        df.loc[valid_enop_mask, 'ENOP'] = (
            df.loc[valid_enop_mask, 'ENOT'] + '.' + df.loc[valid_enop_mask, 'Suffix'].astype(int).astype(str)
        )

        return df




    def add_row_number(df, column_name='RNO'):

        # Only add if RNO doesn't already exist
        if column_name not in df.columns:
            df[column_name] = range(1, len(df) + 1)

        # Reorder so RNO is the first column
        cols = [column_name] + [col for col in df.columns if col != column_name]
        return df


    def NormaliseAddress(RunningVals,Lookups,filename,df):

# fort convert postcodes to 8 charcter compressed format used in postcode files
        df = DFpostcodetoDF(df)
        Addno1 = ""
        Addno2 = ""
        Addno = ""
        count = 0
        electors10 = df.dropna(subset=['Postcode']) # filter out all records with no Postcode
        electors1 = electors10.merge(Lookups['LatLong'], how='left', on='Postcode' )
        electors1.to_csv(filename+"-latlongs.csv")
        electors2 = electors1.merge(Lookups['Elevation'], how='left', on='Postcode' )
        print("____Lat Long and Elevation merged")
        electors2['Lat'] = electors1['Lat'].astype(float)
        electors2['Long'] = electors1['Long'].astype(float)
        electors2['AddressNumber'] = ""
        electors2['AddressPrefix'] = ""
        electors2['StreetName'] = ""
        electors2['Address_1'] = ""
        electors2['Address_2'] = ""
        electors2['Address_3'] = ""
        electors2['Address_4'] = ""
        electors2['Address_5'] = ""
        electors2['Address_6'] = ""

        #  set up the council attribute

        for index, elector in electors2.iterrows():
        #            if DQstats.loc[Outcols.index('ENO'),'P2'] != 1 and DQstats.loc[Outcols.index('ENOT'),'P2'] == 1:
        #                enot = elector['ENOT'].split("-")
        #                electors2.loc[index,'PD'] =  enot[0]
        #                electors2.loc[index,'ENO'] = enot[1]
        #            if DQstats.loc[Outcols.index('ENO'),'P2'] != 1 and DQstats.loc[Outcols.index('ENOP'),'P2'] == 1:
        #                enop = elector['ENOP'].split("-")
        #                electors2.loc[index,'PD'] =  enop[0]
        #                electors2.loc[index,'ENO'] = enop[1].split(".")[0]
        #                electors2.loc[index,'Suffix'] = enop[1].split(".")[1]
        #            electors2.loc[index,'ENOP'] =  f"{elector['PD']}-{elector['ENO']}.{elector['Suffix']}"

          #  set up the address attributes
            if elector.ElectorName == "Fenton Luke":
                print("_____foundexception Luke Fenton", elector)
                raise Exception('Luke Fenton no lat long')

            xx = str(elector["Address1"])
            addr = xx.replace('"', '')
        #        Addno1 = re.search("\d+\s*[a-fA-F]?[,;\s]+", str(elector["Address1"]))
        #        Addno2 = re.search("\d+\s*[a-fA-F]?[,;\s]+", str(elector["Address2"]))
            Addno1 = re.search("(?:House|Flat|Apartment)?\s*((\d+[A-Za-z]?(?:\s*-\s*\d+[A-Za-z]?|\s*/\s*\d+[A-Za-z]?)?[\s,]*)+)", str(elector["Address1"]))
            Addno2 = re.search("(?:House|Flat|Apartment)?\s*((\d+[A-Za-z]?(?:\s*-\s*\d+[A-Za-z]?|\s*/\s*\d+[A-Za-z]?)?[\s,]*)+)", str(elector["Address2"]))
            prefix = str(elector["Address1"]).lstrip()
            print ("xx:", xx, "addr:", addr, "Addno1:", Addno1, "Addno2:", Addno2, "prefix:", prefix, "P1:",str(elector['Address2']),"P2:" ,str(elector['Postcode'])  )
            if Addno1 is None:
              addr = str(elector.Address2)
              if Addno2 is None :
                Addno = ""
                street = str(elector.Address2).lstrip()
                electors2.loc[index,'StreetName'] = street
                electors2.loc[index,'Address_1'] = elector["Address3"]
                electors2.loc[index,'Address_2'] = elector["Address4"]
                electors2.loc[index,'Address_3'] = elector["Address5"]
                electors2.loc[index,'Address_4'] = elector.get('Address6', None)
                print ("len00:", 0, "ind10:", 0, "No:", Addno, "Addr:", addr, "str:", street, "addr1:", elector["Address1"], "addr2:", elector["Address2"])
              else:
                Addnolen = len(Addno2.group())
                Addno = str(Addno2.group())
                Addnoindex = addr.index(Addno)
                addr = str(elector.Address2).lstrip()
                street = addr[Addnolen+Addnoindex:].rstrip().lstrip()
                electors2.loc[index,'Address_1'] = elector["Address2"]
                electors2.loc[index,'Address_2'] = elector["Address3"]
                electors2.loc[index,'Address_3'] = elector["Address4"]
                electors2.loc[index,'Address_4'] = elector["Address5"]
                print ("len01:", Addnolen, "ind10:", Addnoindex, "No:", Addno, "Addr:", addr, "str:", street, "addr1:", elector["Address1"], "addr2:", elector["Address2"])
                if street == "" or street is None:
                  street = str(elector.Address3).lstrip()
                  electors2.loc[index,'Address_1'] = elector["Address3"]
                  electors2.loc[index,'Address_2'] = elector["Address4"]
                  electors2.loc[index,'Address_3'] = elector["Address5"]
                  electors2.loc[index,'Address_4'] = elector.get('Address6', None)
                  print ("len010:", Addnolen, "ind10:", Addnoindex, "No:", Addno, "Addr:", addr, "str:", street, "addr1:", elector["Address1"], "addr2:", elector["Address2"])
            else:
              if Addno2 is None:
                Addnolen = len(Addno1.group())
                Addno = str(Addno1.group())
                Addnoindex = addr.index(Addno)
                street = addr[Addnolen+Addnoindex:].rstrip().lstrip()
                electors2.loc[index,'Address_1'] = elector["Address1"]
                electors2.loc[index,'Address_2'] = elector["Address2"]
                electors2.loc[index,'Address_3'] = elector["Address3"]
                electors2.loc[index,'Address_4'] = elector["Address4"]
                prefix = addr[:Addnoindex].rstrip().lstrip()
                print ("len10:", Addnolen, "ind10:", Addnoindex, "No:", Addno, "Addr:", addr, "str:", street, "addr1:", elector["Address1"], "addr2:", elector["Address2"])
                if street == "" or street is None:
                  street = elector.Address2.lstrip()
                  electors2.loc[index,'Address_1'] = elector["Address2"]
                  electors2.loc[index,'Address_2'] = elector["Address3"]
                  electors2.loc[index,'Address_3'] = elector["Address4"]
                  electors2.loc[index,'Address_4'] = elector["Address5"]
                  electors2.loc[index,'Address_5'] = elector.get('Address6', None)
                  print ("len100:", Addnolen, "ind2:", Addnoindex, "str:", street, "addr:", elector['Address_1'],"addr2:", elector['Address_2'])
              else:
                if re.sub(r"\s+", "", str(elector['Address2'])) == re.sub(r"\s+", "", str(elector['Postcode'])):
                    Addno2 = re.search("X","Y")
                    Addnolen = len(Addno1.group())
                    Addno = str(Addno1.group())
                    addr = str(elector["Address1"])
                    Addnoindex = addr.index(Addno)
                    prefix = addr[Addnoindex+Addnolen:].rstrip().lstrip()
                    electors2.loc[index,'Address_1'] = elector["Address1"]
                    electors2.loc[index,'Address_2'] = elector["Address2"]
                    electors2.loc[index,'Address_3'] = elector["Address3"]
                    electors2.loc[index,'Address_4'] = elector["Address4"]
                    print ("len101:", Addnolen, "ind2:", Addnoindex, "str:", street, "addr:", elector['Address_1'])
                else:
                    Addnolen = len(Addno1.group())
                    Addno = str(Addno1.group())
                    addr = str(elector["Address1"])
                    Addnoindex = addr.index(Addno)
                    prefix = addr[Addnoindex+Addnolen:].rstrip().lstrip()

                    Addno3 = str(Addno2.group().rstrip())
                    Addnolen = len(Addno2.group().rstrip())
                    xx = str(elector["Address2"])
                    addr = xx.replace('"', '')
                    Addnoindex = addr.index(Addno3)
                    street = addr[Addnolen+Addnoindex:].rstrip().lstrip()
                    if street is None or street == "":
                        street = str(elector["Address3"])
                        electors2.loc[index,'Address_1'] = elector["Address4"]
                        electors2.loc[index,'Address_2'] = elector["Address5"]
                        electors2.loc[index, 'Address_3'] = elector.get('Address6', None)
                        print ("len110:", Addnolen, "ind10:", Addnoindex, "No:", Addno1, "No2:", Addno2, "Addr:", addr, "str:", street, "addr1:", elector["Address1"], "addr2:", elector["Address2"])
                    else:
                        electors2.loc[index,'Address_1'] = elector["Address3"]
                        electors2.loc[index,'Address_2'] = elector["Address4"]
                        electors2.loc[index,'Address_3'] = elector["Address5"]
                        electors2.loc[index,'Address_4'] = elector.get('Address6', None)
                        print ("len111:", Addnolen, "ind10:", Addnoindex, "No:", Addno1, "No2:", Addno2, "Addr:", addr, "str:", street, "addr1:", elector["Address1"], "addr2:", elector["Address2"])
                    Addnolen1 = len(Addno1.group())
                    Addno1 = str(Addno1.group())
                    Addno = str(Addno1)+","+str(Addno3)
                    print ("len11:", Addnolen, "ind10:", Addnoindex, "No:", Addno1, "No2:", Addno2, "Addr:", addr, "str:", street, "addr1:", elector["Address1"], "addr2:", elector["Address2"])
            electors2.loc[index,'StreetName'] = street.replace(" & "," AND ").replace(r'[^A-Za-z0-9 ]+', '').replace("'","").replace(",","").replace(" ","_").upper()
            electors2.loc[index,'AddressNumber'] = Addno
            electors2.loc[index,'AddressPrefix'] = prefix
            if math.isnan(elector['Elevation'] or elector['Elevation'] is None):
                electors2.loc[index,'Elevation'] = float(0.0)
            else:
                electors2.loc[index,'Elevation'] = float(elector['Elevation'])
            if math.isnan(elector.Lat):
              if str(elector.Postcode) != "?":
                url = "http://api.getthedata.com/postcode/"+str(elector.Postcode).replace(" ","+")
              # It is a good practice not to hardcode the credentials. So ask the user to enter credentials at runtime
                myResponse = requests.get(url)
                print("retrieving postcode latlong",url)
                print (myResponse.status_code)
                print (myResponse.content)

            # For successful API call, response code will be 200 (OK)
                if(myResponse.status_code == 200):
            # Loading the response data into a dict variable
                  latlong = json.loads(myResponse.content)
                  if latlong['status'] == "match" :
                      electors2.loc[index,"Lat"] = latlong['data']['latitude']
                      electors2.loc[index,"Long"] = latlong['data']['longitude']
                      RunningVals['Last_Lat'] = latlong['data']['latitude']
                      RunningVals['Last_Long'] = latlong['data']['longitude']
                  else:
                      print("______Postcode Nomatch & GTD Response:", str(elector.Postcode), myResponse)
                      electors2.loc[index,"Lat"] = RunningVals['Last_Lat']
                      electors2.loc[index,"Long"] = RunningVals['Last_Long']
                  RunningVals['Mean_Lat'] = statistics.mean([Decimal(RunningVals['Mean_Lat']), Decimal(electors2.loc[index,"Lat"])])
                  RunningVals['Mean_Long'] = statistics.mean([Decimal(RunningVals['Mean_Long']), Decimal(electors2.loc[index,"Long"])])
                else:
                  electors2.loc[index,"Lat"] = RunningVals['Last_Lat']
                  electors2.loc[index,"Long"] = RunningVals['Last_Long']
                  print("______Postcode Error GTD Response:", str(elector.Postcode), myResponse.status_code)
                  RunningVals['Mean_Lat'] = statistics.mean([Decimal(RunningVals['Mean_Lat']), Decimal(elector.Lat)])
                  RunningVals['Mean_Long'] = statistics.mean([Decimal(RunningVals['Mean_Long']), Decimal(elector.Long)])
              else:
                electors2.loc[index,"Lat"] = RunningVals['Last_Lat']
                electors2.loc[index,"Long"] = RunningVals['Last_Long']
            else:
                RunningVals['Mean_Lat'] = statistics.mean([Decimal(RunningVals['Mean_Lat']), Decimal(elector.Lat)])
                RunningVals['Mean_Long'] = statistics.mean([Decimal(RunningVals['Mean_Long']), Decimal(elector.Long)])

            count = count + 1
            if count > 500: break
        return electors2


    electors10 = pd.DataFrame()
    DQstats = pd.DataFrame(columns=['Stream','File','Field','P0', 'P1', 'P2', 'P3'])


#AUTO DATA IMPORT
#1 - read in columns into a normalised list if columns and derive outcomes df
#2 - check the content of EVERY column matches the desired outcome type 	(need content checkers for each column type - eg Fname, Surname, initials, ENOP, ENO, ENOS, PD,
#3 - compare names with the required outcomes column list to identify all present and absent
#4 - fill all factor gaps first - row by row
#	eg fname, sname, initials, ENO, Suffix, Postcode, Address1-6
#5 - then fill any ‘multi-col value derived’ gaps second row by row
# 	eg ename, ENOP, ENOS, StreetName, AddressPrefix, Address_1-6, Lat, Long , Elevation
#6 - fill any ‘group row value derived’ columns third by
# 	eg Ward (needs a contains test of PD mean lat long), Con(needs a contains test of PD mean lat long), County(needs a contains test of PD mean lat long), Country(needs a contains test of PD mean lat long),

#  make two electors dataframes - one for compressed 7 char postcodes(electors0), the other for 8 char postcodes(electors10)


    electors100 = dfx
    print ("_____pass 0.1 start: ", dfx.columns)

    electors100 = add_row_number(electors100)
    print ("_____pass 0.2 start: ", electors100.columns)

    dfz = electors100[1:10]
    dfzmax = dfz.shape[0]
    print(dfz.columns," data rows: ", dfzmax )

    COLNORM = { "FIRSTNAME" : "Firstname" , "FORENAME" : "Firstname" ,"FIRST" : "Firstname" , "SURNAME" : "Surname", "SECONDNAME" : "Surname","INITS" :"Initials","INITIALS" : "Initials","MIDDLENAME" :"Initials","POSTCODE" : "Postcode", "NUMBERPREFIX" : "PD","PD" : "PD", "NUMBER":"X","SHORTNUMBER":"ENO","ROLLNO":"ENO","ENO":"ENO",
    "ADDRESS1":"Address1","ADDRESS2":"Address2","ADDRESS3":"Address3","ADDRESS4":"Address4","ADDRESS5":"Address5","ADDRESS6":"Address6","MARKERS":"Markers","DOB":"DOB",
    "NUMBERSUFFIX" : "Suffix","SUFFIX" : "Suffix","DISTRICTREF" : "PD", "TITLE" :"Title" , "ADDRESSNUMBER" :"AddressNumber","AVDESCRIPTION" : "AV", "AV" : "AV" ,"ELEVATION" : "Elevation" ,"ADDRESSPREFIX":"AddressPrefix", "LAT" : "Lat", "LONG" : "Long" ,"RNO" : "RNO" ,"ENOP" : "ENOP" ,"ENOT" : "ENOT" , "FULLNAME" :"ElectorName","ELECTORNAME" :"ElectorName","NAME" :"ElectorName", "STREETNAME" :"StreetName" }


    Outcomes = pd.read_excel(workdir+"/"+"RuncornRegister.xlsx")
    Outcols = Outcomes.columns.to_list()
    for i in range(len(Outcols)):
        DQstats.loc[i,'P0'] = 0
        DQstats.loc[i,'P1'] = 0
        DQstats.loc[i,'P2'] = 0
        DQstats.loc[i,'P3'] = 0
    print(f"___DQ Stats1",DQstats, Outcols)

    for z in Outcols :
        DQstats.loc[Outcols.index(z),'Stream'] = stream.upper()
        DQstats.loc[Outcols.index(z),'File'] = ImportFilename
        DQstats.loc[Outcols.index(z),'Field'] = z
    print(f"___DQ Stats2",DQstats, Outcols)

#pass 0 - how many required fieldnames are in the source file?

    incols = list(set(electors100.columns))

    for y in list(set(Outcols) & set(electors100.columns)):
        DQstats.loc[Outcols.index(y),'P0'] = 1
    electors100['Source_ID'] = ImportFilename
    electors100['Stream'] = stream
    electors100['Purpose'] = purpose
    print(f"___DQ Stats3",DQstats, electors100.columns)

    if autofix == 0:
        print(f"____Autofix = 0 , DQstats:{DQstats} at : {datetime.now()}")
        return [electors100,DQstats]
#        dfzres = extractfactors(dfz)
#        dfzres = checkENOP(dfz)
#        print("found ENO match in column: ", dfzres)

# pass 1 - how many required fieldnames can be derived by simply capitalising and debunking fields in the source file
    INCOLS = [x.upper().replace("ELECTOR","").replace("PROPERTY","").replace("REGISTERED","").replace("QUALIFYING","").replace(" ","").replace("_","") for x in incols]
    Incolstuple = [(incols[INCOLS.index(x)],COLNORM[x]) for x in list(set(INCOLS) & set(COLNORM.keys()))]
    print(f"__________Debunked: {Incolstuple} INCOLS{INCOLS} incols{incols} CONNORMKEYS {COLNORM.keys()}")

    for a,b in Incolstuple:
        electors100 = electors100.rename(columns= {a: b})
        print(f"___NRenamed from {a} to {b} ")

    electors100 = electors100.reset_index(drop=True)
    for y in list(set(Outcols) & set(electors100.columns)):
        DQstats.loc[Outcols.index(y), 'P1'] = 1
    if autofix == 1:
        print(f"____Autofix = 1 , DQstats:{DQstats} at : {datetime.now()}")
        return [electors100,DQstats]

#pass 2 - how many required required identity columns and name columns can be derived from existing columns, eg ENOP  etc
    print ("_____ENO & NAME RECLASSIFICATION start: ", electors100.columns)
    electors100 = normalise_eno_column(electors100)
    electors100 = NormaliseName(electors100)
    electors100 = electors100.reset_index(drop=True)

    print ("_____ENO & NAME RECLASSIFICATION end: ", electors100.columns)
    for y in list(set(Outcols) & set(electors100.columns)):
        DQstats.loc[Outcols.index(y), 'P2'] = 1
    if autofix == 2:
        print(f"____Autofix = 2 , DQstats:{DQstats} at : {datetime.now()}")
        return [electors100,DQstats]

#pass 3 - how many required 'purpose-related columns can be calculated from existing columns, ie avi - AV, adds - new ID, Streetname,AddrNo, & main - Lat Long, StreetName, AddressPrefix, AddressNumber  etc
    if purpose == 'delta':
        electors2 = NormaliseAddress(RunningVals,Lookups,ImportFilename,electors100)
        print(f"____________DELTA file {ImportFilename} contains {len(electors2)} records: " )
    elif purpose == 'main':
        electors2 = NormaliseAddress(RunningVals,Lookups,ImportFilename,electors100)
        print("____________MAIN file processing complete for : ",ImportFilename, electors2.columns )
    elif purpose == 'avi':
        # not processing addresses , just the elector identity and AV
        electors2 = pd.DataFrame(electors100, columns=['ENOP','ENOT','Suffix','ENO','AV'])
        print("____________AVI file processing complete for : ",ImportFilename, electors2.columns )
    print("____________Normalisation_Complete________in ",ImportFilename )

    for y in list(set(Outcols) & set(electors2.columns)):
        DQstats.loc[Outcols.index(y),'P3'] = 1
    if autofix == 3:
        print(f"____Autofix = 3 , DQstats:{DQstats} at : {datetime.now()}")
        return [electors2,DQstats]

    return [electors2,DQstats]


if __name__ == '__main__':
    # This doesn't run on import
    # It only runs when the module is run directly
    normz()
