import re
import numpy as np
from decimal import Decimal
import pandas as pd
import os, sys, math, stat, json, statistics
import requests
from requests.auth import HTTPDigestAuth

normstats = {}



def normz(LocalFile, normstats):
    print ("____________inside normz_________")
    templdir = "/Users/newbrie/Documents/ReformUK/GitHub/electtrek/templates/"
    workdir = "/Users/newbrie/Sites"
    testdir = "/Users/newbrie/Documents/ReformUK/ElectoralRegisters/Test"
    bounddir = "/Users/newbrie/Documents/ReformUK/GitHub/electtrek/Boundaries/"
    os.chdir(workdir)
    Env1 = sys.base_prefix
    Mean_Lat = 51.240299
    Mean_Long = -0.562301

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

    def checkelectorName(data):
        pattern = r"(?P<Firstname>David|[A-Za-z'-]+)\s*(?P<Initials>(?:[A-Z](?:\s+[A-Z])*)*)\s*(?P<Surname>[A-Za-z'-]+)"
        datamax = data.shape[0]
        name_order = None

        for col in data.columns:
            i = 0
            for name in data[col].astype(str).values.tolist():
                match = re.match(pattern, name)
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

                    if i > 0.95*(datamax) :
                        return col

        return None

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


    electors0 = pd.DataFrame()
    electors10 = pd.DataFrame()
    Env1 = sys.base_prefix

    normstats['env'] = Env1
    if Env1.find("Orange")>0:
        from Orange.data import ContinuousVariable, StringVariable, DiscreteVariable, Domain
        from Orange.data import Table, Instance
        electors0 = TabletoDF(in_data, True)
        electors10 = TabletoDF(in_data, False)
        domain = in_data.domain
        addrNo = StringVariable("AddressNumber", )
        prefix = StringVariable("AddressPrefix", )
        street = StringVariable("StreetName", )
        addr1 = StringVariable("Address_1", )
        addr2 = StringVariable("Address_2", )
        addr3 = StringVariable("Address_3", )
        addr4 = StringVariable("Address_4", )
        addr5 = StringVariable("Address_5", )
        addr6 = StringVariable("Address_6", )
        RNO = ContinuousVariable("RNO", )
        Lat = ContinuousVariable("Lat", )
        Long = ContinuousVariable("Long", )
        elevation = ContinuousVariable("Elevation",)
        council = DiscreteVariable("Council", values=["Runcorn","Skipton","Northallerton","Thirsk","Kingston","Spelthorne","Mole_Valley", "Tandridge" , "Epsom_and_Ewell", "Elmbridge", "Guildford", "Surrey_Heath", "Woking", "Reigate_and_Banstead", "Waverley", "Runnymede", "East_Hampshire"])
        new_domain1 = Domain(attributes=domain.attributes + (council, elevation, Lat, Long, RNO), metas=domain.metas + (addr1, addr2, addr3, addr4, addr5, addr6, addrNo, prefix, street), class_vars=domain.class_vars)
    #  Normalise Address and Name Data using a new extended Orange domain
        OrangeE = in_data.transform(new_domain1)
        ImportFilename = str(OrangeE[0,'Source ID'])
    else:
        ImportFilename = str(LocalFile.filename)
        dfx = pd.read_excel(LocalFile)
#        dfx['RNO'] = dfx.index
        if 'AV' not in dfx.columns:
            dfx['AV'] = ""
#       if find ENOP pattern - separate into 2 or 3 new fields
#       else generate ENOP field from 3 seprate components (PD-ENO/Suffix)
#       if find ElectorName pattern - separate into firstname, initisla dn Surname
#       else generate ElectorName pattern from separate fields
#       address field pattern matching and processing
#       Lat Long , Elevation extraction from Postcode processing
#       exclude all other fields, like markers etc

      #  make two electors dataframes - one for compressed 7 char postcodes(electors0), the other for 8 char postcodes(electors10)
        electors0 = DFtoDF(dfx)
        electors10 = dfx
      # now normalise the postcodes and other address fields
        dfz = electors10[1:100]
        dfzmax = dfz.shape[0]
        print(ImportFilename," data rows: ", dfzmax )

        dfzres = checkelectorName(dfz)
        print("found ElectorName match in column: ", dfzres )

