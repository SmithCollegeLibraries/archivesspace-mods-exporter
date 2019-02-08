import json
import os
from archivesspace import archivesspace
import pprint
from utilities import *
import argparse
import logging

## -----Connect to ASpace API----- ##

CONFIGFILE = "archivesspace.cfg"

argparser = argparse.ArgumentParser()
argparser.add_argument("jsonfile", help="Path to the JSON file containing the data with which to update the records.")
argparser.add_argument("SERVERCFG", nargs="?", default="DEFAULT", help="Name of the server configuration section e.g. 'production' or 'testing'. Edit archivesspace.cfg to add a server configuration section. If no configuration is specified, the default settings will be used host=localhost user=admin pass=admin.")
cliArguments = argparser.parse_args()

aspace = archivesspace.ArchivesSpace()
aspace.setServerCfg(CONFIGFILE, section=cliArguments.SERVERCFG)
aspace.connect()

##-------------------------------- ##

# Opens JSON file of SOLR query output for YWCA of the U.S.A. Photographic Records within Compass
# Transforms JSON into usable Python dictionary object
jsonfile = cliArguments.jsonfile
with open(jsonfile) as json_file:
    try:
    	json_data = json.load(json_file)
    except ValueError:
    	exit(1)

# Parses the dictionary and adds to a list the dictionaries within that dictionary of each Compass object
ywca_compass_objects = []
for ob_dict in json_data['response']['docs']:
	x = ob_dict
	ywca_compass_objects.append(x)

# Adds Compass root to PID
for ob in ywca_compass_objects:
	pid = ob['PID']
	ob['PID'] = 'https://compass.fivecolleges.edu/object/' + pid
# ywca_compass_objects now contains full Compass URIs for every Compass object

# Strips identifier to the numeric string needed for the API endpoint
# e.g. "smith_ssc_324_digital_object_289" to "289"
for ob in ywca_compass_objects:
	do_id = ob['mods_identifier_local_s']
	ob['mods_identifier_local_s'] = do_id.split('_')[-1]
# ywca_compass_objects['mods_identifier_local_s'] now contains only the ASpace object id necessary to run API calls 

##-------------------------------- ##

def updateDOwithCompassURI(ywca_compass_object):
	' Updates ArchivesSpace Digital Object records with their Compass URIs '
	
	# Gets the digital object id and the digital object record
	do_id = ywca_compass_object['mods_identifier_local_s']
	digital_object = aspace.get('/repositories/2/digital_objects/' + do_id)
	# Gets the Compass URI and builds the data dictionary necessary for the API call to update the digital object record
	compass_uri = ywca_compass_object['PID']
	uri_key = {'file_uri': compass_uri}
	digital_object['file_versions'].append(uri_key)
	# Updates digital object records with the file URIs
	response = aspace.post('/repositories/2/digital_objects/' + do_id, requestData=digital_object)

	return digital_object['digital_object_id']


## -- Function call -- ##

for compass_ob in ywca_compass_objects:
	print(updateDOwithCompassURI(compass_ob))
