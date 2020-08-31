from asnake.aspace import ASpace
import jinja2
from pprint import pprint as pp
import argparse
import glob
import os.path
import record_funcs
import logging
import json


def set_cache(list_of_repos):
  'Function to set cache of digital objects and parent archival objects and resources for MODS exporting'
  
  cache = []
  for r in list_of_repos:
      repo = aspace.repositories(r)
      dos = repo.digital_objects()
      for do in dos:
          do_dict = {}
          do_dict['digital_object'] = do.json()
          try:
              do_dict['archival_object'] = aspace.client.get(do_dict['digital_object']['linked_instances'][0]['ref']).json()
          except Exception as e:
              logging.error(e)
              do_dict['archival_object'] = ""
          try:
              do_dict['resource'] = aspace.client.get(do_dict['archival_object']['resource']['ref']).json()
          except Exception as e:
              logging.error(e)
              do_dict['resource'] = ""
          cache.append(do_dict)

  return cache


def renderRecord(cache_obj):
    'Call all the functions'

    logging.info('Calling all functions and rendering MODS record')

    digital_object = cache_obj['digital_object']
    try:
        archival_object = cache_obj['archival_object']
    except Exception as e:
        logging.error(e)
        archival_object = ''
    try:
        container = myrecordfuncs.getShelfLocation(cache_obj['archival_object'])
    except Exception as e:
        logging.error(e)
        container = ''
    try:
        folder = myrecordfuncs.getFolder(archival_object)
    except Exception as e:
        logging.error(e)
        folder = ''
    try: 
        resource = cache_obj['resource']
    except Exception as e:
        logging.error(e)
        resource = ''
    try:
        notes = myrecordfuncs.getNotesTree(archival_object, resource)
    except Exception as e:
        logging.error(e)
        notes = []
    try:
        abstract = myrecordfuncs.getNotesByType(notes, 'scopecontent')
    except Exception as e:
        logging.error(e)
        abstract = ''
    try:
        userestrict = myrecordfuncs.getNotesByType(notes, 'userestrict')
    except Exception as e:
        logging.error(e)
        userestrict = ''
    try:
        accrestrict = myrecordfuncs.getNotesByType(notes, 'accessrestrict')
    except Exception as e:
        logging.error(e)
        accrestrict = ''
    try:
        processinfo = myrecordfuncs.getNotesByType(notes, 'processinfo')
        if 'select material' in processinfo[0]['content'].lower():
            excerpts = True
        else:
            excerpts = False
    except Exception as e:
        logging.error(e)
        excerpts = False
    try:
        langs = myrecordfuncs.getLangAtAOLevel(archival_object, resource)
    except Exception as e:
        logging.error(e)
        langs = []
    try:
        repository = myrecordfuncs.getRepository(digital_object)
    except Exception as e:
        logging.error(e)
        repository = ''
    try:
        collecting_unit = myrecordfuncs.getCollectingUnit(repository)
    except Exception as e:
        logging.error(e)
        collecting_unit = ''
    try:
        ms_no = myrecordfuncs.getMsNo(archival_object, resource)
    except Exception as e:
        logging.error(e)
        ms_no = ''
    try:
        subjects = myrecordfuncs.getSubjects(archival_object)
        genre_subs = myrecordfuncs.getGenreSubjects(subjects)
        subjects = myrecordfuncs.removeGenreSubjects(subjects)
    except Exception as e:
        logging.error(e)
        genre_subs = []
        subjects = []
    try:
        agents = myrecordfuncs.getInheritedAgents(archival_object, resource)
    except Exception as e:
        logging.error(e)
        agents = []

    data = {'archival_object': archival_object, 'resource': resource, 'langs': langs, 'repository': repository, 'subjects': subjects, 'genre_subs': genre_subs, 'agents': agents, 'collecting_unit': collecting_unit, 'ms_no': ms_no, 'digital_object': digital_object, 'folder': folder, 'container': container, 'abstract': abstract, 'userestrict': userestrict, 'accessrestrict': accrestrict, 'excerpts': excerpts}

    templateLoader = jinja2.FileSystemLoader(searchpath=".")
    templateEnv = jinja2.Environment(loader=templateLoader)

    # Merge the template and data
    template = templateEnv.get_template('compass-mods-template.xml')

    return template.render(data)



if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    aspace = ASpace()

    argparser = argparse.ArgumentParser()
    argparser.add_argument("OUTPUTPATH", help="File path for record output.")
    cliArguments = argparser.parse_args()

    myrecordfuncs = record_funcs.aspaceRecordFuncs(aspace)

    # Make API call for each digital object and set cache
    list_of_repos = [2, 3, 4]

    compass_dos = []
    sieve = []
    cache = set_cache(list_of_repos)
    for c in cache:
        for fv in c['digital_object']['file_versions']:
            if 'compass' in fv['file_uri']:
                if not c['digital_object']['uri'] in sieve:
                    sieve.append(c['digital_object']['uri'])
                    compass_dos.append(c) 

    
    # Writing the files
    save_path = cliArguments.OUTPUTPATH

    count = 0
    if os.path.isdir(save_path) != False:
        for obj in compass_dos:
            count += 1
            pp(count)
            logging.debug('Rendering MODS record for %s' % obj['digital_object']['uri'])
            xml = renderRecord(obj)
            handle = myrecordfuncs.getModsFileName(obj['digital_object'])
            filename = os.path.join(save_path, handle + ".xml")

            try:
                with open(filename, "w") as fh:
                    logging.info('Writing %s' % filename)
                    fh.write(xml)
            except Exception as e:
                logging.error(e)

        logging.info('All files written.')        

    else:
        logging.error("Directory not found. Please create if not created. Files cannot be written without an existing directory to store them.")
        exit(1)




