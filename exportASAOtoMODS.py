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
argparser.add_argument("SERVERCFG", nargs="?", default="DEFAULT", help="Name of the server configuration section e.g. 'production' or 'testing'. Edit archivesspace.cfg to add a server configuration section. If no configuration is specified, the default settings will be used host=localhost user=admin pass=admin.")
cliArguments = argparser.parse_args()

aspace = archivesspace.ArchivesSpace()
aspace.setServerCfg(CONFIGFILE, section=cliArguments.SERVERCFG)
aspace.connect()

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
    resource = record_funcs.getResource(archival_object)
    try:
        id_1 = resource['id_1']
        id_2 = resource['id_2']
        ms_no = id_1 + ' ' + id_2
    except KeyError:
        ms_no = 'MS' + ' ' + resource['id_0'][:3]

    return ms_no


class AoGeneologyChain(object):
    def __init__(self, archival_object):
        '''Traverse all parent AOs and save them to a list. Also tack on the
        Resource Record.
        '''
        newGeneologyChain = dict()
        newGeneologyChain['object'] = archival_object
        newGeneologyChain['parents'] = []
        newGeneologyChain['resource'] = record_funcs.getResource(archival_object)
        for i in range(100):
            try:
                parentUri = archival_object['parent']['ref']
            except KeyError:
                break
            archival_object = aspace.get(parentUri)
            newGeneologyChain['parents'].append(archival_object)
        self.newGeneologyChain = newGeneologyChain

    def __repr__(self):
        return(pprint.pformat(self.newGeneologyChain))

    def dereferenceRefs(self, archival_object, elementsName):
        '''Dereference references from a given Archival Object or Resource Record
        and return them as a list.
        '''
        elements = []

        try:
            for element in archival_object[elementsName]:
                elementData = aspace.get(element['ref'])
                elements.append(elementData)
        except KeyError:
            pass
        # print(elements)
        return elements

    def lazyFind(self, mytype):
        """Get fields of a given type from the newGeneologyChain in a "lazy"
        manner, i.e. stop at the first instance. If nothing is found, return an
        empty list.
        """
        mylist = []  # Start a running list

        # If the field exists in the initial decendant object stop there
        mylist.extend(self.dereferenceRefs(self.newGeneologyChain['object'], mytype))
        if mylist:
            return mylist

        # If not, look in the parent Archival Objects. If I find something good
        # stop and return that.
        for archival_object in self.newGeneologyChain['parents']:
            mylist.extend(self.dereferenceRefs(archival_object, mytype))
            if mylist:
                return mylist

        # If all else fails, try to find it in the Resource Record
        mylist.extend(self.dereferenceRefs(self.newGeneologyChain['resource'], mytype))
        return mylist

    def TEST_lazySubFind(self, mytype, subtypeFieldName='', subtype=''):
        """Get fields of a given type from the newGeneologyChain in a "lazy"
        manner, i.e. stop at the first instance. If nothing is found, return an
        empty list.
        """

        mylist = []  # Start a running list

        def findAgentsByType(subtypeFieldName, subtype):
            myagents = []
            for item in mylist:
                # Within each item there's a list of subtypes
                # Is it one of the ones I'm looking for?
                for role in item[subtypeFieldName]:
                    if role == subtype:
                        # If so, add it to the list of agents of the desired type
                        myagents.append(item)
            return myagents

        # If the field exists in the initial decendant object stop there
        mylist.extend(self.dereferenceRefs(self.newGeneologyChain['object'], mytype))
        if mylist:
            # Run through the list to see if there are any of the desired subtype
            myagents = findAgentsByType(subtypeFieldName, subtype)
            if myagents:
                return myagents

        # If not, look in the parent Archival Objects. If I find something good
        # stop and return that.
        for archival_object in self.newGeneologyChain['parents']:
            mylist.extend(self.dereferenceRefs(archival_object, mytype))
            if mylist:
                # Run through the list to see if there are any of the desired subtype
                myagents = findAgentsByType(subtypeFieldName, subtype)
                if myagents:
                    return myagents

        # If all else fails, try to find it in the Resource Record
        mylist.extend(self.dereferenceRefs(self.newGeneologyChain['resource'], mytype))
        # Run through the list to see if there are any of the desired subtype
        myagents = findAgentsByType(subtypeFieldName, subtype)
        if myagents:
            return myagents

    def getAgentsInherited(self, mychain):
        """Get agents running up the inheritance chain handling them
        independently by type: creator, source, subject.
        """
        # agentsAnyType = self.lazyFind('linked_agents')
        # mychain = AoGeneologyChain(archival_object)

        agents = {}
        # Sort agents out into their roles for different uses in the MARC record
        agents['creators'] = []
        agents['donors'] = []
        agents['subjects'] = []
        agents['creators'] = mychain.TEST_lazySubFind('linked_agents', subtypeFieldName='linked_agent_roles', subtype='creator')
        agents['donors'] = mychain.TEST_lazySubFind('linked_agents', subtypeFieldName='linked_agent_roles', subtype='source')
        agents['subjects'] = mychain.TEST_lazySubFind('linked_agents', subtypeFieldName='linked_agent_roles', subtype='subject')
        
        if agents['creators']:
            for agent in agents['creators']:
                if agent['jsonmodel_type'] == 'agent_person':
                    agent['jsonmodel_type'] = 'personal'
                elif agent['jsonmodel_type'] == 'agent_corporate_entity':
                    agent['jsonmodel_type'] = 'corporate'
                else:
                    pass

        if agents['donors']:
            for agent in agents['donors']:
                if agent['jsonmodel_type'] == 'agent_person':
                    agent['jsonmodel_type'] = 'personal'
                elif agent['jsonmodel_type'] == 'agent_corporate_entity':
                    agent['jsonmodel_type'] = 'corporate'
                else:
                    pass

        if agents['subjects']:
            for agent in agents['subjects']:
                if agent['jsonmodel_type'] == 'agent_person':
                    agent['jsonmodel_type'] = 'personal'
                elif agent['jsonmodel_type'] == 'agent_corporate_entity':
                    agent['jsonmodel_type'] = 'corporate'
                else:
                    pass


                if 'display_name' in agent.keys():
                    if 'authority_id' in agent['display_name'].keys():
                        if agent['display_name']['source'] == 'naf':
                            if 'loc.gov' not in agent['display_name']['authority_id']:
                                agent['display_name']['authority_id'] = 'http://id.loc.gov/authorities/names/' + agent['display_name']['authority_id']
                        elif agent['display_name']['source'] == 'lcsh':
                            agent['display_name']['authority_id'] = 'http://id.loc.gov/authorities/subjects/' + agent['display_name']['authority_id']
                        elif agent['display_name']['source'] == 'tgn':
                            agent['display_name']['authority_id'] = 'http://vocab.getty.edu/tgn/' + agent['display_name']['authority_id']
                        elif agent ['display_name']['source'] == 'aat':
                            agent['display_name']['authority_id'] = 'http://vocab.getty.edu/aat/' + agent['display_name']['authority_id']
        
        return agents

    # def getNotesByType(self, noteType):
    #     '''Traverse all parent AOs and the Resource Record and get all the
    #     notes of given type
    #     '''
    #     notes = []
    #     for archival_object in self.aoGeneologyChain:
    #         try:
    #             for note in archival_object['notes']:
    #                 if note['type'] == noteType:
    #                     notes.append(note)
    #         except KeyError:
    #             pass
    #     return notes

    # def getAllNotes(self):
    #     # Get list of controled values for note types
    #     enums = aspace.get(NOTETYPESURI)
    #     noteTypeS = enums['values']
    #     notes = dict()
    #     for noteType in noteTypeS:
    #         notes[noteType] = self.getNotesByType(noteType)
    #     return notes


