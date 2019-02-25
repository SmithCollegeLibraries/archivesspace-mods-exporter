from archivesspace import archivesspace
import jinja2
import pprint
import argparse
import glob
import os.path
import record_funcs
import logging

CONFIGFILE = "archivesspace.cfg"

argparser = argparse.ArgumentParser()
argparser.add_argument("outputpath", help="File path for record output.")
argparser.add_argument("RESOURCERECORDID", type=int, help="ID of top level resource record to get digital objects from. (example: 676)")
argparser.add_argument("SERVERCFG", default="DEFAULT", help="Name of the server configuration section e.g. 'production' or 'testing'. Edit archivesspace.cfg to add a server configuration section. If no configuration is specified, the default settings will be used host=localhost user=admin pass=admin.")
cliArguments = argparser.parse_args()

aspace = archivesspace.ArchivesSpace()
aspace.setServerCfg(CONFIGFILE, section=cliArguments.SERVERCFG)
aspace.connect()

myrecordfuncs = record_funcs.aspaceRecordFuncs(aspace)

"""
Query ArchivesSpace API for details about an Archival Object and format the
resulting data in MODS format using a jinja template.

Concepts:

# Geneology Chain

# Constellation

"""

logging.basicConfig(level=logging.INFO)

NOTETYPESURI = '/config/enumerations/45'

print("*********")


def getDigitalObject(do_uri):
    'Get Digital Object from Digital Object URI'

    logging.debug('Retrieving Digital Object from Digital Object URI')
    digital_object = aspace.get(do_uri)

    return digital_object


def getArchivalObject(do_uri):
    'Get an Archival Object from a Digital Object URI'

    logging.debug('Retrieving Archival Object from Digital Object %s' % do_uri)
    digital_object = getDigitalObject(do_uri)
    archival_object_uri = digital_object['linked_instances'][0]['ref']
    archival_object = aspace.get(archival_object_uri)

    return archival_object


def getShelfLocation(archival_object):
    'Get the Shelf Location of a given Archival Object'
    
    logging.debug('Retrieving Shelf Location of Archival Object %s' % archival_object['uri'])
    try:
        top_container_uri = archival_object['instances'][0]['sub_container']['top_container']['ref']
        top_container = aspace.get(top_container_uri)
        top_container_title = top_container['display_string']
    except KeyError:
        return None

    return top_container_title


def getFolder(archival_object):
    ' Gets the folder if there is one of an Archival Object '

    logging.debug('Retrieving folder of Archival Object %s' % archival_object['uri'])
    try:
        fol = archival_object['instances'][0]['sub_container']['type_2'].capitalize()
        num = archival_object['instances'][0]['sub_container']['indicator_2']
        folder = fol + " " + num
    except KeyError:
        return None

    return folder


def getRepository(archival_object):
    'Get the repository of a given Archival Object'

    logging.debug('Retrieving Repository of Archival Object %s' % archival_object['uri'])
    repository_uri = archival_object['repository']['ref']
    repository = aspace.get(repository_uri)
    return repository


def getCollectingUnit(archival_object):
    'Get the collecting unit of a given Archival Object'

    logging.debug('Retrieving Collecting Unit of Archival Object %s' % archival_object['uri'])
    repository = getRepository(archival_object)
    collecting_unit = repository['name']

    return collecting_unit


def getMsNo(archival_object):
    'Get the MS number of a given Archival Object'

    logging.debug('Retrieving MS number of Archival Object %s' % archival_object['uri'])
    resource = myrecordfuncs.getResource(archival_object)
    try:
        id_1 = resource['id_1']
        id_2 = resource['id_2']
        ms_no = id_1 + ' ' + id_2
    except KeyError:
        ms_no = 'MS' + ' ' + resource['id_0'][:3]

    return ms_no


def getAgents(archival_object):
    'Returns agents'
    agents_lst = []
    if 'linked_agents' in archival_object.keys():
        for agent in archival_object['linked_agents']:
            agents_lst.append(agent)

    new_agents_lst = []     
    for agent in agents_lst:
        agent_dct = {}
        agent_dct['role'] = agent['role']
        uri = agent['ref']
        agent_dct['data'] = aspace.get(uri) 
        new_agents_lst.append(agent_dct)


    for agent in new_agents_lst:
        if agent['role'] == 'creator':
            if agent['data']['jsonmodel_type'] == 'agent_person':
                agent['data']['jsonmodel_type'] = 'personal'
            elif agent['data']['jsonmodel_type'] == 'agent_corporate_entity':
                agent['data']['jsonmodel_type'] = 'corporate'
            else:
                pass
        if agent['role'] == 'source':
            if agent['data']['jsonmodel_type'] == 'agent_person':
                agent['data']['jsonmodel_type'] = 'personal'
            elif agent['data']['jsonmodel_type'] == 'agent_corporate_entity':
                agent['data']['jsonmodel_type'] = 'corporate'
            else:
                pass
        if agent['role'] == 'subject':
            if agent['data']['jsonmodel_type'] == 'agent_person':
                agent['data']['jsonmodel_type'] = 'personal'
            elif agent['data']['jsonmodel_type'] == 'agent_corporate_entity':
                agent['data']['jsonmodel_type'] = 'corporate'
            else:
                pass

            if 'display_name' in agent['data'].keys():
                if 'authority_id' in agent['data']['display_name'].keys():
                    if agent['data']['display_name']['source'] == 'naf':
                        if 'loc.gov' not in agent['data']['display_name']['authority_id']:
                            agent['data']['display_name']['authority_id'] = 'http://id.loc.gov/authorities/names/' + agent['data']['display_name']['authority_id']
                        elif agent['data']['display_name']['source'] == 'lcsh':
                            agent['data']['display_name']['authority_id'] = 'http://id.loc.gov/authorities/subjects/' + agent['data']['display_name']['authority_id']
                        elif agent['data']['display_name']['source'] == 'tgn':
                            agent['data']['display_name']['authority_id'] = 'http://vocab.getty.edu/tgn/' + agent['data']['display_name']['authority_id']
                        elif agent['data']['display_name']['source'] == 'aat':
                            agent['data']['display_name']['authority_id'] = 'http://vocab.getty.edu/aat/' + agent['data']['display_name']['authority_id']

    return new_agents_lst


