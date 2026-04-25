import os
from pathlib import Path
workdirectories = {}
workdirectories['testdir'] = "/Users/newbrie/Documents/ReformUK/ElectoralRegisters/Test"
workdirectories['staticdir'] = "/Users/newbrie/Documents/ReformUK/GitHub/Electtrek"
workdirectories['workdir'] = "/Users/newbrie/Sites/"
workdirectories['resdir'] = "/Users/newbrie/Sites/static/resources"
workdirectories['datadir'] = "/Users/newbrie/Sites/INDATA"
workdirectories['templdir'] = "/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/templates"
workdirectories['bounddir'] = "/Users/newbrie/Documents/ReformUK/GitHub/Reference/Boundaries"
workdirectories['resultdir'] = "/Users/newbrie/Documents/ReformUK/GitHub/Reference/AreaIndicators/"
workdirectories['candidatedir'] = "/Users/newbrie/Documents/ReformUK/GitHub/Reference/Candidates/"

GENESYS_FILE =  os.path.join(workdirectories['workdir'],'static','registers','RuncornRegister.xlsx')
NATIONAL_DIVISION_FILE = os.path.join(workdirectories['bounddir'],'County_Electoral_Division_May_2023_Boundaries_EN_BFC_8030271120597595609.geojson')
LAST_RESULTS_FILE = os.path.join(workdirectories['workdir'],'static','registers','LastResults.json')
CANDIDATES_FILE = os.path.join(workdirectories['workdir'],'static','registers','Candidates.json')
ELECTIONS_FILE = os.path.join(workdirectories['workdir'],'static','elections','Elections-DEMO.json')
TREEPOLY_FILE = os.path.join(workdirectories['workdir'],'static','nodes','Treepolys.pkl')
ELECTOR_FILE = Path(workdirectories['workdir']) /'static'/ 'registers' / 'allelectors.csv'
TREKNODE_FILE = Path(workdirectories['workdir']) /'static'/ 'nodes' / 'Treknodes.json'
FULLPOLY_FILE = os.path.join(workdirectories['workdir'],'static','nodes','Fullpolys.pkl')
GEO_INDEX_FILE = Path(workdirectories['workdir']) /'static'/ 'nodes' / 'Geo_index.json'
TABLE_FILE = os.path.join(workdirectories['workdir'],'static','registers','stream_data.json')
RESOURCE_FILE = Path(workdirectories['workdir']) /'static'/ 'resources' / 'Resources.csv'
BASEX_FILE = Path(workdirectories['workdir']) /'static'/ 'elections' / 'Elections-DEMO.json'
POSTCODE_FILE = Path(workdirectories['bounddir']) /'NSPL_FEB_2026_UK.csv'
LOGO_FILE = Path(workdirectories['resdir']) /'logo.png'
DATA_FILE = Path(workdirectories['workdir']) / 'static' / 'registers' / 'baked_data.js'
DEVURLS = { "prod" : "https://electtrek.com",
            "dev" : "http://127.0.0.1:5000" }
