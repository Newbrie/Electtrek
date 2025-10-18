import os
workdirectories = {}
workdirectories['testdir'] = "/Users/newbrie/Documents/ReformUK/ElectoralRegisters/Test"
workdirectories['staticdir'] = "/Users/newbrie/Documents/ReformUK/GitHub/Electtrek"
workdirectories['workdir'] = "/Users/newbrie/Sites/"
workdirectories['datadir'] = "/Users/newbrie/Sites/INDATA"
workdirectories['templdir'] = "/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/templates"
workdirectories['bounddir'] = "/Users/newbrie/Documents/ReformUK/GitHub/Reference/Boundaries"
workdirectories['resultdir'] = "/Users/newbrie/Documents/ReformUK/GitHub/Reference/AreaIndicators/"
TABLE_FILE = os.path.join(workdirectories['workdir'],'static','data','stream_data.json')
OPTIONS_FILE = os.path.join(workdirectories['workdir'],'static','data','options.json')
ELECTIONS_FILE = os.path.join(workdirectories['workdir'],'static','data','Elections.json')
TREEPOLY_FILE = os.path.join(workdirectories['workdir'],'static','data','Treepolys.pkl')
GENESYS_FILE =  os.path.join(workdirectories['workdir'],'static','data','RuncornRegister.xlsx')
ELECTOR_FILE = os.path.join(workdirectories['workdir'],'static','data','allelectors.csv')
TREKNODE_FILE = os.path.join(workdirectories['workdir'],'static','data','Treknodes.pkl')
FULLPOLY_FILE = os.path.join(workdirectories['workdir'],'static','data','Fullpolys.pkl')
MARKER_FILE = os.path.join(workdirectories['workdir'],'static','data','Markers.json')
RESOURCE_FILE = os.path.join(workdirectories['workdir'],'static','data','Resources.json')
DEVURLS = { "prod" : "https://electtrek.com",
            "dev" : "http://127.0.0.1:5000" }
