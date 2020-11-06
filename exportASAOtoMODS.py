from asnake.aspace import ASpace
import jinja2
from pprint import pprint as pp
import argparse
import glob
import os.path
import record_funcs
import logging
import json
import time as t


def set_dict(do):
    d = {}
    d['digital_object'] = do
    d['archival_object'] = {}
    d['resource'] = {}
    d['archival_object_subjects'] = []
    d['creators'] = []
    d['sources'] = []
    d['subject_agents'] = []
    d['top_container'] = {}

    return d    


def chunk_ids(id_list):
    ids = []
    if len(id_list) > 25:
        id_chunks = [id_list[uri:uri + 25] for uri in range(0, len(id_list), 25)] 
        for chunk in id_chunks:
            chunk = [str(i) for i in chunk]
            chunk = ','.join(chunk)
            ids.append(chunk)
    
    else:
        id_list = [str(i) for i in id_list]
        id_list = ','.join(id_list)
        ids.append(id_list)

    return ids


def group_uris(uri_list):
    all_uris = {}
    all_uris['2'] = []
    all_uris['3'] = []
    all_uris['4'] = []
    for uri in uri_list:
        if '/repositories/2' in uri:
            all_uris['2'].append(uri.split('/')[-1])
        elif '/repositories/3' in uri:
            all_uris['3'].append(uri.split('/')[-1])
        elif '/repositories/4' in uri:
            all_uris['4'].append(uri.split('/')[-1])

    return all_uris


def group_agents(uri_list):
    all_uris = {}
    all_uris['corporate_entities'] = []
    all_uris['people'] = []
    all_uris['families'] = []
    for uri in uri_list:
        if 'corporate' in uri:
            all_uris['corporate_entities'].append(uri.split('/')[-1])
        elif 'people' in uri:
            all_uris['people'].append(uri.split('/')[-1])
        elif 'families' in uri:
            all_uris['families'].append(uri.split('/')[-1])

    return all_uris


def get_data_dict():
    extracted_data = {}
    extracted_data['digital_objects'] = []
    extracted_data['archival_objects'] = []
    extracted_data['accessions'] = []
    extracted_data['resources'] = []    
    extracted_data['subjects'] = []
    extracted_data['agents'] = []
    extracted_data['top_containers'] = []

    return extracted_data


def get_digital_objects(repo):
    r = aspace.repositories(repo)
    dos = r.digital_objects()
    digital_objects = []
    for do in dos:
        if 'user_defined' in do.json().keys():
            if do.json()['user_defined']['boolean_1'] == True:
                continue
        
        for file_version in do.json()['file_versions']:
            if 'compass' in file_version['file_uri']:
                if not do.json() in digital_objects:
                    digital_objects.append(do.json())

    return digital_objects


def get_digital_objects_by_repo(list_of_repos, data_dict):
    for repo in list_of_repos:  
        data_dict['digital_objects'].extend(get_digital_objects(repo))

    return data_dict


def get_parent_objects(data_dict):
    all_ao_uris = []
    for do in data_dict['digital_objects']:
        for instance in do['linked_instances']:
            if 'archival_objects' in instance['ref']:
                if not instance['ref'] in all_ao_uris:
                    all_ao_uris.append(instance['ref'])
                else:
                    record = aspace.client.get(instance['ref'])
                    if 'resources' in instance['ref']:
                        data_dict['resources'].append(record.json())
                    elif 'accessions' in instance['ref']:
                        data_dict['accessions'].append(record.json())

    aos_grouped_by_repo = group_uris(all_ao_uris)
    for k, v in aos_grouped_by_repo.items():
        chunks = chunk_ids(v)
        for chunk in chunks:
            archival_objects = aspace.client.get(f'/repositories/{k}/archival_objects?id_set={chunk}')
            data_dict['archival_objects'].extend(archival_objects.json())

    return data_dict


def get_resources(data_dict):
    resource_uris = []
    for ao in data_dict['archival_objects']:
        try:
            if not ao['resource']['ref'] in resource_uris:
                resource_uris.append(ao['resource']['ref'])
        except TypeError as e:
            continue

    resources_grouped_by_repo = group_uris(resource_uris)
    for k, v in resources_grouped_by_repo.items():
        chunks = chunk_ids(v)
        for chunk in chunks:
            resources = aspace.client.get(f'/repositories/{k}/resources?id_set={chunk}')
            data_dict['resources'].extend(resources.json())

    return data_dict