#        dfzres = checkENOP(dfz)
#        print("found ENO match in column: ", dfzres)

    raise Exception('XYZ')
    count = 0
    Addno1 = ""
    Addno2 = ""
    Addno = ""
    count = 0
    dfx = pd.read_csv(bounddir+"National_Statistics_Postcode_Lookup_UK_20241022.csv")
    df1 = dfx[['Postcode 1','Latitude','Longitude']]
    df1 = df1.rename(columns= {'Postcode 1': 'Postcode', 'Latitude': 'Lat','Longitude': 'Long'})
    electors1 = electors0.merge(df1, how='left', on='Postcode' )
    electors1.to_csv("mergedlatlong.csv")
    df1 = pd.read_csv(bounddir+"open_postcode_elevation.csv")
    df1.columns = ["Postcode","Elevation"]
    electors2 = electors10.merge(df1, how='left', on='Postcode' )
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
    Councilx = ""
    #  set up the council attribute
    if ImportFilename.find("Runcorn_and_Helsby") >= 0:
        Councilx = "Runcorn_and_Helsby"
    if ImportFilename.find("MoleValley") >= 0:
        Councilx = "Mole Valley"
    elif ImportFilename.find("Tandridge")>= 0:
        Councilx = "Tandridge"
    elif ImportFilename.find("Epsom") >= 0:
        Councilx = "Epsom_and_Ewell"
    elif ImportFilename.find("Elmbridge")>= 0:
        Councilx = "Elmbridge"
    elif ImportFilename.find("Guildford")>= 0:
        Councilx = "Guildford"
    elif ImportFilename.find("Heath") >= 0:
        Councilx = "Surrey_Heath"
    elif ImportFilename.find("Woking") >= 0:
        Councilx = "Woking"
    elif ImportFilename.find("Reigate") >= 0:
        Councilx = "Reigate_and_Banstead"
    elif ImportFilename.find("Waverley") >= 0:
        Councilx = "Waverley"
    elif ImportFilename.find("Runnymede") >= 0:
        Councilx = "Runnymede"
    elif ImportFilename.find("Hampshire") >= 0:
        Councilx = "East Hampshire"
    elif ImportFilename.find("Spelthorne") >= 0:
        Councilx = "Spelthorne"
    elif ImportFilename.find("Kingston") >= 0:
        Councilx = "Kingston"
    elif ImportFilename.find("Tendring") >= 0:
        Councilx = "Tendring"
    elif ImportFilename.find("Skipton") >= 0:
        Councilx = "Skipton"
    elif ImportFilename.find("Northallerton") >= 0:
        Councilx = "Northallerton"
    elif ImportFilename.find("Thirsk") >= 0:
        Councilx = "Thirsk"
    elif ImportFilename.find("Runcorn") >= 0:
        Councilx = "Runcorn"
    electors2['Council'] = Councilx
    normstats['source'] = ImportFilename
    normstats['columns'] = str(electors2.columns)
    normstats['council'] = Councilx
    for index, elector in electors2.iterrows():
        elector['RNO'] = index
        if elector['AV'] is None:
            elector['AV'] = ""
        if math.isnan(elector['Elevation'] or elector['Elevation'] is None):
            elector['Elevation'] = float(0.0)
        else:
            elector['Elevation'] = float(elector['Elevation'])
        if str(elector['ElectorName']) == "":
            electors2.loc[index,'ElectorName'] = str(elector['Surname']) +" "+ str(elector['Firstname'])
        if str(electors2.loc[index,'Firstname']) == "":
            wordlist = str(elector['ElectorName']).split()
            l = len(wordlist)
            electors2.loc[index,'Surname'] = str(wordlist[0])
            if l>1:
                electors2.loc[index,'Firstname'] = str(wordlist[1])
            if l>2:
                for i in range(l-2):
                    electors2.loc[index,'Initials'] = "".join(wordlist[i+2],)
        if str(elector["PD"]) is None:
            print("no PD:", elector)
        if elector['Council'] is None :
            print("No Council:", elector)
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
            street = elector.Address2.lstrip()
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
            addr = elector.Address2.lstrip()
            street = addr[Addnolen+Addnoindex:].rstrip().lstrip()
            electors2.loc[index,'Address_1'] = elector["Address2"]
            electors2.loc[index,'Address_2'] = elector["Address3"]
            electors2.loc[index,'Address_3'] = elector["Address4"]
            electors2.loc[index,'Address_4'] = elector["Address5"]
            print ("len01:", Addnolen, "ind10:", Addnoindex, "No:", Addno, "Addr:", addr, "str:", street, "addr1:", elector["Address1"], "addr2:", elector["Address2"])
            if street == "" or street is None:
              street = elector.Address3.lstrip()
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
        if Env1.find("Orange")>0:
          OrangeE[count]['Lat'] = elector["Lat"]
          OrangeE[count]['Long'] = elector["Long"]
          OrangeE[count]['StreetName'] = elector["StreetName"].replace(" & "," AND ").replace(r'[^A-Za-z0-9 ]+', '').replace("'","").replace(",","").replace(" ","_").upper()
          OrangeE[count]['AddressPrefix'] = elector["AddressPrefix"]
          OrangeE[count]['AddressNumber'] = elector['AddressNumber']
          OrangeE[count]['Council'] = elector['Council']
          OrangeE[count]['ElectorName'] = elector['ElectorName']
          OrangeE[count]['Elevation'] = elector['Elevation']
          OrangeE[count]['Firstname'] = elector['Firstname']
          OrangeE[count]['Surname'] = elector['Surname']
          OrangeE[count]['Initials'] = elector['Initials']
          OrangeE[count]['Address_1'] = elector['Address_1']
          OrangeE[count]['Address_2'] = elector['Address_2']
          OrangeE[count]['Address_3'] = elector['Address_3']
          OrangeE[count]['Address_4'] = elector['Address_4']
          OrangeE[count]['Address_5'] = elector['Address_5']
          OrangeE[count]['Address_6'] = elector['Address_6']
        count = count + 1
      #  if count > 500: break

    if Env1.find("Orange")>0:
        out_data = OrangeE
    else:
        electors2.to_csv(Councilx+"Register.csv")
        print("____________Normalisation_Complete________in ",Councilx, "Register.csv" )
    normstats['count'] = count
    normstats['Mean_Lat'] = Decimal(Mean_Lat)
    normstats['Mean_Long'] = Decimal(Mean_Long)

#    normstats['Mean_Long'] = np.mean(electors2['Long']).astype(float)
#    normstats['Mean_Lat'] = np.mean(electors2['Lat']).astype(float)
#    normstats['Mean_Elev'] = np.mean(electors2['Elevation']).astype(float)
    normstats['status'] = "NormComplete"
    return [electors2,normstats]


if __name__ == '__main__':
    # This doesn't run on import
    # It only runs when the module is run directly
    normz()
