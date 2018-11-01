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
argparser.add_argument("outputpath", help="File path for record output")
argparser.add_argument("SERVERCFG", nargs="?", default="DEFAULT", help="Name of the server configuration section e.g. 'production' or 'testing'. Edit archivesspace.cfg to add a server configuration section. If no configuration is specified, the default settings will be used host=localhost user=admin pass=admin.")
cliArguments = argparser.parse_args()

aspace = archivesspace.ArchivesSpace()
aspace.setServerCfg(CONFIGFILE, section=cliArguments.SERVERCFG)
aspace.connect()

##-------------------------------- ##

# test = aspace.get('/repositories/2/archival_objects/104905')

def getSubjects(archival_object):
    ' Returns list of subjects for an Archival Object '
    ' Only looking at Archival Object level -- NOT getting them from the hierarchy because all YWCA AOs with Digital Objects have subjects at the AO level '
    
    sub_list = []
    subjects = archival_object['subjects']
    for subject in subjects:
        sub = subject['ref']
        sub_rec = aspace.get(sub)
        sub_list.append(sub_rec)

    return sub_list


def cleanSubjects(sub_list):
    ' Adds full URL address to authority ids of any subjects with authority ids that are not full URLs ' 
    for sub in sub_list:
        if 'authority_id' in sub.keys():
            if sub['source'] == 'tgn' and '.edu' not in sub['authority_id']:
                sub['authority_id'] = 'http://vocab.getty.edu/tgn/' + sub['authority_id']
            elif sub['source'] == 'lcsh' and '.gov' not in sub['authority_id']:
                sub['authority_id'] = 'http://id.loc.gov/authorities/' + sub['authority_id']
            else:
                sub['authority_id'] = sub['authority_id']

    return sub_list   


def getNotesTree(archival_object):
    ' Returns a list of tuples of all the notes from an Archival Object heirarchy '
    
    note_tups = []
    if 'notes' in archival_object.keys():
        notes = archival_object['notes']
        for note in notes:
            if 'content' in note.keys():
                tup = (note['type'], note['content'])
                note_tups.append(tup)
            else:
                tup = (note['type'], note['subnotes'])
                note_tups.append(tup)

        if 'parent' in archival_object.keys():
            parent = archival_object['parent']['ref']
            parent_record = aspace.get(parent)
            if 'notes' in parent_record.keys():
                notes = parent_record['notes']
                for note in notes:
                    if 'content' in note.keys():
                        tup = (note['type'], note['content'])
                        note_tups.append(tup)
                    else:
                        tup = (note['type'], note['subnotes'])
                        note_tups.append(tup)

            if 'parent' in parent_record.keys():
                grandparent = parent_record['parent']['ref']
                grandparent_record = aspace.get(grandparent)
                if 'notes' in grandparent_record.keys():
                    notes = grandparent_record['notes']
                    for note in notes:
                        if 'content' in note.keys():
                            tup = (note['type'], note['content'])
                            note_tups.append(tup)
                        else:
                            tup = (note['type'], note['subnotes']) 
                            note_tups.append(tup)  

    resource = getResource(archival_object)
    if 'notes' in resource.keys():
        notes = resource['notes']
        for note in notes:
            if 'content' in note.keys():
                tup = (note['type'], note['content'])
                note_tups.append(tup)
            else:
                tup = (note['type'], note['subnotes'])
                note_tups.append(tup)

    return note_tups


def getNotesByType(note_tups, notetype):
    ' Returns the dictionary for a specified note type; works in conjunction with getNotesTree '
    
    for note in note_tups:
        if note[0] == notetype:
            return note[1]


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
    ' Calls getSeries and getChildUris to return all the Archival Object URIs for a resource '
    
    hierarchy = getSeries(resource_num)
    uri_lst = []
    for level in hierarchy:
        uri_lst.extend(getChildUris(level))

    return uri_lst


def getDigitalObjectUris(ao_uri_list):
    ' Returns list of Digital Object uris '

    do_list = []

    if len(ao_uri_list) > 0:
        for uri in ao_uri_list:
            archival_object = aspace.get(uri)
            if 'instances' in archival_object.keys():
                for instance in archival_object['instances']:
                    if 'digital_object' in instance.keys():
                        do_list.append(instance['digital_object']['ref'])
            else:
                exit(1)

    else:
        exit(1)

    return do_list


def getSlice(a_list, num=5):  # Why is this useful again?
    ' Returns select amount of the list to a new list '
    
    piece = a_list[:num]

    lst = []
    for bite in piece:
        lst.append(bite)

    return lst
