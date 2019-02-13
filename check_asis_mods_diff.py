description = """Scan directory of MODS files with Islandora CRUD formated names
and check them against the currently ingested datastreams in Islandora.

NOTE: If the datastreams to be compared have restricted access you will need to log
into Islandora and save your cookies to a file using a tool like this one:
https://chrome.google.com/webstore/detail/cookiestxt/njabckikapfpffapmjgojcnbfjonfjfg?hl=en
Then use --cookie-file= to point to the cookie file.
"""
import glob
import os
import re
import requests
import string
import argparse
import logging

import xmlisequal # custom, in the current dir

logging.basicConfig(level=logging.INFO)

argparser = argparse.ArgumentParser(description=description)
argparser.add_argument('inputdir', help="A directory full of CRUD name format files ready to be ingested.")
argparser.add_argument('islandora', help="e.g. compass-stage.fivecolleges.edu")
argparser.add_argument('--cookie-file', help="cookies.txt format cookie file saved from active session. Needed if the objects have restricted access.")
cliargs = argparser.parse_args()

METADATA_DIRECTORY = cliargs.inputdir
ENVIRONMENT = cliargs.islandora
COOKIEFILE = cliargs.cookie_file

def parseCookieFile(cookiefile):
    cookies = {}
    with open (cookiefile, 'r') as fp:
        for line in fp:
            if not re.match(r'^\#', line):
                lineFields = line.strip().split('\t')
                cookies[lineFields[5]] = lineFields[6]
    return cookies

def getDatastreamsInfo(searchPattern):
    datastreams = []
    for filepathname in glob.glob(searchPattern):
        filename = os.path.basename(filepathname)
        splitFilename = filename.split('_')
        namespace = splitFilename[0]
        pidnumber = splitFilename[1]
        datastreamName = splitFilename[2].split('.')[0]
        urlTemplate = string.Template("https://$environment/islandora/object/$namespace:$pidnumber/datastream/$datastream/download")
#        import pdb; pdb.set_trace()
        url = urlTemplate.substitute(
            environment = ENVIRONMENT,
            namespace = namespace,
            pidnumber = pidnumber,
            datastream = datastreamName,
        )
        datastreams.append({
            'filepathname': filepathname,
            'namespace': namespace,
            'pidnumber': pidnumber,
            'datastream': datastreamName,
            'url': url,
        })
    return datastreams

def getLocalContents(datastreams):
    for datastream in datastreams:
        with open(datastream['filepathname'], 'rb') as fp:
            datastream['contents_local'] = fp.read()
            # datastream['checksum_local'] = hashlib.sha1(datastream['contents_local'])
    return datastreams

def getRemoteContents(datastreams):
    for datastream in datastreams:
        logging.info(datastream['url'])
        # cookies = {
        #     SHIBSESSIONKEY: SHIBSESSIONVALUE,
        #     SESSIONKEY: SESSIONVALUE
        # }
        if COOKIEFILE:
            cookies = parseCookieFile(COOKIEFILE)
        else:
            cookies = {}
        httpResponse = requests.get(datastream['url'], cookies=cookies)
        if httpResponse.status_code == 200:
            # datastream['checksum_remote'] = hashlib.sha1(httpResponse.content)
            datastream['contents_remote'] = httpResponse.content
        else:
            logging.error("Failed to fetch remote datastream for %s because %s" % (datastream['url'], httpResponse.status_code))
            # datastream['checksum_remote'] = None
            datastream['contents_remote'] = None
    return datastreams

def getDifferences(datastreams):
    differences = []
    for datastream in datastreams:
        pid = datastream['namespace'] + ':' + datastream['pidnumber']
        if datastream['contents_local'] is not None and \
        datastream['contents_remote'] is not None:
            logging.debug("Local and remote contents exist")
            if not xmlisequal.xmlIsEqual(datastream['contents_remote'], datastream['contents_local'], pid=pid):
                logging.debug("Local and remote instances do not match for %s adding to list to be synced!" % datastream['filepathname'])
                differences.append(pid)
            else:
                logging.debug("Local and remote instances match. Skipping %s" % datastream['filepathname'])
        else:
            logging.error("Could not compare %s, missing local or remote data." % datastream['filepathname'])
    return differences

datastreams = getDatastreamsInfo(METADATA_DIRECTORY + '/*MODS.xml')
datastreams = getLocalContents(datastreams)
datastreams = getRemoteContents(datastreams)
differences = getDifferences(datastreams)

for difference in differences:
    print(difference)

#import pdb; pdb.set_trace()
