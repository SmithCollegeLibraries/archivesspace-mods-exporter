# About

Tools for syncing metadata from ArchivesSpace to Islandora for the YWCA digitization project at Smith College Special Collections. NOTICE: this toolset was developed specifically for one institution's metadata practices and morover in the context of a specific project. If you chose to use this code YMMV!

## Mapping
https://github.com/smith-special-collections/sc-documentation/wiki/Mapping-archival-and-bibliographic-metadata-schemas-to-Compass-MODS

## Description inheritance logic
https://github.com/smith-special-collections/sc-documentation/wiki/Rules-for-description-inheritance-for-digital-object-records

# Set up
## Requirements
```
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

Hence forth before using these tools you should execute `source venv/bin/activate` to enable the python virtual environment.

### Install archivesspace Python module
```
git clone https://github.com/SmithCollegeLibraries/archivesspace-python.git
mv archivesspace-python archivesspace
cd archivesspace
git checkout v0.0.4 # At the time of writing. This version may change! TODO: Keep this updated
```

## Configure `archivesspace.cfg`
Copy `archivesspace-example.cfg` to `archivesspace.cfg` then edit the file to reflect your environment and account credentials.

# Usage
## Use `digitalobjecturiadd.py` to add URLs to your digital objects in ArchivesSpace

```
python3 digitalobjecturiadd.py --help
python3 digitalobjecturiadd.py newphotopids.json test
```

### Generating JSON file for digitalobjecturiadd.py
This is used to add the Islandora URI as a File Version to the corresponding ArchivesSpace digital object record. The Islandora URI is necessary in order to generate the proper file name for the XML exporter.

1. Log into VPN
2. Go to the SOLR admin panel: http://compass-fedora-prod.fivecolleges.edu:8080/solr/#/
3. Enter desired query, such as:
- q: RELS_EXT_isMemberOfCollection_uri_t:"smith\:ssc--ms0324rg9" fl: PID, mods_identifier_local_s, mods_titleInfo_title_s (this one retrieves the PID, local id, and title for all digital objects in the YWCA U.S.A photographic collection)
4. Set wt field to ‘json’
5. To save JSON file: 
- In the command line, write: curl “URL of JSON output” > filename.json

## Use `exportASAOtoMODS.py` to export the metadata from those records into MODS.xml files

```
python3 exportASAOtoMODS.py --help
mkdir myoutputdir
python3 exportASAOtoMODS.py myoutputdir 676 test
```





























# \/ SCRATCH SPACE \/

# Acceptance Criteria
- Does the script generate a valid MODS XML file?
- Does the output map data from the appropriate ArchivesSpace records? (see documentation)
- Does the output contain all of the relevant fields? (see documentation)
- Does the output fallback to the appropriate ancestor data element? (see documentation)
- Can the XML template file be tweaked by a non-coder?
- Is there an automated test to verify that the tool is functional?
- Can I pass the tool a list of AS digital object ids to be fetched?

# Project Completion
[x] Query AS
[x] Set up jinja2 templater
[x] Output MODS XML
[x] Title
[x] Subjects with inheritance logic
[ ] Agents inheritance logic as creator, donor, subject
[ ] Notes
[ ] Misc remaining flat fields
[ ] Digital object starting point
[ ] Select group of items to be exported Output as file?
[ ] or Turn into module that can be used by a processing script
[ ] Save to a file?
[ ] Sample data importer so I can write doctests

# Test plan
## Setup
Create a Resource Record (Record Group)
Create an Archival Object as child of Resource Record (Series)
Create an Archival Object as child of the Series (Sub-Series)
Create an Archival Object as child of the Sub-Series (File)
Create a Digital Object as child of the Sub-Series Archival Object

## Basic test (title)
1. When I export a digital object record does the output contain MODS XML and does the title element contain the title of the Archival Object (not the digital object)?

## Subject tests
https://github.com/smith-special-collections/sc-documentation/wiki/Rules-for-description-inheritance-for-digital-object-records

1. If I export a digital object and it does not have directly associated subjects, but its parent Archival Object or Resource Record has subjects associated with it,
Does the output XML contain subjects with the subject names from the parent Archival Object or Resource Record?

2. If I export a Digital Object and it has subjects directly associated with it,
does the output XML contain only subjects with the subject names from the digital object, and not those from the parent Archival Object or Resource Record?

## Agents tests

1. If I link an agent record as a creator to a parent Archival Object and the Resource Record -- does the output XML contain that agent of the parent Archival Object, but not the Resource Record?

1. Assuming the above conditions if I link an agent as a source to a parent Archival Object or the Resource Record -- does the output XML contain that source agent of the parent Archival Object, or Resource Record, AND the creator agent from the Archival Object?

1. If I link an agent record as a source, subject, or creator to a parent Archival Object and the Resource Record -- does the output XML contain that agent of the parent Archival Object, but not the Resource Record?

2. If I link an agent to a Digital Object record and also to a parent level such as Archival Object or Resource Record -- does the output XML contain that agent of the Digital Object record but not the Archival Object, or Resource Record?

## Teardown
...

# Old Next steps:
- Creators: Leslie missing
- Donors: Margaret is showing
- wiki rules text wrong. last sentence.
