from asnake.aspace import ASpace
import logging



class aspaceRecordFuncs(object):
    def __init__(self, aspace):
        self.aspace = aspace


    def getShelfLocation(self, archival_object):
        'Get the Shelf Location of a given Archival Object'

        logging.debug('Retrieving Shelf Location of Archival Object %s' % archival_object['uri'])
        try:
            top_container_uri = archival_object['instances'][0]['sub_container']['top_container']['ref']
            top_container = self.aspace.client.get(top_container_uri).json()
        except KeyError:
            return None

        return top_container['display_string']


    def getFolder(self, archival_object):
        'Gets the folder if there is one of an Archival Object'

        logging.debug('Retrieving folder of Archival Object %s' % archival_object['uri'])
        try:
            fol = archival_object['instances'][0]['sub_container']['type_2'].capitalize()
            num = archival_object['instances'][0]['sub_container']['indicator_2']
        except KeyError:
            return None

        return fol + " " + num


    def getRepository(self, digital_object): # Can hard code this
        'Get the repository of a given Archival Object'

        logging.debug('Retrieving Repository of Archival Object %s' % digital_object['uri'])
        repository_uri = digital_object['uri'].split('/digital_objects')[0]
        repository = self.aspace.client.get(repository_uri).json()
        
        return repository


    def getCollectingUnit(self, repository):
        'Get the collecting unit of a given Archival Object'

        return repository['name']


    def getMsNo(self, archival_object, resource):
        'Get the MS number of a given Archival Object'

        logging.debug('Retrieving MS number of Archival Object %s' % archival_object['uri'])
        try:
            id_1 = resource['id_1']
            id_2 = resource['id_2']
            ms_no = id_1 + ' ' + id_2
        except KeyError:
            ms_no = 'MS' + ' ' + resource['id_0'][:3]

        return ms_no    


    def getModsFileName(self, do_json):
        'Returns file name in format islandora_NUMBER_MODS'

        logging.debug('Returning file name for %s in format: islandora_NUMBER_MODS' % do_json['digital_object_id'])
        try:
            uri = do_json['file_versions'][0]['file_uri']
            split_uri = uri.split('/')
            islandora_pid = split_uri[-1]
            formatted_islandora_pid = islandora_pid.replace(':', '_')
            mods_file_name = formatted_islandora_pid + '_MODS'
        except:
            mods_file_name = 'did_not_work'

        return mods_file_name


    def getSubjects(self, archival_object):
        'Returns list of subjects for an Archival Object'
        'Only looking at Archival Object level -- NOT getting them from the hierarchy because all YWCA AOs with Digital Objects have subjects at the AO level'
        
        logging.debug('Retrieving Subject list from %s' % archival_object['uri'])
        sub_list = []
        subjects = archival_object['subjects']
        for subject in subjects:
            sub = subject['ref']
            sub_rec = self.aspace.client.get(sub).json()
            sub_list.append(sub_rec)

        for sub in sub_list:
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

        return sub_list


    def getGenreSubjects(self, subjects):
        'Gets genre_form type subjects for Resource'

        genre_subs = []
        for subject in subjects:
            if subject['terms'][0]['term_type'] == 'genre_form':
                genre_subs.append(subject)
     

        return genre_subs


    def removeGenreSubjects(self, subjects):
        'Deleting Genre subjects from AllSubjects list because requires different tags than other subjects in template'

        non_genre_subs = []
        for sub in subjects:
            if not sub['terms'][0]['term_type'] == 'genre_form':
                non_genre_subs.append(sub)

        return non_genre_subs        


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

            if 'parent' in archival_object.keys():
                parent = archival_object['parent']['ref']
                parent_record = self.aspace.client.get(parent).json()
                if 'notes' in parent_record.keys():
                    notes = parent_record['notes']
                    for note in notes:
                        logging.debug('Retrieving available notes from parent of %s' % archival_object['uri'])
                        try:
                            tup = self.getNoteTup(note)
                            if tup != None:
                                note_tups.append(tup)
                        except Exception as e:
                            logging.error(e)

                if 'parent' in parent_record.keys():
                    grandparent = parent_record['parent']['ref']
                    grandparent_record = self.aspace.client.get(grandparent).json()
                    if 'notes' in grandparent_record.keys():
                        notes = grandparent_record['notes']
                        for note in notes:
                            logging.debug('Retrieving available notes from grandparent of %s' % archival_object['uri'])
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
                return note[1]


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


    def findKey(self, d, key):
        """Find all instances of key."""
        if key in d:
            yield d[key]
        for k in d:
            if isinstance(d[k], list) and k == 'children':
                for i in d[k]:
                    for j in self.findKey(i, key):
                        yield j


    def get_all_archival_object_uris_for_resource(self, resource, repo_num):
        endpoint = f'/repositories/{repo_num}/resources/{resource}/tree'
        output = self.aspace.client.get(endpoint).json()
        uris = []
        uris.append(output['record_uri'])
        for value in self.findKey(output, 'record_uri'):
            if 'archival_objects' in value:
                uris.append(value)

        return uris


    def getAgents(self, archival_object):
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
            agent_dct['data'] = self.aspace.client.get(uri).json()
            new_agents_lst.append(agent_dct)

        for agent in new_agents_lst:
            if agent['role'] == 'creator' or agent['role'] == 'source' or agent['role'] == 'subject':
                if agent['data']['jsonmodel_type'] == 'agent_person':
                    agent['data']['jsonmodel_type'] = 'personal'
                elif agent['data']['jsonmodel_type'] == 'agent_corporate_entity':
                    agent['data']['jsonmodel_type'] = 'corporate'
                elif agent['data']['jsonmodel_type'] == 'agent_family':
                    agent['data']['jsonmodel_type'] = 'family'
                else:
                    continue

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


    def getParentRecords(self, archival_object):
        parent_uris = []
        for i in range(100):
            try:
                parentUri = archival_object['parent']['ref']
            except KeyError:
                break
            parent_ao = self.aspace.client.get(parentUri).json()
            if parent_ao['uri'] not in parent_uris:
                parent_uris.append(parent_ao['uri'])

        parent_records = []
        for uri in parent_uris:
            parent_record = self.aspace.client.get(uri).json()
            parent_records.append(parent_record)

        return parent_records


    def filterSubjectAgents(self, agent_list):
        filtered_agents = []
        for agent in agent_list:
            if agent['role'] == 'subject':
                continue
            else:
                filtered_agents.append(agent)

        return filtered_agents


    def getInheritedAgents(self, archival_object, resource):
        '''Gets all agents from parent records apart from agents as subjects'''
        all_agents = []

        resource_agents = self.getAgents(resource)
        all_agents.extend(resource_agents)

        ao_agents = self.getAgents(archival_object)
        all_agents.extend(ao_agents)

        parent_records = self.getParentRecords(archival_object)
        for record in parent_records:
            parent_agents = self.getAgents(record)
            all_agents.extend(parent_agents)

        filtered_agents = self.filterSubjectAgents(all_agents)
        return filtered_agents


 
if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    aspace = ASpace()
