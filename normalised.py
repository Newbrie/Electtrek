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

def normz(stream,ImportFilename,dfx,autofix,purpose):
    print ("____________inside normz_________", ImportFilename)
    templdir = config.workdirectories['templdir']
    workdir = config.workdirectories['workdir']
    testdir = config.workdirectories['testdir']
    bounddir = config.workdirectories['bounddir']
    datadir = config.workdirectories['datadir']
    os.chdir(workdir)
    os.chdir(workdir)
    Env1 = sys.base_prefix
    Mean_Lat = 51.240299
    Mean_Long = -0.562301

    def NormaliseName(df):
        df = df.copy()

        # Split ElectorName into components if ElectorName exists
        def split_name(name):
            parts = str(name).split()
            if len(parts) < 2:
                return pd.Series([None, None, None])
            firstname = parts[0]
            surname = parts[-1]
            initials = ' '.join(parts[1:-1]) if len(parts) > 2 else None
            return pd.Series([firstname, initials, surname])

        # Always try to split ElectorName
        name_parts = df['ElectorName'].apply(split_name)
        name_parts.columns = ['split_firstname', 'split_initials', 'split_surname']

        # Fill missing name parts only
        for col, split_col in zip(['Firstname', 'Initials', 'Surname'],
                                  ['split_firstname', 'split_initials', 'split_surname']):
            df[col] = df[col].fillna(name_parts[split_col])

        # Always try to construct ElectorName if any component is missing or ElectorName is missing
        def join_name(row):
            if pd.notnull(row['Firstname']) and pd.notnull(row['Surname']):
                parts = [row['Firstname']]
                if pd.notnull(row['Initials']):
                    parts.append(row['Initials'])
                parts.append(row['Surname'])
                return ' '.join(parts)
            return row['ElectorName']  # fallback to original

        df['ElectorName'] = df.apply(join_name, axis=1)

        return df

    def DFtoDF (df):
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

    def normalise_id_columns(df):
    # Track which columns exist and which are missing
        required_cols = ['ENO', 'ENOT', 'ENOP', 'Suffix', 'PD']
        available = [col for col in required_cols if col in df.columns and df[col].notna().any()]

        # Early exit if we don't have enough to infer the rest
        if set(available).isdisjoint({'ENOT', 'ENOP', 'Suffix'}) or ('ENO' not in available and 'PD' not in available):
            return "Insufficient data"

        # Preserve original
        df = df.copy()

        # Derive Suffix from ENOP or ENOT
        if 'Suffix' not in df.columns:
            if 'ENOP' in df.columns:
                df['Suffix'] = df['ENOP'].str.extract(r'\.(.*)$')[0]
            else:
                df['Suffix'] = 0

        # Derive ENOT from ENOP or PD + ENO
        if 'ENOT' not in df.columns:
            if 'ENOP' in df.columns:
                df['ENOT'] = df['ENOP'].str.extract(r'(.*)\.')[0]
            elif 'PD' in df.columns and 'ENO' in df.columns:
                df['ENOT'] = df['PD'] + '-' + df['ENO'].astype("string")

        # Derive ENOP from ENOT and Suffix
        if 'ENOP' not in df.columns and 'ENOT' in df.columns and 'Suffix' in df.columns:
            df['ENOP'] = df['ENOT'] + '.' + df['Suffix'].astype("string")

        # Derive ENO from ENOT or ENOP
        if 'ENO' not in df.columns:
            if 'ENOT' in df.columns:
                df['ENO'] = df['ENOT'].str.extract(r'-(.*?)(?:\.|$)')[0]
            elif 'ENOP' in df.columns:
                df['ENO'] = df['ENOP'].str.extract(r'-(.*?)(?:\.|$)')[0]

        # Derive PD from ENOT or ENOP
        if 'PD' not in df.columns:
            if 'ENOT' in df.columns:
                df['PD'] = df['ENOT'].str.extract(r'^(.*?)-')[0]
            elif 'ENOP' in df.columns:
                df['PD'] = df['ENOP'].str.extract(r'^(.*?)-')[0]

        return df

    def reclassify_eno_column(df):
        """
        Classifies and renames the 'ENO' column into ENO, ENOT, or ENOP depending on its content pattern:
        - ENO: Just the base number (e.g. '123')
        - ENOT: Has a '-' but no '.' (e.g. 'AA1-123')
        - ENOP: Has both '-' and '.' (e.g. 'AA1-123.9')
        The function returns a DataFrame with the correctly named column.
        """
        df = df.copy()

        if 'X' not in df.columns:
            raise ValueError("Input DataFrame must have an 'X' column.")

        # Define patterns
        def classify(val):
            if pd.isna(val):
                return 'ENO'
            val = str(val)
            if '-' in val and '.' in val:
                return 'ENOP'
            elif '-' in val:
                return 'ENOT'
            else:
                return 'ENO'

        # Classify each row
        df['classification'] = df['X'].apply(classify)

        # Create new columns based on classification
        df['ENOP'] = df.apply(lambda x: x['X'] if x['classification'] == 'ENOP' else None, axis=1)
        df['ENOT'] = df.apply(lambda x: x['X'] if x['classification'] == 'ENOT' else None, axis=1)
        df['ENO_clean'] = df.apply(lambda x: x['X'] if x['classification'] == 'ENO' else None, axis=1)

        # Drop old column and classification marker
        df.drop(columns=['X', 'classification'], inplace=True)

        # Rename to final expected columns (fill only non-null ones)
        for col in ['ENO_clean', 'ENOT', 'ENOP']:
            if df[col].notna().any():
                df.rename(columns={col: col.replace('_clean', '')}, inplace=True)
            else:
                df.drop(columns=[col], inplace=True)

        return df

    electors0 = pd.DataFrame()
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

    electors0 = DFtoDF(dfx)
    electors100 = dfx

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
    incols = electors100.columns

    for y in list(set(Outcols) & set(electors100.columns)):
        DQstats.loc[Outcols.index(y),'P0'] = 1
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
    print(f"__________Debunked: {Incolstuple} ")

    DQstats.loc[Outcols.index('RNO'),'P1'] = 1
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
    electors100 = reclassify_eno_column(electors100)
    print ("_____ENO & NAME RECLASSIFICATION start: ", electors100.columns)
    electors100 = normalise_id_columns(electors100)
    electors100 = NormaliseName(electors100)
    electors100 = electors100.reset_index(drop=True)
    DQstats.loc[Outcols.index('RNO'),'P2'] = 1
    print ("_____ENO & NAME RECLASSIFICATION end: ", electors100.columns)
    for y in list(set(Outcols) & set(electors100.columns)):
        DQstats.loc[Outcols.index(y), 'P2'] = 1
    if autofix == 2:
        print(f"____Autofix = 2 , DQstats:{DQstats} at : {datetime.now()}")
        return [electors100,DQstats]