def get_agents(data_dict):
    agent_uris = []
    for ao in data_dict['archival_objects']:
        if len(ao['linked_agents']) > 0:
            for agent in ao['linked_agents']:
                if not agent['ref'] in agent_uris:
                    agent_uris.append(agent['ref'])

    for r in data_dict['resources']:
        if len(r['linked_agents']) > 0:
            for agent in r['linked_agents']:
                if agent['role']!= 'subject':
                    if agent['ref'] not in agent_uris:
                        agent_uris.append(agent['ref'])

    agents_grouped_by_type = group_agents(agent_uris)
    for k, v in agents_grouped_by_type.items():
        chunks = chunk_ids(v)
        for chunk in chunks:
            agents = aspace.client.get(f'/agents/{k}?id_set={chunk}')
            data_dict['agents'].extend(agents.json())

    return data_dict


def correct_agent_type(data_dict):
    for a in data_dict['agents']:
        if a['jsonmodel_type'] == 'agent_person':
            a['jsonmodel_type'] = 'personal'
        elif a['jsonmodel_type'] == 'agent_corporate_entity':
            a['jsonmodel_type'] = 'corporate'
        elif a['jsonmodel_type'] == 'agent_family':
            a['jsonmodel_type'] = 'family'

    return data_dict


def get_subjects(data_dict):
    subject_uris = []
    for ao in data_dict['archival_objects']:
        if len(ao['subjects']) > 0:
            for subject in ao['subjects']:
                if not subject['ref'] in subject_uris:
                    subject_uris.append(subject['ref'].split('/')[-1])

    chunks = chunk_ids(subject_uris)
    for chunk in chunks:
        subjects = aspace.client.get(f'/subjects?id_set={chunk}')
        data_dict['subjects'].extend(subjects.json())

    return data_dict


def get_top_containers(data_dict):
    top_container_uris = []
    for ao in data_dict['archival_objects']:
        if len(ao['instances']) > 0:
            for i in ao['instances']:
                try:
                    if not i['sub_container']['top_container']['ref'] in top_container_uris:
                        top_container_uris.append(i['sub_container']['top_container']['ref'])
                except KeyError:
                    pass
    grouped_by_repo = group_uris(top_container_uris)
    for k, v in grouped_by_repo.items():
        chunks = chunk_ids(v)
        for chunk in chunks:
            tcs = aspace.client.get(f'/repositories/{k}/top_containers?id_set={chunk}')
            data_dict['top_containers'].extend(tcs.json())

    return data_dict


def get_extract(list_of_repos):
    data_dict = get_data_dict()
    data_dict = get_digital_objects_by_repo(list_of_repos, data_dict)
    data_dict = get_parent_objects(data_dict)
    data_dict = get_resources(data_dict)
    data_dict = correct_agent_type(get_agents(data_dict))
    data_dict = get_subjects(data_dict)
    data_dict = get_top_containers(data_dict)
    
    return data_dict


def match_subjects_to_archival_objects(extract, dict_obj):
    try:
        for sub in dict_obj['archival_object']['subjects']:
            for s in extract['subjects']:
                if sub['ref'] == s['uri']:
                    dict_obj['archival_object_subjects'].append(s)
    except TypeError:
        pass
    except KeyError:
        pass

    return dict_obj


def match_top_containers_to_archival_objects(extract, dict_obj):
    try:
        for i in dict_obj['archival_object']['instances']:
            for t in extract['top_containers']:
                if i['sub_container']['top_container']['ref'] == t['uri']:
                    dict_obj['top_container'] = t
    except KeyError:
        pass

    return dict_obj


