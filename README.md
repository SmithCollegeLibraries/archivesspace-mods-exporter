Does the script generate a valid MODS XML file?
Does the output map data from the appropriate ArchivesSpace records? (see documentation)
Does the output contain all of the relevant fields? (see documentation)
Does the output fallback to the appropriate ancestor data element? (see documentation)
Can the XML template file be tweaked by a non-coder?
Is there an automated test to verify that the tool is functional?
Can I pass the tool a list of AS digital object ids to be fetched?

# Links
https://github.com/smith-special-collections/sc-documentation/wiki/Mapping-archival-and-bibliographic-metadata-schemas-to-Compass-MODS

[x] Subjects
[ ] Agents
[ ] Title, Abstract, etc.
[ ] Select group of items to be exported
[ ] Notes
[ ] Sample data importer so I can write doctests

# Test plan
## Setup
Create a Resource Record (Record Group)
Create an Archival Object as child of Resource Record (Series)
Create an Archival Object as child of the Series (Sub-Series)
Create an Archival Object as child of the Sub-Series (File)
Create a Digital Object as child of the Sub-Series Archival Object

## Subject tests
https://github.com/smith-special-collections/sc-documentation/wiki/Rules-for-description-inheritance-for-digital-object-records

1. If I export a digital object and it does not have directly associated subjects, but its parent Archival Object or Resource Record has subjects associated with it,
Does the output XML contain subjects with the subject names from the parent Archival Object or Resource Record?

2. If I export a Digital Object and it has subjects directly associated with it,
Does the output XML contain only subjects with the subject names from the digital object, and not those from the parent Archival Object or Resource Record?

## Teardown
...

# Scratch
