description = """Scan directory of MODS files with Islandora CRUD formated names and check them against the currently ingested datastreams in Islandora. Connects directly for Fedora to get MODS datastreams.

NOTE: to connect to Fedora config file called 'fedora.cfg' is required in the current directory. Copy 'example-fedora.cfg' to 'fedora.cfg' and edit to get started.
"""
import glob
import os
import requests
import string
import argparse
import logging
import configparser

import xmlisequal # custom, in the current dir

def getDatastreamsInfo(searchPattern):
    logging.debug("getDatastreamsInfo")
    filepathname_S = glob.glob(searchPattern)
    if len(filepathname_S) < 1:
        logging.error("No files found. Exiting.")
        exit(1)
    datastreams = []
    for filepathname in filepathname_S:
        filename = os.path.basename(filepathname)
        splitFilename = filename.split('_')
        namespace = splitFilename[0]
        pidnumber = splitFilename[1]
        datastreamName = splitFilename[2].split('.')[0]
        datastreams.append({
            'filepathname': filepathname,
            'namespace': namespace,
            'pidnumber': pidnumber,
            'datastream': datastreamName,
            # 'url': url,
        })
    return datastreams


def getLocalContents(datastreams):
    logging.debug("getLocalContents")
    for datastream in datastreams:
        with open(datastream['filepathname'], 'rb') as fp:
            datastream['contents_local'] = fp.read()
    return datastreams


def getRemoteContents(datastreams, fedoraConfig):
    logging.debug("getRemoteContents")

    def makeFedoraURL(namespace, pidnumber, datastreamName):
        urlTemplate = string.Template("https://$environment:$port/fedora/objects/$namespace:$pidnumber/datastreams/$datastream/content")
        url = urlTemplate.substitute(
            environment = fedoraConfig['ENVIRONMENT'],
            port = fedoraConfig['FEDORA_PORT'],
            namespace = namespace,
            pidnumber = pidnumber,
            datastream = datastreamName,
        )
        return url

    for datastream in datastreams:
        pid = datastream['namespace'] + ':' + datastream['pidnumber']
        logging.info(pid)
        url = makeFedoraURL(datastream['namespace'], datastream['pidnumber'], datastream['datastream'])
        username = fedoraConfig['FEDORA_USER']
        password = fedoraConfig['FEDORA_PASS']
        httpResponse = requests.get(url, auth=(username, password))
        if httpResponse.status_code == 200:
            datastream['contents_remote'] = httpResponse.content
        else:
            logging.error("Failed to fetch remote datastream for %s because %s" % (url, httpResponse.status_code))
            datastream['contents_remote'] = None
    return datastreams


def getDifferences(datastreams):
    logging.debug("getDifferences")
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


######## MAIN ########

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    argparser = argparse.ArgumentParser(description=description)
    argparser.add_argument('INPUTDIR', help="A directory full of CRUD name format files ready to be ingested.")
    argparser.add_argument('ENVIRONMENT', help="e.g. 'prod'")
    argparser.add_argument('--config-file', default='fedora.cfg', help="Location of config file. e.g. /home/me/fedora.cfg. Defaults to current directory.")
    cliargs = argparser.parse_args()

    configFile = cliargs.config_file

    configSection = cliargs.ENVIRONMENT

    try:
        config = configparser.ConfigParser()
        config.read_file(open(configFile), source=configFile)
        configData = config[configSection]
    except FileNotFoundError:
        print("Can't find a config file called %s" % configFile)
        exit(1)
    except KeyError as e:
        print("Config file %s doesn't contain that section %s" % (configFile, e))
        exit(1)

    fedoraConfig = {}

    try:
        fedoraConfig['ENVIRONMENT'] = configData['hostname']
        fedoraConfig['FEDORA_PORT'] = configData['port']
        fedoraConfig['FEDORA_USER'] = configData['username']
        fedoraConfig['FEDORA_PASS'] = configData['password']
    except KeyError as e:
        print("Config file section '%s' doesn't contain required property %s" % (configSection, e))
        exit(1)

    datastreams = getDatastreamsInfo(cliargs.INPUTDIR + '/*MODS.xml')
    datastreams = getLocalContents(datastreams)
    datastreams = getRemoteContents(datastreams, fedoraConfig)
    differences = getDifferences(datastreams)

    if len(differences) < 1:
        print("No differences found!")
    else:
        for difference in differences:
            print(difference)
