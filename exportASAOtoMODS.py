from archivesspace import archivesspace
import jinja2
import pprint
from utilities import *
aspace = archivesspace.ArchivesSpace('http', 'aspace.smith.edu', '9999', 'tchambers', 'changeme')
aspace.connect()

# Retrieve the DO
# Find the DO's parent AO
archival_object = aspace.requestGet('/repositories/2/archival_objects/105443')
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
        def wrapUp(aoGeneologyChain):
            resource = getResource(archival_object)
            aoGeneologyChain.append(resource)
            return aoGeneologyChain

        aoGeneologyChain = []
        for i in range(100):
            aoGeneologyChain.append(archival_object)
            try:
                parentUri = archival_object['parent']['ref']
            except KeyError:
                self.aoGeneologyChain = wrapUp(aoGeneologyChain)
            archival_object = aspace.requestGet(parentUri)
        self.aoGeneologyChain = wrapUp(aoGeneologyChain)

    def getSubjects(self):
        '''Get subject data by merging subjects from the Archival Object and its
        parent archival objects.
        '''
        subjects = []
        for archival_object in self.aoGeneologyChain:
            try:
                for subject in archival_object['subjects']:
                    subjectData = aspace.requestGet(subject['ref'])
                    subjects.append(subjectData)
            except KeyError:
                pass
        return subjects

    def getNotesByType(self, noteType):
        '''Traverse all parent AOs and the Resource Record and get all the notes of
        given type
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

    def getNotes(self):
        # Get list of controled values for note types
        enums = aspace.requestGet('/config/enumerations/45')
        noteTypeS = enums['values']
        notes = dict()
        for noteType in noteTypeS:
            notes[noteType] = self.getNotesByType(noteType)
        return notes

mychain = AoGeneologyChain(archival_object)


# Traverse all parent AOs and the Resource Record and get their subjects
subjects = mychain.getSubjects()

# Debug
#pprint.pprint(subjects)

# Get genre data
# Get agent data
# Get notes data
allNotes = mychain.getNotes()
notesToPublish = dict()
notesToPublish['accessrestrict'] = []

try:
    notesToPublish['accessrestrict'].append(allNotes['accessrestrict'][0])
    notesToPublish['accessrestrict'].append(allNotes['accessrestrict'][-1])
except KeyError:
    pass

import pdb; pdb.set_trace()

# Compile all the data into a big structure for jinja
data = { 'archival_object': archival_object, 'resource': resource, 'repository': repository, 'subjects': subjects }

# Set up jinja loader and template objects
templateLoader = jinja2.FileSystemLoader( searchpath="." )
templateEnv = jinja2.Environment( loader=templateLoader )

# Merge the template and data
template = templateEnv.get_template( 'compass-mods-template.xml' )
print(template.render( data ))

# Write the file?
