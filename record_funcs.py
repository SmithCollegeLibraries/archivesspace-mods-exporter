import json
import os
from archivesspace import archivesspace
import pprint
import argparse
import logging

## -----Connect to ASpace API----- ##

CONFIGFILE = "archivesspace.cfg"

argparser = argparse.ArgumentParser()
argparser.add_argument("outputpath", help="File path for record output.")
argparser.add_argument("SERVERCFG", nargs="?", default="DEFAULT", help="Name of the server configuration section e.g. 'production' or 'testing'. Edit archivesspace.cfg to add a server configuration section. If no configuration is specified, the default settings will be used host=localhost user=admin pass=admin.")
cliArguments = argparser.parse_args()

aspace = archivesspace.ArchivesSpace()
aspace.setServerCfg(CONFIGFILE, section=cliArguments.SERVERCFG)
aspace.connect()

##-------------------------------- ##

logging.basicConfig(level=logging.INFO)

def getModsFileName(digital_object):
    ' Returns file name in format islandora_NUMBER_MODS '

    logging.debug('Returning file name for %s in format: islandora_NUMBER_MODS' % digital_object['digital_object_id'])
    
    try:
        uri = digital_object['file_versions'][0]['file_uri']
        split_uri = uri.split('/')
        islandora_pid = split_uri[-1]
        formatted_islandora_pid = islandora_pid.replace(':', '_')
        mods_file_name = formatted_islandora_pid + '_MODS'
    except:
        mods_file_name = 'did_not_work'

    return mods_file_name


def getSubjects(archival_object):
    ' Returns list of subjects for an Archival Object '
    ' Only looking at Archival Object level -- NOT getting them from the hierarchy because all YWCA AOs with Digital Objects have subjects at the AO level '
    
    logging.debug('Retrieving Subject list from %s' % archival_object['uri'])
    sub_list = []
    subjects = archival_object['subjects']
    for subject in subjects:
        sub = subject['ref']
        sub_rec = aspace.get(sub)
        sub_list.append(sub_rec)

    for sub in sub_list:
        if 'authority_id' in sub.keys():
            if sub['source'] == 'lcsh':
                if 'loc.gov' not in sub['authority_id']:
                    sub['authority_id'] = 'http://id.loc.gov/authorities/subjects/' + sub['authority_id']
            elif sub['source'] == 'lcnaf':
                if 'loc.gov' not in sub['authority_id']:
                    sub['authority_id'] = 'http://id.loc.gov/authorities/names/' + sub['authority_id']
            elif sub['source'] == 'naf':
                if 'loc.gov' not in sub['authority_id']:
                    sub['authority_id'] = 'http://id.loc.gov/authorities/names/' + sub['authority_id']
            elif sub['source'] == 'tgn':
                if 'getty.edu' not in sub['authority_id']:
                    sub['authority_id'] = 'http://vocab.getty.edu/tgn/' + sub['authority_id']
            elif sub['source'] == 'aat':
                if 'getty.edu' not in sub['authority_id']:
                    sub['authority_id'] = 'http://vocab.getty.edu/aat/' + sub['authority_id']
            else:
                pass
        else:
            pass

    return sub_list


def getGenreSubjects(subjects, resource):

    genre_subs = []
    for subject in subjects:
        if subject['terms'][0]['term_type'] == 'genre_form':
            genre_subs.append(subject)

    try:        
        if len(genre_subs) == 0:
            resource_subjects = getSubjects(resource)
            for subject in resource_subjects:
                if subject['terms'][0]['term_type'] == 'genre_form':
                    genre_subs.append(subject)
                else: 
                    pass
    except:
        pass

    return genre_subs


def getResource(archival_object):
    'Get the Resource Record of a given Archival Object'

    logging.debug('Retrieving Resource of Archival Object %s' % archival_object['uri'])
    resource_uri = archival_object['resource']['ref']
    resource = aspace.get(resource_uri)
    return resource 


