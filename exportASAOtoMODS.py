from archivesspace import archivesspace
import jinja2
import pprint
from utilities import *
aspace = archivesspace.ArchivesSpace('http', 'archivesspace-test.smith.edu', '9999', 'cmarshall', 'aspace1')
aspace.connect()

"""
Query ArchivesSpace API for details about an Archival Object and format the
resulting data in MODS format using a jinja template.

Concepts:

# Geneology Chain

# Constelation

"""

NOTETYPESURI = '/config/enumerations/45'

# Retrieve the DO
# Find the DO's parent AO
# archival_object = aspace.get('/repositories/2/archival_objects/105443')
archival_object = aspace.get('/repositories/2/archival_objects/159445')
# Find the AO's parent resource
# 845


def getResource(archival_object):
    'Get the Resource Record of a given Archival Object'
    resource_uri = archival_object['resource']['ref']
    resource = aspace.get(resource_uri)
    return resource


resource = getResource(archival_object)
# print(resource)

# Find the parent repo


def getRepository(archival_object):
    'Get the repository of a given Archival Object'
    repository_uri = archival_object['repository']['ref']
    repository = aspace.get(repository_uri)
    return repository


repository = getRepository(archival_object)


def getCollectingUnit(archival_object):
    repository = getRepository(archival_object)
    collecting_unit = repository['name']

    return collecting_unit


collecting_unit = getCollectingUnit(archival_object)


def getMsNo(archival_object):
    resource = getResource(archival_object)
    try:
        id_1 = resource['id_1']
        id_2 = resource['id_2']
        ms_no = id_1 + ' ' + id_2
    except KeyError:
        ms_no = 'MS' + ' ' + resource['id_0'][:3]

    return ms_no


ms_no = getMsNo(archival_object)


class AoGeneologyChain(object):
    def __init__(self, archival_object):
        '''Traverse all parent AOs and save them to a list. Also tack on the
        Resource Record.
        '''
        # def wrapUp(aoGeneologyChain):
        #     resource = getResource(archival_object)
        #     aoGeneologyChain.append(resource)
        #     return aoGeneologyChain
        #
        # aoGeneologyChain = []
        # for i in range(100):
        #     aoGeneologyChain.append(archival_object)
        #     try:
        #         parentUri = archival_object['parent']['ref']
        #     except KeyError:
        #         self.aoGeneologyChain = wrapUp(aoGeneologyChain)
        #     archival_object = aspace.get(parentUri)
        # self.aoGeneologyChain = wrapUp(aoGeneologyChain)

        # restructuring
        newGeneologyChain = dict()
        newGeneologyChain['object'] = archival_object
        newGeneologyChain['parents'] = []
        newGeneologyChain['resource'] = getResource(archival_object)
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

    def getSubjectsInherited(self):
        '''Get subject data from either the current Archival Object, its parent
        Archival Objects, or the Resource Record. 'Lazily' i.e. stop as soon as
        I find subjects as I traverse up the geneology chain.
        '''
        subjects = self.lazyFind('subjects')
        return subjects

    def getAgentsInherited(self):
        """Get agents running up the inheritance chain handling them
        independently by type: creator, source, subject.
        """
        # agentsAnyType = self.lazyFind('linked_agents')

        agents = {}
        # Sort agents out into their roles for different uses in the MARC record
        agents['creators'] = []
        agents['donors'] = []
        agents['subjects'] = []
        agents['creators'] = mychain.TEST_lazySubFind('linked_agents', subtypeFieldName='linked_agent_roles', subtype='creator')
        agents['donors'] = mychain.TEST_lazySubFind('linked_agents', subtypeFieldName='linked_agent_roles', subtype='source')
        agents['subjects'] = mychain.TEST_lazySubFind('linked_agents', subtypeFieldName='linked_agent_roles', subtype='subject')
#        pprint.pprint(agents)

        # for agent in agentsAnyType:
        #     for role in agent['linked_agent_roles']:
        #         if role == 'creator':
        #             agents['creators'].append(agent)
        #         if role == 'source':
        #             agents['donors'].append(agent)
        #         if role == 'subject':
        #             agents['subjects'].append(agent)
        return agents

    def getNotesByType(self, noteType):
        '''Traverse all parent AOs and the Resource Record and get all the
        notes of given type
        '''
        notes = []
        for archival_object in self.aoGeneologyChain:
            try:
                for note in archival_object['notes']:
                    if note['type'] == noteType:
                        notes.append(note)
            except KeyError:
                pass
        return notes

    def getAllNotes(self):
        # Get list of controled values for note types
        enums = aspace.get(NOTETYPESURI)
        noteTypeS = enums['values']
        notes = dict()
        for noteType in noteTypeS:
            notes[noteType] = self.getNotesByType(noteType)
        return notes


mychain = AoGeneologyChain(archival_object)


# Traverse all parent AOs and the Resource Record and get their subjects
subjects = mychain.getSubjectsInherited()
agents = mychain.getAgentsInherited()


# Debug
# pprint.pprint(agents)
#import pdb; pdb.set_trace()

# Get genre data
# Get agent data
# Get notes data
#allNotes = mychain.getNotes()
# notesToPublish = dict()
# notesToPublish['accessrestrict'] = []
#
# try:
#     notesToPublish['accessrestrict'].append(allNotes['accessrestrict'][0])
#     notesToPublish['accessrestrict'].append(allNotes['accessrestrict'][-1])
# except KeyError:
#     pass


# Compile all the data into a big structure for jinja
data = {'archival_object': archival_object, 'resource': resource, 'repository': repository, 'subjects': subjects, 'agents': agents, 'collecting_unit': collecting_unit, 'ms_no': ms_no}

# Set up jinja loader and template objects
templateLoader = jinja2.FileSystemLoader(searchpath=".")
templateEnv = jinja2.Environment(loader=templateLoader)

# Merge the template and data
template = templateEnv.get_template('compass-mods-template.xml')
print(template.render(data))

# Write the file?
