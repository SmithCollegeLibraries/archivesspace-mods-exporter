from asnake.aspace import ASpace
import jinja2
from pprint import pprint as pp
import argparse
import glob
import os.path
import new_record_funcs
import logging
import json



def filter_out_non_compass_objs(cache):
        compass_dos = []
        sieve = []
        for c in cache:
            for fv in c['digital_object']['file_versions']:
                if 'compass' in fv['file_uri']:
                    if not c['digital_object']['uri'] in sieve:
                        sieve.append(c['digital_object']['uri'])
                        compass_dos.append(c) 

        return compass_dos


def cache_agents_or_subjects(record_json, search_type):
    # search_type must either be 'linked_agents' or 'subjects'
    lst = []
    if len(record_json[search_type]) > 0:
        for i in record_json[search_type]:
            i_json = aspace.client.get(i['ref']).json()
            if not i_json in lst:
                lst.append(i_json)

    return lst


def get_resource_agents(dict_of_resources, search_type='linked_agents'):
    # search_type must be 'linked_agents'
    resource_objs = {}
    for k in dict_of_resources.keys():
        record_json = dict_of_resources[k]
        objs = cache_agents_or_subjects(record_json, search_type)
        resource_objs[record_json['uri']] = objs

    return resource_objs


def add_resource_agents_to_cache(cache, resource_agents):
    for do_dict in cache:
        do_dict['resource_agents'] = []
        try:
            if resource_agents.get(do_dict['resource']['uri']) != None:
                do_dict['resource_agents'] = resource_agents[do_dict['resource']['uri']]
        except KeyError:
            continue

        do_dict['all_agents'] = do_dict['resource_agents'] + do_dict['archival_object_agents']
        try:
            do_dict['all_linked_agents'] = do_dict['resource']['linked_agents'] + do_dict['archival_object']['linked_agents']
        except KeyError:
            do_dict['all_linked_agents'] = do_dict['resource']['linked_agents']
        except KeyError:
            do_dict['all_linked_agents'] = []       
         
    return cache


def set_dict(do):
    d = {}
    d['digital_object'] = do.json()
    d['archival_object'] = {}
    d['resource'] = {}
    d['archival_object_agents'] = []
    d['archival_object_subjects'] = []
    d['resource_agents'] = []
    d['all_agents'] = []

    return d    


def run_one_or_all(repo, number=''):
    if len(str(number)) > 0:
        dos = []
        do = repo.digital_objects(int(number))
        dos.append(do)
        return dos
    else:
        dos = repo.digital_objects()
        return dos


def make_cache(list_of_repos):
    cache = []
    resources = {}
    for r in list_of_repos:
        repo = aspace.repositories(r)
        logging.info('Making cache for repo {}'.format(r))
        dos = run_one_or_all(repo)
        for do in dos:
            do_dict = set_dict(do)
            try:
                if 'archival_objects' in do_dict['digital_object']['linked_instances'][0]['ref']: # So don't get JSON for accession, etc.
                    do_dict['archival_object'] = aspace.client.get(do_dict['digital_object']['linked_instances'][0]['ref']).json()
                    do_dict['archival_object_agents'] = cache_agents_or_subjects(do_dict['archival_object'], 'linked_agents')
                    do_dict['archival_object_subjects'] = cache_agents_or_subjects(do_dict['archival_object'], 'subjects')  
            except IndexError:
                continue
            try:
                if resources.get(do_dict['archival_object']['resource']['ref']) != None:
                    do_dict['resource'] = resources[do_dict['archival_object']['resource']['ref']]
                else:
                    resource = aspace.client.get(do_dict['archival_object']['resource']['ref']).json()
                    resources[resource['uri']] = resource # resource['uri'] should equal do_dict['archival_object']['resource']['ref']
                    do_dict['resource'] = resource
            except KeyError:
                continue
            cache.append(do_dict)

    resource_agents = get_resource_agents(resources, 'linked_agents')

    return add_resource_agents_to_cache(cache, resource_agents)


def get_value(myrecipe):
    try:
        myrecipe
    except Exception as e:
        return ''


def render_record(mapping): 
    templateLoader = jinja2.FileSystemLoader(searchpath=".")
    templateEnv = jinja2.Environment(loader=templateLoader)

    # Merge the template and data
    template = templateEnv.get_template('compass-mods-template.xml')

    return template.render(mapping)


def make_mapping(cache_obj):
    mapping = {
        'archival_object': cache_obj['archival_object'], 
        'resource': cache_obj['resource'], 
        'langs': myrecordfuncs.getLangAtAOLevel(cache_obj['archival_object'], cache_obj['resource']), 
        'repository': myrecordfuncs.getRepository(cache_obj['digital_object']), 
        'subjects': myrecordfuncs.removeGenreSubjects(myrecordfuncs.getSubjects(cache_obj['archival_object_subjects'])), 
        'genre_subs': myrecordfuncs.getGenreSubjects(cache_obj['archival_object_subjects']), 
        'agents': myrecordfuncs.filterSubjectAgents(myrecordfuncs.getAgents(cache_obj['all_linked_agents'], cache_obj['all_agents'])), 
        'collecting_unit': myrecordfuncs.getCollectingUnit(myrecordfuncs.getRepository(cache_obj['digital_object'])), 
        'ms_no': myrecordfuncs.getMsNo(cache_obj['archival_object'], cache_obj['resource']), 
        'digital_object': cache_obj['digital_object'], 
        'folder': myrecordfuncs.getFolder(cache_obj['archival_object']), 
        'container': myrecordfuncs.getShelfLocation(cache_obj['archival_object']), 
        'abstract': myrecordfuncs.getNotesByType(myrecordfuncs.getNotesTree(cache_obj['archival_object'], cache_obj['resource']), 'scopecontent'), 
        'userestrict': myrecordfuncs.getNotesByType(myrecordfuncs.getNotesTree(cache_obj['archival_object'], cache_obj['resource']), 'userestrict'), 
        'accessrestrict': myrecordfuncs.getNotesByType(myrecordfuncs.getNotesTree(cache_obj['archival_object'], cache_obj['resource']), 'accessrestrict'), 
        'excerpts': myrecordfuncs.add_excerpts_to_title(myrecordfuncs.getNotesTree(cache_obj['archival_object'], cache_obj['resource']))
        }


    for key, value in mapping.items():
        key = get_value(value)

    return mapping


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    aspace = ASpace()

    argparser = argparse.ArgumentParser()
    argparser.add_argument("OUTPUTPATH", help="File path for record output.")
    cliArguments = argparser.parse_args()

    myrecordfuncs = record_funcs.aspaceRecordFuncs(aspace)

    list_of_repos = [2,3,4]
    
    cache = filter_out_non_compass_objs(make_cache(list_of_repos))        
    
    save_path = cliArguments.OUTPUTPATH

    count = 0
    if os.path.isdir(save_path) != False:
        for obj in cache:
            try:
                count += 1
                pp(count)
                logging.debug('Rendering MODS record for %s' % obj['digital_object']['uri'])
                xml = render_record(make_mapping(obj))
                handle = myrecordfuncs.getModsFileName(obj['digital_object'])
                filename = os.path.join(save_path, handle + ".xml")

                try:
                    with open(filename, "w") as fh:
                        logging.info('Writing %s' % filename)
                        fh.write(xml)
                except Exception as e:
                    logging.error(e)
            except Exception as e:
                logging.error(e)

        logging.info('All files written.')        

    else:
        logging.error("Directory not found. Please create if not created. Files cannot be written without an existing directory to store them.")
        exit(1)