def getNotesByResource(resource):
    ' Returns a list of tuples of all the notes from a Resource '

    note_tups = []
    if 'notes' in resource.keys():
        notes = resource['notes']
        for note in notes:
            logging.debug('Retrieving available notes from the Resource of %s' % resource['uri'])
            if 'content' in note.keys():
                tup = (note['type'], note['content'])
                note_tups.append(tup)
            else:
                tup = (note['type'], note['subnotes'])
                note_tups.append(tup)

    return note_tups


def getNotesTree(archival_object):
    ' Returns a list of tuples of all the notes from an Archival Object heirarchy '
    
    logging.debug('Returning list of tuples of all notes from Archival Object %s heirarchy' % archival_object['uri'])
    note_tups = []
    if 'notes' in archival_object.keys():
        notes = archival_object['notes']
        for note in notes:
            logging.debug('Retrieving available notes from %s' % archival_object['uri'])
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
                    logging.debug('Retrieving available notes from parent of %s' % archival_object['uri'])
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
                        logging.debug('Retrieving available notes from grandparent of %s' % archival_object['uri'])
                        if 'content' in note.keys():
                            tup = (note['type'], note['content'])
                            note_tups.append(tup)
                        else:
                            tup = (note['type'], note['subnotes']) 
                            note_tups.append(tup)  

        resource = getResource(archival_object)
        resource_notes = getNotesByResource(resource)
        note_tups.extend(resource_notes)

    return note_tups


def getNotesByType(note_tups, notetype):
    ' Returns the dictionary for a specified note type; works in conjunction with getNotesTree '
    
    logging.debug('Retrieving notes by type %s from list of note tuples generated in getNotesTree' % notetype)
    for note in note_tups:
        logging.debug('Iterating over list of notes to retrieve %s type notes if they exist' % notetype)
        if note[0] == notetype:
            return note[1]


def getLangAtAOLevel(archival_object):
    obj_langs = []
    note_tups = getNotesTree(archival_object)
    lang_notes = getNotesByType(note_tups, 'langmaterial')
    try:
        for lang in lang_notes:
            langs = lang.split(';')
            for lang in langs:
                if lang == 'The primary language of the materials is English.':
                    lang = 'English'
                    obj_langs.append(lang)
                else:
                    obj_langs.append(lang)
    except:
        pass

    return obj_langs


def getSeries(resource_num):
    ' Returns first level down children of given resource '

    logging.debug('Retrieving Series level children of Resource %s' % resource_num)
    resource_num = str(resource_num)
    series_lst = []

    record = aspace.get('/repositories/2/resources/' + resource_num + '/tree')

    if record['children']:
        for child in record['children']:
            logging.debug('Adding each first level child of Resource %s to a list' % resource_num)
            series_lst.append(child)

    return series_lst


def getSeriesUri(series):
    return series['record_uri']


def getChildUri(child):
    logging.debug('Returning URI for Archival Object %s' % child['record_uri'])
    return child['record_uri']


def getChildUris(series):  # Could probably be reworked
    ' Returns list of child URIs for the child of a parent resource '
    ' Assumes searching through a single series in a record group '

    logging.debug('Retrieving URIs for each child of Series %s passed' % series)
    child_uris = []  # Starting list to append to
    children = series['children']  # Children of the series, which is itself the child of a record group

    child_uris.append(getSeriesUri(series))

    for child in children:
        child_uris.append(getChildUri(child))
        if child['children']:
            for child in child['children']:
                child_uris.append(getChildUri(child))
                if child['children']:
                    for child in child['children']:
                        child_uris.append(getChildUri(child))
                        if child['children']:
                            for child in child['children']:
                                child_uris.append(getChildUri(child))
                                if child['children']:
                                    for child in child['children']:
                                        child_uris.append(getChildUri(child))
                                        if child['children']:
                                            for child in child['children']:
                                                child_uris.append(getChildUri(child))
                                                if child['children']:
                                                    for child in child['children']:
                                                        child_uris.append(getChildUri(child))


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
            logging.debug('Checking if Archival Object %s has Digital Object instance' % uri)
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


def getSlice(a_list, num=5):  
    ' Returns select amount of the list to a new list '
    
    piece = a_list[:num]

    lst = []
    for bite in piece:
        lst.append(bite)

    return lst

 

