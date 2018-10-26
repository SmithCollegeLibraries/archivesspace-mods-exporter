import json
import os
from archivesspace import archivesspace
import pprint
from utilities import *
import argparse
from record_funcs import *
import logging

## -----Connect to ASpace API----- ##

CONFIGFILE = "archivesspace.cfg"

argparser = argparse.ArgumentParser()
# argparser.add_argument("--outputpath", help="File path for record output")
argparser.add_argument("SERVERCFG", nargs="?", default="DEFAULT", help="Name of the server configuration section e.g. 'production' or 'testing'. Edit archivesspace.cfg to add a server configuration section. If no configuration is specified, the default settings will be used host=localhost user=admin pass=admin.")
cliArguments = argparser.parse_args()

aspace = archivesspace.ArchivesSpace()
aspace.setServerCfg(CONFIGFILE, section=cliArguments.SERVERCFG)
aspace.connect()

##-------------------------------- ##


def getSeries(resource_num):
    ' Returns first level down children of given resource '

    resource_num = str(resource_num)
    series_lst = []

    record = aspace.get('/repositories/2/resources/' + resource_num + '/tree')

    if record['children']:
        for child in record['children']:
            series_lst.append(child)

    return series_lst


def getChildUris(series):  # Could probably be reworked
    ' Returns list of child URIs for the child of a parent resource '
    ' Assumes searching through a single series in a record group '

    child_uris = []  # Starting list to append to
    children = series['children']  # Children of the series, which is itself the child of a record group

    series_uri = series['record_uri']
    child_uris.append(series_uri)

    for teen in children:
        teen_uri = teen['record_uri']
        child_uris.append(teen_uri)
        if teen['children']:
            for tween in teen['children']:
                tween_uri = tween['record_uri']
                child_uris.append(tween_uri)
                if tween['children']:
                    for kid in tween['children']:
                        kid_uri = kid['record_uri']
                        child_uris.append(kid_uri)
                        if kid['children']:
                            for toddler in kid['children']:
                                toddler_uri = toddler['record_uri']
                                child_uris.append(toddler_uri)
                                if toddler['children']:
                                    for infant in toddler['children']:
                                        infant_uri = infant['record_uri']
                                        child_uris.append(infant_uri)
                                        if infant['children']:
                                            for baby in infant['children']:
                                                baby_uri = baby['record_uri']
                                                child_uris.append(baby_uri)
                                                if baby['children']:
                                                    for fetus in baby['children']:
                                                        fetus_uri = fetus['record_uri']
                                                        child_uris.append(fetus_uri)

    return child_uris


def getAllResourceUris(resource_num):
    ' Call getSeries and getChildUris to return all the Archival Object URIs for a resource '
    hierarchy = getSeries(resource_num)
    uri_lst = []
    for level in hierarchy:
        uri_lst.extend(getChildUris(level))

    return uri_lst


def getDigitalObjectUris(ao_uri_list):
    ' Returns list of digital object uris '

    do_list = []

    if len(ao_uri_list) > 0:
        for uri in ao_uri_list:
            archival_object = aspace.get(uri)
            try:
                if 'instances' in archival_object.keys():
                    for instance in archival_object['instances']:
                        if 'digital_object' in instance.keys():
                            do_list.append(instance['digital_object']['ref'])
                else:
                    pass

            except KeyError:
                print("Key not found")
                exit(1)
    else:
        print("No digital objects found")
        exit(1)

    return do_list


def getDigitalObjectId(archival_object):
    'Get the Digital Object ID from an Archival Object'

    if len(archival_object['instances']) > 1:
        try:
            do_uri = archival_object['instances'][1]['digital_object']['ref']
            do = aspace.get(do_uri)
            digital_object_id = do['digital_object_id']
        except IndexError:
            do_uri = archival_object['instances'][2]['digital_object']['ref']
            do = aspace.get(do_uri)
            digital_object_id = do['digital_object_id']

    else:
        digital_object_id = ""

    return digital_object_id


test = aspace.get('/repositories/2/digital_objects/123')
print(test)


def getSlice(child_list, num=5):  # Why is this useful again?
    ' Returns select amount of the list to a new list '
    piece = child_list[:num]

    lst = []
    for bite in piece:
        lst.append(bite)

    return lst
