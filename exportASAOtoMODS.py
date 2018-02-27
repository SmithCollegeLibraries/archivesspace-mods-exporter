from archivesspace import archivesspace
import jinja2
import pprint
from utilities import *
aspace = archivesspace.ArchivesSpace('http', 'aspace.smith.edu', '9999', 'tchambers', 'changeme')
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
# archival_object = aspace.requestGet('/repositories/2/archival_objects/105443')
archival_object = aspace.requestGet('/repositories/2/archival_objects/159445')
# Find the AO's parent resource
# 845
def getResource(archival_object):
    'Get the Resource Record of a given Archival Object'
    resource_uri = archival_object['resource']['ref']
    resource = aspace.requestGet(resource_uri)
    return resource
resource = getResource(archival_object)

# Find the parent repo
def getRepository(archival_object):
    'Get the repository of a given Archival Object'
    repository_uri = archival_object['repository']['ref']
    repository = aspace.requestGet(repository_uri)
    return repository
repository = getRepository(archival_object)

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
        #     archival_object = aspace.requestGet(parentUri)
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
            archival_object = aspace.requestGet(parentUri)
            newGeneologyChain['parents'].append(archival_object)
        self.newGeneologyChain = newGeneologyChain

    def __repr__(self):
        return(pprint.pformat(self.newGeneologyChain))

    def dereferenceRefs(self, archival_object, elementsName):
        '''Dereference references from a given Archival Object or Resource Record
        and load data into a list.
        '''
        elements = []
#        import pdb; pdb.set_trace()
        try:
            for element in archival_object[elementsName]:
                elementData = aspace.requestGet(element['ref'])
                elements.append(elementData)
        except KeyError:
            pass
        return elements

    def lazyFind(self, type):
        list = []
        
        list.extend(self.dereferenceRefs(self.newGeneologyChain['object'], type))
        if list:
            return list
        for archival_object in self.newGeneologyChain['parents']:
            list.extend(self.dereferenceRefs(archival_object, type))
            if list:
                return list
        list.extend(self.dereferenceRefs(self.newGeneologyChain['resource'], type))
        return list

    def getSubjectsConstelation(self):
        '''Get subject data from either the current Archival Object, its parent
        Archival Objects, or the Resource Record. 'Lazily' i.e. stop as soon as
        I find subjects as I traverse up the geneology chain.
        '''
        subjects = self.lazyFind('subjects')
        return subjects

    def getAgentsConstelation(self):
        agentsAnyType = self.lazyFind('linked_agents')
        agents = {}
        # Sort agents out into their roles for different uses in the MARC record
        agents['creators'] = []
        agents['donors'] = []
        agents['subjects'] = []
        for agent in agentsAnyType:
            for role in agent['linked_agent_roles']:
                if role == 'creator':
                    agents['creators'].append(agent)
                if role == 'source':
                    agents['donors'].append(agent)
                if role == 'subject':
                    agents['subjects'].append(agent)
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
        enums = aspace.requestGet(NOTETYPESURI)
        noteTypeS = enums['values']
        notes = dict()
        for noteType in noteTypeS:
            notes[noteType] = self.getNotesByType(noteType)
        return notes

mychain = AoGeneologyChain(archival_object)


# Traverse all parent AOs and the Resource Record and get their subjects
subjects = mychain.getSubjectsConstelation()
agents = mychain.getAgentsConstelation()
# Debug
pprint.pprint(agents['subjects'])
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
data = { 'archival_object': archival_object, 'resource': resource, 'repository': repository, 'subjects': subjects, 'agents': agents }

# Set up jinja loader and template objects
templateLoader = jinja2.FileSystemLoader( searchpath="." )
templateEnv = jinja2.Environment( loader=templateLoader )

# Merge the template and data
template = templateEnv.get_template( 'compass-mods-template.xml' )
print(template.render( data ))

# Write the file?
