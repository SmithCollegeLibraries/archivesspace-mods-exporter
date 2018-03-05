# About

# Usage

# Acceptance Criteria
Does the script generate a valid MODS XML file?
Does the output map data from the appropriate ArchivesSpace records? (see documentation)
Does the output contain all of the relevant fields? (see documentation)
Does the output fallback to the appropriate ancestor data element? (see documentation)
Can the XML template file be tweaked by a non-coder?
Is there an automated test to verify that the tool is functional?
Can I pass the tool a list of AS digital object ids to be fetched?

# Project Completion
[x] Query AS
[x] Set up jinja2 templater
[x] Output MODS XML
[x] Title
[x] Subjects with inheritance logic
[ ] Agents as creator, donor, subject with inheritance logic
[ ] Notes
[ ] Misc remaining flat fields
[ ] Select group of items to be exported Output as file?
[ ] or Turn into module that can be used by a processing script
[ ] Save to a file?
[ ] Sample data importer so I can write doctests

# Mapping
https://github.com/smith-special-collections/sc-documentation/wiki/Mapping-archival-and-bibliographic-metadata-schemas-to-Compass-MODS

# Description inheritance logic
https://github.com/smith-special-collections/sc-documentation/wiki/Rules-for-description-inheritance-for-digital-object-records

# Test plan
## Setup
Create a Resource Record (Record Group)
Create an Archival Object as child of Resource Record (Series)
Create an Archival Object as child of the Series (Sub-Series)
Create an Archival Object as child of the Sub-Series (File)
Create a Digital Object as child of the Sub-Series Archival Object

## Basic test (title)
1. When I export a digital object record does the output contain MODS XML and does the title element contain the title of the Archival Object (not the digital object?)

## Subject tests
https://github.com/smith-special-collections/sc-documentation/wiki/Rules-for-description-inheritance-for-digital-object-records

1. If I export a digital object and it does not have directly associated subjects, but its parent Archival Object or Resource Record has subjects associated with it,
Does the output XML contain subjects with the subject names from the parent Archival Object or Resource Record?

2. If I export a Digital Object and it has subjects directly associated with it,
Does the output XML contain only subjects with the subject names from the digital object, and not those from the parent Archival Object or Resource Record?

## Teardown
...

# Scratch