def getParentRecords(archival_object):
    parent_uris = []
    for i in range(100):
        try:
            parentUri = archival_object['parent']['ref']
        except KeyError:
            break
        parent_ao = aspace.get(parentUri)
        if parent_ao['uri'] not in parent_uris:
            parent_uris.append(parent_ao['uri'])

    parent_records = []
    for uri in parent_uris:
        parent_record = aspace.get(uri)
        parent_records.append(parent_record)

    return parent_records


def getAllAgents(archival_object, resource):
    all_agents = []

    resource_agents = getAgents(resource)
    all_agents.extend(resource_agents)

    ao_agents = getAgents(archival_object)
    all_agents.extend(ao_agents)

    parent_records = getParentRecords(archival_object)
    for record in parent_records:
        parent_agents = getAgents(record)
        all_agents.extend(parent_agents)

    return all_agents


def renderRecord(do_uri):
    'Call all the functions'

    logging.info('Calling all functions and rendering MODS record')
    digital_object = getDigitalObject(do_uri)
    archival_object = getArchivalObject(do_uri)
    archival_object = archival_object
    container = getShelfLocation(archival_object)
    folder = getFolder(archival_object)
    resource = myrecordfuncs.getResource(archival_object)
    notes = myrecordfuncs.getNotesTree(archival_object)
    abstract = myrecordfuncs.getNotesByType(notes, 'scopecontent')
    userestrict = myrecordfuncs.getNotesByType(notes, 'userestrict')
    accrestrict = myrecordfuncs.getNotesByType(notes, 'accessrestrict')
    langs = myrecordfuncs.getLangAtAOLevel(archival_object)
    collecting_unit = getCollectingUnit(archival_object)
    ms_no = getMsNo(archival_object)
    repository = getRepository(archival_object)
    subjects = myrecordfuncs.getSubjects(archival_object)
    genre_subs = myrecordfuncs.getGenreSubjects(subjects, resource)
    subjects = myrecordfuncs.deleteGenreSubjects(subjects)
    agents = getAllAgents(archival_object, resource)

    data = {'archival_object': archival_object, 'resource': resource, 'langs': langs, 'repository': repository, 'subjects': subjects, 'genre_subs': genre_subs, 'agents': agents, 'collecting_unit': collecting_unit, 'ms_no': ms_no, 'digital_object': digital_object, 'folder': folder, 'container': container, 'abstract': abstract, 'userestrict': userestrict, 'accessrestrict': accrestrict}

    templateLoader = jinja2.FileSystemLoader(searchpath=".")
    templateEnv = jinja2.Environment(loader=templateLoader)

    # Merge the template and data
    template = templateEnv.get_template('compass-mods-template.xml')

    return template.render(data)




' ********************************* '
' ***** Calling the functions ***** '
' ********************************* '

'Retrieve list of digital object URIs for YWCA of the U.S.A. Photographic Records'
# ywca_photo_uris = myrecordfuncs.getAllResourceUris(cliArguments.RESOURCERECORDID)

'Make API call for each record in YWCA of the U.S.A. Photographic Records and add all Digital Object URIs to a list'
# do_photo_uris = myrecordfuncs.getDigitalObjectUris(ywca_photo_uris)

do_photo_uris = ['/repositories/2/digital_objects/1365']

'Writing the files'
save_path = cliArguments.outputpath

if os.path.isdir(save_path) != False:
    for do_uri in do_photo_uris:
        logging.debug('Rendering MODS record for %s' % do_uri)
        xml = renderRecord(do_uri)
        do = getDigitalObject(do_uri)
        handle = myrecordfuncs.getModsFileName(do)
        filename = os.path.join(save_path, handle + ".xml")

        with open(filename, "w") as fh:
            logging.info('Writing %s' % filename)
            fh.write(xml)

    logging.info('All files written.')        

else:
    logging.info("Directory not found. Please create if not created. Files cannot be written without an existing directory to store them.")
    exit(1)
