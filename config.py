import os
from pathlib import Path
workdirectories = {}
workdirectories['testdir'] = "/Users/newbrie/Documents/ReformUK/ElectoralRegisters/Test"
workdirectories['staticdir'] = "/Users/newbrie/Documents/ReformUK/GitHub/Electtrek"
workdirectories['workdir'] = "/Users/newbrie/Sites/"
workdirectories['datadir'] = "/Users/newbrie/Sites/INDATA"
workdirectories['templdir'] = "/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/templates"
workdirectories['bounddir'] = "/Users/newbrie/Documents/ReformUK/GitHub/Reference/Boundaries"
workdirectories['resultdir'] = "/Users/newbrie/Documents/ReformUK/GitHub/Reference/AreaIndicators/"
GENESYS_FILE =  os.path.join(workdirectories['workdir'],'static','registers','RuncornRegister.xlsx')
LAST_RESULTS_FILE = os.path.join(workdirectories['workdir'],'static','registers','LastResults.json')
ELECTIONS_FILE = os.path.join(workdirectories['workdir'],'static','elections','Elections-DEMO.json')
TREEPOLY_FILE = os.path.join(workdirectories['workdir'],'static','nodes','Treepolys.pkl')
ELECTOR_FILE = Path(workdirectories['workdir']) /'static'/ 'registers' / 'allelectors.csv'
TREKNODE_FILE = Path(workdirectories['workdir']) /'static'/ 'nodes' / 'Treknodes.json'
FULLPOLY_FILE = os.path.join(workdirectories['workdir'],'static','nodes','Fullpolys.pkl')
TABLE_FILE = os.path.join(workdirectories['workdir'],'static','registers','stream_data.json')
RESOURCE_FILE = Path(workdirectories['workdir']) /'static'/ 'resources' / 'Resources.csv'
BASE_FILE = Path(workdirectories['workdir']) /'static'/ 'elections' / 'Elections-DEMO.json'
DEVURLS = { "prod" : "https://electtrek.com",
            "dev" : "http://127.0.0.1:5000" }