# mychain = AoGeneologyChain(archival_object)
# notes = getNotesByType(mychain, userestrict)

# print(notes)

# Traverse all parent AOs and the Resource Record and get their subjects
# subjects = mychain.getSubjectsInherited()

# agents = mychain.getAgentsInherited()


# Debug
# pprint.pprint(agents)
# import pdb; pdb.set_trace()

# Get genre data
# Get agent data
# Get notes data
# allNotes = mychain.getNotes()
# notesToPublish = dict()
# notesToPublish['accessrestrict'] = []
#
# try:
#     notesToPublish['accessrestrict'].append(allNotes['accessrestrict'][0])
#     notesToPublish['accessrestrict'].append(allNotes['accessrestrict'][-1])
# except KeyError:
#     pass


def renderRecord(do_uri):
    'Call all the functions'

    logging.info('Calling all functions and rendering MODS record')
    digital_object = getDigitalObject(do_uri)
    archival_object = getArchivalObject(do_uri)
    container = getShelfLocation(archival_object)
    folder = getFolder(archival_object)
    resource = record_funcs.getResource(archival_object)
    notes = record_funcs.getNotesTree(archival_object)
    abstract = record_funcs.getNotesByType(notes, 'scopecontent')
    userestrict = record_funcs.getNotesByType(notes, 'userestrict')
    accrestrict = record_funcs.getNotesByType(notes, 'accessrestrict')
    collecting_unit = getCollectingUnit(archival_object)
    ms_no = getMsNo(archival_object)
    repository = getRepository(archival_object)
    mychain = AoGeneologyChain(archival_object)
    subjects = record_funcs.getSubjects(archival_object)
    genre_subs = record_funcs.getGenreSubjects(subjects, resource)
    agents = mychain.getAgentsInherited(mychain)

    data = {'archival_object': archival_object, 'resource': resource, 'repository': repository, 'subjects': subjects, 'genre_subs': genre_subs, 'agents': agents, 'collecting_unit': collecting_unit, 'ms_no': ms_no, 'digital_object': digital_object, 'folder': folder, 'container': container, 'abstract': abstract, 'userestrict': userestrict, 'accessrestrict': accrestrict}

    templateLoader = jinja2.FileSystemLoader(searchpath=".")
    templateEnv = jinja2.Environment(loader=templateLoader)

    # Merge the template and data
    template = templateEnv.get_template('compass-mods-template.xml')

    return template.render(data)


' ********************************* '
' ***** Calling the functions ***** '
' ********************************* '

'Retrieve list of digital object URIs for YWCA of the U.S.A. Photographic Records'
ywca_photo_uris = record_funcs.getAllResourceUris(676)

'Make API call for each record in YWCA of the U.S.A. Photographic Records and add all Digital Object URIs to a list'
do_photo_uris = record_funcs.getDigitalObjectUris(ywca_photo_uris)


'Writing the files'
save_path = cliArguments.outputpath

if os.path.isdir(save_path) != False:
    for do_uri in do_photo_uris:
        logging.debug('Rendering MODS record for %s' % do_uri)
        xml = renderRecord(do_uri)
        do = getDigitalObject(do_uri)
        handle = record_funcs.getModsFileName(do)
        filename = os.path.join(save_path, handle + ".xml")

        with open(filename, "w") as fh:
            logging.info('Writing %s' % filename)
            fh.write(xml)

    logging.info('All files written.')        

else:
    logging.info("Directory not found. Please create if not created. Files cannot be written without an existing directory to store them.")
    exit(1)
