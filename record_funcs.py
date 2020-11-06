from asnake.aspace import ASpace
import logging
import re
import html
from pprint import pprint as pp



class aspaceRecordFuncs(object):
    def __init__(self, aspace):
        self.aspace = aspace


    def getBoxString(self, top_container):
        'Get the Shelf Location of a given Archival Object'
        try:
            return top_container['display_string']
        except KeyError:
            return None


    def getFolder(self, archival_object):
        'Gets the folder if there is one of an Archival Object'

        logging.debug('Retrieving folder of Archival Object %s' % archival_object['uri'])
        try:
            fol = archival_object['instances'][0]['sub_container']['type_2'].capitalize()
            num = archival_object['instances'][0]['sub_container']['indicator_2']
        except KeyError:
            return None

        return fol + " " + num


    def getCollectingUnit(self, digital_object): # Can hard code this
        'Get the repository of a given Archival Object'

        logging.debug('Retrieving Repository of Archival Object %s' % digital_object['uri'])
        repository_uri = digital_object['uri'].split('/digital_objects')[0]
        if repository_uri == '/repositories/2':
            repository = "Sophia Smith Collection of Women's History"
        elif repository_uri == '/repositories/3':
            repository = "Mortimer Rare Book Collection"
        elif repository_uri == '/repositories/4':
            repository = "Smith College Archives"
        
        return repository


    def getParentInstitution(self):
        'Get the collecting unit of a given Archival Object'
        name = 'Smith College Special Collections'
        return name


    def getMsNo(self, resource):
        'Get the MS number of a given Archival Object'

        logging.debug('Retrieving MS number of Archival Object %s' % resource['uri'])
        try:
            id_1 = resource['id_1']
            id_2 = resource['id_2']
            ms_no = id_1 + ' ' + id_2
        except KeyError:
            ms_no = 'MS' + ' ' + resource['id_0'][:3]

        return ms_no    


    def getModsFileName(self, do_json):
        'Returns file name in format islandora_NUMBER_MODS'
        'Assumes that if multiple file version URLs to Compass exist, all are identical'
        'Asummes will work even if URL is written differently'

        logging.debug('Returning file name for %s in format: islandora_NUMBER_MODS' % do_json['digital_object_id'])
        regex = '(smith:+?\d+)'
        uris = [uri['file_uri'] for uri in do_json['file_versions'] if 'compass' in uri['file_uri']]
        uri = uris[0] # Takes first URL of list
        islandora_pid = re.search(regex, uri).group()
        formatted_islandora_pid = islandora_pid.replace(':', '_')
        mods_file_name = formatted_islandora_pid + '_MODS'

        return mods_file_name


    def getSubjects(self, archival_object_subjects):
        'Modifies list of subjects for an Archival Object with proper authority id formatting'

        for sub in archival_object_subjects:
            if 'authority_id' in sub.keys():
                if sub['source'] == 'lcsh':
                    if not 'loc.gov' in sub['authority_id']:
                        sub['authority_id'] = 'http://id.loc.gov/authorities/subjects/' + sub['authority_id']
                elif sub['source'] == 'lcnaf':
                    if not 'loc.gov' in sub['authority_id']:
                        sub['authority_id'] = 'http://id.loc.gov/authorities/names/' + sub['authority_id']
                elif sub['source'] == 'naf':
                    if not 'loc.gov' in sub['authority_id']:
                        sub['authority_id'] = 'http://id.loc.gov/authorities/names/' + sub['authority_id']
                elif sub['source'] == 'tgn':
                    if not 'getty.edu' in sub['authority_id']:
                        sub['authority_id'] = 'http://vocab.getty.edu/tgn/' + sub['authority_id']
                elif sub['source'] == 'aat':
                    if not 'getty.edu' in sub['authority_id']:
                        sub['authority_id'] = 'http://vocab.getty.edu/aat/' + sub['authority_id']
                else:
                    continue

        archival_object_subjects = [i for n, i in enumerate(archival_object_subjects) if i not in archival_object_subjects[n + 1:]]
        return archival_object_subjects


    def getGenreSubjects(self, archival_object_subjects):
        'Gets genre_form type subjects for Archival Object if they exist'

        genre_subs = []
        for subject in archival_object_subjects:
            if subject['terms'][0]['term_type'] == 'genre_form':
                genre_subs.append(subject)
        
        genre_subs = [i for n, i in enumerate(genre_subs) if i not in genre_subs[n + 1:]]

        return genre_subs


    def removeGenreSubjects(self, archival_object_subjects):
        'Deleting Genre subjects from Archival Object Subjects list because requires different tags than other subjects in template'

        non_genre_subs = []
        for sub in archival_object_subjects:
            if not sub['terms'][0]['term_type'] == 'genre_form':
                non_genre_subs.append(sub)

        return non_genre_subs 


    def removeEADTags(self, note):
        regex = '(<.*?>)'
        for n in note:
            n['content'] = html.unescape(n['content'])
            chars_to_remove = re.findall(regex, n['content'])
            if len(chars_to_remove) > 0:
                for char in chars_to_remove:
                    n['content'] = n['content'].replace(char, "")
            n['content'] = html.escape(n['content']) 

        return note


    def getNoteTup(self, note):
        if 'type' in note.keys():
            if 'content' in note.keys():
                tup = (note['type'], note['content'])
            else:
                tup = (note['type'], note['subnotes'])

            return tup
        
        else:
            return None


    def getNotesByResource(self, resource):
        'Returns a list of tuples of all the notes from a Resource'

        note_tups = []
        if 'notes' in resource.keys():
            notes = resource['notes']
            for note in notes:
                logging.debug('Retrieving available notes from the Resource of %s' % resource['uri'])
                try:
                    tup = self.getNoteTup(note)
                    if tup != None:
                        note_tups.append(tup)
                except Exception as e:
                    logging.error(e)

        return note_tups


    def getNotesTree(self, archival_object, resource):
        'Returns a list of tuples of all the notes from an Archival Object heirarchy'
        
        logging.debug('Returning list of tuples of all notes from Archival Object %s heirarchy' % archival_object['uri'])
        note_tups = []
        if 'notes' in archival_object.keys():
            notes = archival_object['notes']
            for note in notes:
                logging.debug('Retrieving available notes from %s' % archival_object['uri'])
                try:
                    tup = self.getNoteTup(note)
                    if tup != None:
                        note_tups.append(tup)
                except Exception as e:
                    logging.error(e)

            resource_notes = self.getNotesByResource(resource)
            note_tups.extend(resource_notes)

        return note_tups


    def getNotesByType(self, note_tups, notetype):
        ' Returns the dictionary for a specified note type; works in conjunction with getNotesTree '
        
        logging.debug('Retrieving notes by type %s from list of note tuples generated in getNotesTree' % notetype)
        for note in note_tups:
            logging.debug('Iterating over list of notes to retrieve %s type notes if they exist' % notetype)
            if note[0] == notetype:
                return self.removeEADTags(note[1])


    def getLangAtAOLevel(self, archival_object, resource):
        obj_langs = []
        try:
            if len(archival_object['lang_materials']) != 0:
                try:
                    for lang in archival_object['lang_materials']:
                        obj_langs.append(lang['language_and_script']['language'])
                except:
                    obj_langs.append(archival_object['lang_materials'][0]['notes'][0]['content'][0])
            elif len(archival_object['lang_materials']) == 0:
                for lang in resource['lang_materials']:
                    obj_langs.append(lang['language_and_script']['language'])
            else:
                note_tups = self.getNotesTree(archival_object, resource)
                lang_notes = self.getNotesByType(note_tups, 'langmaterial')
                for lang in lang_notes:
                    langs = lang.split(';')
                    for lang in langs:
                        if lang == 'The primary language of the materials is English.':
                            lang = 'English'
                            obj_langs.append(lang)
                        else:
                            obj_langs.append(lang)
        except Exception as e:
            logging.debug(e)

        return obj_langs


    def filterSubjectAgents(self, agents_list):
        filtered_agents = []
        for agent in agents_list:
            if agent['role'] == 'subject':
                continue
            else:
                filtered_agents.append(agent)

        return filtered_agents


    def add_excerpts_to_title(self, notes):
        processinfo = self.getNotesByType(notes, 'processinfo')
        if processinfo != None:
            if 'select material' in processinfo[0]['content'].lower():
                return True


 
if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    aspace = ASpace()