def match_agents(extract, dict_obj):
    try:
        for a in dict_obj['archival_object']['linked_agents']:
            for agent in extract['agents']:
                try:
                    if a['ref'] == agent['uri']:
                        if a['role'] == 'creator':
                            dict_obj['creators'].append(agent)
                        elif a['role'] == 'source':
                            dict_obj['sources'].append(agent)
                        elif a['role'] == 'subject':
                            dict_obj['subject_agents'].append(agent)
                except TypeError:
                    pass
    except KeyError:
        pass

    try:
        for a in dict_obj['resource']['linked_agents']:
            for agent in extract['agents']:
                try:
                    if a['ref'] == agent['uri']:
                        if a['role'] == 'creator':
                            dict_obj['creators'].append(agent)
                except TypeError:
                    pass
    except KeyError:
        pass

    dict_obj['creators'] = [i for n, i in enumerate(dict_obj['creators']) if i not in dict_obj['creators'][n + 1:]]
    dict_obj['sources'] = [i for n, i in enumerate(dict_obj['sources']) if i not in dict_obj['sources'][n + 1:]] 
    dict_obj['subject_agents'] = [i for n, i in enumerate(dict_obj['subject_agents']) if i not in dict_obj['subject_agents'][n + 1:]]  
    
    return dict_obj


def match_archival_objects_to_resources(extract, dict_obj):
    try:
        for r in extract['resources']:
            if r['uri'] == dict_obj['archival_object']['resource']['ref']:
                dict_obj['resource'] = r
    except KeyError:
        pass

    return dict_obj


def match_extract_objects(extract):
    dicts = []
    for d in extract['digital_objects']:
        dict_obj = set_dict(d)
        for a in extract['archival_objects']:
            for inst in d['linked_instances']:
                if a['uri'] == inst['ref']:
                    dict_obj['archival_object'] = a
        try:
            dict_obj = match_archival_objects_to_resources(extract, dict_obj)
        except KeyError:
            pass
        dict_obj = match_subjects_to_archival_objects(extract, dict_obj)
        dict_obj = match_agents(extract, dict_obj)
        dict_obj = match_top_containers_to_archival_objects(extract, dict_obj)
        dicts.append(dict_obj) 

    return dicts


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
        'repository': myrecordfuncs.getCollectingUnit(cache_obj['digital_object']), 
        'subjects': myrecordfuncs.removeGenreSubjects(myrecordfuncs.getSubjects(cache_obj['archival_object_subjects'])), 
        'genre_subs': myrecordfuncs.getGenreSubjects(cache_obj['archival_object_subjects']), 
        'sources': cache_obj['sources'], 
        'creators': cache_obj['creators'],
        'subject_agents': cache_obj['subject_agents'],
        'collecting_unit': myrecordfuncs.getParentInstitution(), 
        'ms_no': myrecordfuncs.getMsNo(cache_obj['resource']), 
        'digital_object': cache_obj['digital_object'], 
        'folder': myrecordfuncs.getFolder(cache_obj['archival_object']), 
        'container': myrecordfuncs.getBoxString(cache_obj['top_container']), 
        'abstract': myrecordfuncs.getNotesByType(myrecordfuncs.getNotesTree(cache_obj['archival_object'], cache_obj['resource']), 'scopecontent'), 
        'userestrict': myrecordfuncs.getNotesByType(myrecordfuncs.getNotesTree(cache_obj['archival_object'], cache_obj['resource']), 'userestrict'), 
        'accessrestrict': myrecordfuncs.getNotesByType(myrecordfuncs.getNotesTree(cache_obj['archival_object'], cache_obj['resource']), 'accessrestrict'), 
        'excerpts': myrecordfuncs.add_excerpts_to_title(myrecordfuncs.getNotesTree(cache_obj['archival_object'], cache_obj['resource']))
        }


    return mapping


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    aspace = ASpace()

    argparser = argparse.ArgumentParser()
    argparser.add_argument("OUTPUTPATH", help="File path for record output.")
    cliArguments = argparser.parse_args()

    myrecordfuncs = record_funcs.aspaceRecordFuncs(aspace)

    repos = aspace.client.get('/repositories?all_ids=true').json()
    list_of_repos = []
    for repo in repos:
        repo_id = repo['uri'].split('/')[-1]
        list_of_repos.append(repo_id)
    
    start = t.perf_counter()
    cache = get_extract(list_of_repos)
    end = t.perf_counter()
    pp(f'Extract: {(end - start) / 60} mins')

    start = t.perf_counter()
    extract_objects = match_extract_objects(cache)
    end = t.perf_counter()
    pp(f'Match: {(end - start) / 60} mins')

    start = t.perf_counter()
    save_path = cliArguments.OUTPUTPATH

    count = 0
    if os.path.isdir(save_path) != False:
        for obj in extract_objects:
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
    end = t.perf_counter()
    pp(f'Writing: {(end - start) / 60} mins')


