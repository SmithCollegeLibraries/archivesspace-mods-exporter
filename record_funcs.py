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


logging.basicConfig(level=logging.INFO)

def getModsFileName(digital_object):
    ' Returns file name in format islandora_NUMBER_MODS '

    logging.info('Returning file name for %s in format: islandora_NUMBER_MODS' % digital_object['digital_object_id'])
    uri = digital_object['file_versions'][0]['file_uri']
    split_uri = uri.split('/')
    islandora_pid = split_uri[-1]
    formatted_islandora_pid = islandora_pid.replace(':', '_')
    mods_file_name = formatted_islandora_pid + '_MODS'

    return mods_file_name


def getSubjects(archival_object):
    ' Returns list of subjects for an Archival Object '
    ' Only looking at Archival Object level -- NOT getting them from the hierarchy because all YWCA AOs with Digital Objects have subjects at the AO level '
    
    logging.info('Retrieving Subject list from %s' % archival_object['uri'])
    sub_list = []
    subjects = archival_object['subjects']
    for subject in subjects:
        sub = subject['ref']
        sub_rec = aspace.get(sub)
        sub_list.append(sub_rec)

    return sub_list


def cleanSubjects(sub_list):
    ' Adds full URL address to authority ids of any subjects with authority ids that are not full URLs ' 
    
    logging.info('Adding full URLs to Subject authority ids if needed')
    for sub in sub_list:
        logging.info('Checking %s for authority id cleaning' % sub['title'])
        if 'authority_id' in sub.keys():
            if sub['source'] == 'tgn' and '.edu' not in sub['authority_id']:
                sub['authority_id'] = 'http://vocab.getty.edu/tgn/' + sub['authority_id']
            elif sub['source'] == 'lcsh' and '.gov' not in sub['authority_id']:
                sub['authority_id'] = 'http://id.loc.gov/authorities/' + sub['authority_id']
            else:
                sub['authority_id'] = sub['authority_id']

    return sub_list  


def getResource(archival_object):
    'Get the Resource Record of a given Archival Object'

    logging.info('Retrieving Resource of Archival Object %s' % archival_object['uri'])
    resource_uri = archival_object['resource']['ref']
    resource = aspace.get(resource_uri)
    return resource 


def getNotesTree(archival_object):
    ' Returns a list of tuples of all the notes from an Archival Object heirarchy '
    
    logging.info('Returning list of tuples of all notes from Archival Object %s heirarchy' % archival_object['uri'])
    note_tups = []
    if 'notes' in archival_object.keys():
        notes = archival_object['notes']
        for note in notes:
            logging.info('Retrieving available notes from %s' % archival_object['uri'])
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
                    logging.info('Retrieving available notes from parent of %s' % archival_object['uri'])
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
                        logging.info('Retrieving available notes from grandparent of %s' % archival_object['uri'])
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
            logging.info('Retrieving available notes from the Resource of %s' % archival_object['uri'])
            if 'content' in note.keys():
                tup = (note['type'], note['content'])
                note_tups.append(tup)
            else:
                tup = (note['type'], note['subnotes'])
                note_tups.append(tup)

    return note_tups


def getNotesByType(note_tups, notetype):
    ' Returns the dictionary for a specified note type; works in conjunction with getNotesTree '
    
    logging.info('Retrieving notes by type %s from list of note tuples generated in getNotesTree' % notetype)
    for note in note_tups:
        logging.info('Iterating over list of notes to retrieve %s type notes if they exist' % notetype)
        if note[0] == notetype:
            return note[1]


def getSeries(resource_num):
    ' Returns first level down children of given resource '

    logging.info('Retrieving Series level children of Resource %s' % resource_num)
    resource_num = str(resource_num)
    series_lst = []

    record = aspace.get('/repositories/2/resources/' + resource_num + '/tree')

    if record['children']:
        for child in record['children']:
            logging.info('Adding each first level child of Resource %s to a list' % resource_num)
            series_lst.append(child)

    return series_lst


def getChildUris(series):  # Could probably be reworked
    ' Returns list of child URIs for the child of a parent resource '
    ' Assumes searching through a single series in a record group '

    logging.info('Retrieving URIs for each child of Series %s passed' % series)
    child_uris = []  # Starting list to append to
    children = series['children']  # Children of the series, which is itself the child of a record group

    series_uri = series['record_uri']
    child_uris.append(series_uri)

    for teen in children:
        logging.info('Checking for children first level down')
        teen_uri = teen['record_uri']
        child_uris.append(teen_uri)
        if teen['children']:
            for tween in teen['children']:
                logging.info('Checking for children second level down')
                tween_uri = tween['record_uri']
                child_uris.append(tween_uri)
                if tween['children']:
                    for kid in tween['children']:
                        logging.info('Checking for children third level down')
                        kid_uri = kid['record_uri']
                        child_uris.append(kid_uri)
                        if kid['children']:
                            for toddler in kid['children']:
                                logging.info('Checking for children fourth level down')
                                toddler_uri = toddler['record_uri']
                                child_uris.append(toddler_uri)
                                if toddler['children']:
                                    for infant in toddler['children']:
                                        logging.info('Checking for children fifth level down')
                                        infant_uri = infant['record_uri']
                                        child_uris.append(infant_uri)
                                        if infant['children']:
                                            for baby in infant['children']:
                                                logging.info('Checking for children sixth level down')
                                                baby_uri = baby['record_uri']
                                                child_uris.append(baby_uri)
                                                if baby['children']:
                                                    for fetus in baby['children']:
                                                        logging.info('Checking for children seventh level down')
                                                        fetus_uri = fetus['record_uri']
                                                        child_uris.append(fetus_uri)

    return child_uris


def getAllResourceUris(resource_num):
    ' Calls getSeries and getChildUris to return all the Archival Object URIs for a resource '
    
    logging.info('Calling getSeries and getChildUris for Resource %s' % resource_num)
    hierarchy = getSeries(resource_num)
    uri_lst = []
    for level in hierarchy:
        logging.info('Adding all Archival Object URIs for Resource to list')
        uri_lst.extend(getChildUris(level))

    return uri_lst


def getDigitalObjectUris(ao_uri_list):
    ' Returns list of Digital Object uris '

    logging.info('Retrieving Digital Object URIs from list of Archival Object URIs')
    do_list = []

    if len(ao_uri_list) > 0:
        for uri in ao_uri_list:
            logging.info('Checking if Archival Object %s has Digital Object instance' % uri)
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