#pass 3 - how many required 'purpose-related columns can be calculated from existing columns, ie avi - AV, adds - new ID, Streetname,AddrNo, & main - Lat Long, StreetName, AddressPrefix, AddressNumber  etc
    if purpose == 'delta':
        electors2 = electors100[electors100['CreatedMonth'] > 0] # filter out all records with no Postcode
        print("____________DELTA file processing starting for : ",ImportFilename, electors2.columns )
    if purpose == 'main' or purpose == 'delta':
        Addno1 = ""
        Addno2 = ""
        Addno = ""
        count = 0
        dfx = pd.read_csv(bounddir+"/National_Statistics_Postcode_Lookup_UK_20241022.csv")
        df1 = dfx[['Postcode 1','Latitude','Longitude']]
        df1 = df1.rename(columns= {'Postcode 1': 'Postcode', 'Latitude': 'Lat','Longitude': 'Long'})
        electors10 = electors100.dropna(subset=['Postcode']) # filter out all records with no Postcode

        electors1 = electors10.merge(df1, how='left', on='Postcode' )
        electors1.to_csv("mergedlatlong.csv")
        df1 = pd.read_csv(bounddir+"/open_postcode_elevation.csv")
        df1.columns = ["Postcode","Elevation"]
        electors2 = electors10.merge(df1, how='left', on='Postcode' )
        print("___Postcode merged")
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
            electors2.loc[index,'RNO'] = index
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
            if DQstats.loc[Outcols.index('ElectorName'),'P2'] != 1:
                electors2.loc[index,'ElectorName'] = str(elector['Surname']) +" "+ str(elector['Firstname'])
            if DQstats.loc[Outcols.index('Firstname'),'P2'] != 1:
                wordlist = str(elector['ElectorName']).split()
                l = len(wordlist)
                electors2.loc[index,'Surname'] = str(wordlist[0])
                if l>1:
                    electors2.loc[index,'Firstname'] = str(wordlist[1])
                if l>2:
                    for i in range(l-2):
                        electors2.loc[index,'Initials'] = "".join(wordlist[i+2],)

                print("no PD:", elector)
            if DQstats.loc[Outcols.index('Firstname'),'P2'] != 1 :
                print("No Firstname:", elector)
          #  set up the address attributes
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
                electors2.loc[index,'Address_4'] = elector["Address6"]
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
                  electors2.loc[index,'Address_4'] = elector["Address6"]
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
                  electors2.loc[index,'Address_5'] = elector["Address6"]
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
                        electors2.loc[index,'Address_3'] = elector["Address6"]
                        print ("len110:", Addnolen, "ind10:", Addnoindex, "No:", Addno1, "No2:", Addno2, "Addr:", addr, "str:", street, "addr1:", elector["Address1"], "addr2:", elector["Address2"])
                    else:
                        electors2.loc[index,'Address_1'] = elector["Address3"]
                        electors2.loc[index,'Address_2'] = elector["Address4"]
                        electors2.loc[index,'Address_3'] = elector["Address5"]
                        electors2.loc[index,'Address_4'] = elector["Address6"]
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
                  else:
                      print("______Postcode Nomatch & GTD Response:", str(elector.Postcode), myResponse)
                      electors2.loc[index,"Lat"] = Mean_Lat
                      electors2.loc[index,"Long"] = Mean_Long
                  Mean_Lat = statistics.mean([Decimal(Mean_Lat), Decimal(electors2.loc[index,"Lat"])])
                  Mean_Long = statistics.mean([Decimal(Mean_Long), Decimal(electors2.loc[index,"Long"])])
                else:
                  electors2.loc[index,"Lat"] = Mean_Lat
                  electors2.loc[index,"Long"] = Mean_Long
                  print("______Postcode Error GTD Response:", str(elector.Postcode), myResponse.status_code)
                  Mean_Lat = statistics.mean([Decimal(Mean_Lat), Decimal(elector.Lat)])
                  Mean_Long = statistics.mean([Decimal(Mean_Long), Decimal(elector.Long)])
            else:
                Mean_Lat = statistics.mean([Decimal(Mean_Lat), Decimal(elector.Lat)])
                Mean_Long = statistics.mean([Decimal(Mean_Long), Decimal(elector.Long)])

            count = count + 1
            if count > 500: break
        print("____________MAIN file processing complete for : ",ImportFilename, electors2.columns )

    elif purpose == 'avi':
        electors2 = pd.DataFrame(electors100, columns=['ENOP','AV'])
        print("____________AVI file processing complete for : ",ImportFilename, electors2.columns )

    print("____________Normalisation_Complete________in ",ImportFilename )

    # pass 3 - how many required fieldnames can be derived by factoring and regrouping fields in the source file

    DQstats.loc[Outcols.index('RNO'),'P3'] = 1
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
