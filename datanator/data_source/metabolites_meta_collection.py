from datanator_query_python.query import query_sabiork, query_xmdb
from datanator.util import chem_util
from datanator.util import file_util
from datanator.util import index_collection
import datanator.config.core
import pymongo
import re
from pymongo.collation import Collation, CollationStrength


class MetabolitesMeta(query_sabiork.QuerySabio):
    ''' meta_loc: database location to save the meta collection
    '''

    def __init__(self, cache_dirname=None, MongoDB=None, replicaSet=None, db=None,
                 verbose=False, max_entries=float('inf'), username = None, 
                 password = None, authSource = 'admin', meta_loc = None):
        self.cache_dirname = cache_dirname
        self.verbose = verbose
        self.MongoDB = MongoDB
        self.replicaSet = replicaSet
        self.max_entries = max_entries
        self.username = username
        self.password = password
        self.authSource = authSource
        self.meta_loc = meta_loc
        super(MetabolitesMeta, self).__init__(cache_dirname=cache_dirname, MongoDB=MongoDB, replicaSet=replicaSet,
                                              db=db, verbose=verbose, max_entries=max_entries, username = username,
                                              password = password, authSource = authSource)
        self.frequency = 50
        self.chem_manager = chem_util.ChemUtil()
        self.file_manager = file_util.FileUtil()
        self.ymdb_query = query_xmdb.QueryXmdb(username=username, password=password, server=MongoDB, authSource=authSource,
                                        database=db, collection_str='ymdb', readPreference='nearest')
        self.ecmdb_query = query_xmdb.QueryXmdb(username=username, password=password, server=MongoDB, authSource=authSource,
                                        database=db, collection_str='ecmdb', readPreference='nearest')
        self.collation = Collation('en', strength=CollationStrength.SECONDARY)
        self.client, self.db, self.collection = self.con_db('metabolites_meta')

    def load_content(self):
        collection_name = 'metabolites_meta'

        ecmdb_fields = ['m2m_id', 'inchi', 'synonyms.synonym']
        self.fill_metabolite_fields(
            fields=ecmdb_fields, collection_src='ecmdb', collection_des = collection_name)

        ymdb_fields = ['ymdb_id', 'inchi', 'synonyms.synonym']
        self.fill_metabolite_fields(
            fields=ymdb_fields, collection_src='ymdb', collection_des = collection_name)

        _, _, collection = self.con_db(collection_name)
        k = 0
        for doc in self.collection.find(filter={}, projection={'inchi':1}):
            if k > self.max_entries:
                break
            kinlaw_id = self.get_kinlawid_by_inchi([doc['inchi']])
            rxn_participants = self.find_reaction_participants(kinlaw_id)
            collection.update_one({'inchi': doc['inchi']},
                                  {'$set': {'kinlaw_id': kinlaw_id,
                                   'reaction_participants': rxn_participants}},
                                  upsert=False)
            k += 1
        # i = 0
        # cursor = collection.find(filter = {}, projection = {'similar_compounds_corrected':1, 'similar_compounds': 1})
        # for doc in cursor:
        #     if i % self.frequency == 0:
        #         print(i)

        #     replacement = []
        #     for corrected in doc['similar_compounds_corrected']:
        #         for k, v in corrected.items():
        #             dic = {}
        #             dic[k] = v
        #             replacement.append(dic)

        #     collection.update_one({'_id': doc['_id']},
        #                          {'$set': {'similar_compounds': replacement}},
        #                         upsert=False)
        #     i += 1

    def replace_key_in_similar_compounds(self):
        query = {}
        projection = {'similar_compounds': 1}
        _, _, col = self.con_db('metabolites_meta')
        docs = col.find(filter=query, projection=projection)
        for doc in docs:
            result = []
            _list = doc['similar_compounds']
            for dic in _list:
                old_key = list(dic.keys())[0]
                try:
                    new_key = col.find_one(filter={'inchi': old_key}, 
                        projection={'InChI_Key':1})['InChI_Key']
                    result.append( {new_key: dic[old_key]})
                except TypeError:
                    result.append( {'NoStructure': -1} )
            col.update_one({'_id': doc['_id']},
                {'$set': {'similar_compounds': result} })
        

    def fill_metabolite_fields(self, fields=None, collection_src=None, collection_des = None):
        '''Fill in values of fields of interest from 
            metabolite collection: ecmdb or ymdb
                Args:
                        fileds: list of fields of interest
                        collection_src: collection in which query will be done
                        collection_des: collection in which result will be updated

        '''
        projection = {}
        for field in fields:
            projection[field] = 1
        projection['_id'] = 0
        _, _, col_src = self.con_db(collection_src)
        _, _, col_des = self.con_db(collection_des)
        cursor = col_src.find(filter={}, projection=projection)
        i = 0
        for doc in cursor:
            if i == self.max_entries:
                break
            if i % self.frequency == 0:
                print('Getting fields of interest from {} document in {}'.format(i, collection_src))
            doc['InChI_Key'] = self.chem_manager.inchi_to_inchikey(doc['inchi'])
            if isinstance(doc.get('synonyms'), list):
                continue
            try:
                synonyms = doc.get('synonyms', None).get('synonym')
            except AttributeError:
                synonyms = doc.get('synonyms', None)
            col_des.update_one({'inchi': doc['inchi']},
                                  { '$set': { fields[0]: doc[fields[0]],
                                              fields[1]: doc[fields[1]],
                                              'synonyms': synonyms,
                                              'InChI_Key': doc['InChI_Key']}},
                                  upsert=True)
            i += 1


    def fill_names(self):
        """Fill names of metabolites in 'name' field
        """
        docs = self.collection.find({})
        count = self.collection.count_documents({})
        for i, doc in enumerate(docs):
            name = ''
            inchi_key = doc['InChI_Key']
            if i == self.max_entries:
                break
            if i % 100 == 0 and self.verbose:
                print('Adding name to document {} out of {}.'.format(i, count))
            if doc.get('ymdb_id') is None:
                name = self.ecmdb_query.get_name_by_inchikey(inchi_key)
            else:
                name = self.ymdb_query.get_name_by_inchikey(inchi_key)
            self.collection.update_one({'_id': doc['_id']},
                                        {'$set': {'name': name}}, upsert=False)

    def fill_standard_id(self, skip=0):
        """Fill meta collection with chebi_id, pubmed_id,
        and kegg_id.

        Args:
            skip (:obj:`int`): skip first n number of records.
        """
        con_0 = {'chebi_id': {'$exists': False}}
        con_1 = {'chebi_id': None}
        query = {'$or': [con_0, con_1]}
        docs = self.collection.find(query, skip=skip)
        count = self.collection.count_documents(query)
        for i, doc in enumerate(docs):
            if i == self.max_entries:
                break
            if i % 100 == 0 and self.verbose:
                print('Processing doc {} out of {}'.format(i+skip, count))
            m2m_id = doc.get('m2m_id')
            ymdb_id = doc.get('ymdb_id')
            if ymdb_id == 'YMDB00890' or ymdb_id == 'YMDB00862':
                continue
            if ymdb_id is not None: # ymdb has richer data than ecmdb
                doc_e = self.ymdb_query.get_standard_ids_by_id(ymdb_id)
                if doc_e['synonyms']:
                    synonyms = doc_e['synonyms']['synonym']
                else:
                    synonyms = None
                self.collection.update_many({'ymdb_id': ymdb_id},
                                           {'$set': {'chebi_id': doc_e['chebi_id'],
                                                    'hmdb_id': doc_e['hmdb_id'],
                                                    'kegg_id': doc_e['kegg_id'],
                                                    'description': doc_e['description'],
                                                    'chemical_formula': doc_e['chemical_formula'],
                                                    'average_molecular_weight': doc_e['average_molecular_weight'],
                                                    'cas_registry_number': doc_e['cas_registry_number'],
                                                    'smiles': doc_e['smiles'],
                                                    'cellular_locations': doc_e['cellular_locations'],
                                                    'pubchem_compound_id': doc_e['pubchem_compound_id'],
                                                    'chemspider_id': doc_e['chemspider_id'],
                                                    'biocyc_id': doc_e['biocyc_id'],
                                                    'pathways': doc_e['pathways'],
                                                    'property': doc_e['property'],
                                                    'name': doc_e['name'],
                                                    'synonyms': synonyms}}, upsert=False)
            elif m2m_id is not None:
                doc_y = self.ecmdb_query.get_standard_ids_by_id(m2m_id)
                if doc_y['synonyms']:
                    synonyms = doc_y['synonyms']['synonym']
                else:
                    synonyms = None
                self.collection.update_many({'m2m_id': m2m_id},
                                           {'$set': {'chebi_id': doc_y['chebi_id'],
                                                    'hmdb_id': doc_y['hmdb_id'],
                                                    'kegg_id': doc_y['kegg_id'],
                                                    'description': doc_y['description'],
                                                    'chemical_formula': doc_y['chemical_formula'],
                                                    'average_molecular_weight': doc_y['average_molecular_weight'],
                                                    'cas_registry_number': doc_y['cas_registry_number'],
                                                    'smiles': doc_y['smiles'],
                                                    'cellular_locations': doc_y['cellular_locations'],
                                                    'pubchem_compound_id': doc_y['pubchem_compound_id'],
                                                    'chemspider_id': doc_y['chemspider_id'],
                                                    'biocyc_id': doc_y['biocyc_id'],
                                                    'pathways': doc_y['pathways'],
                                                    'property': doc_y['property'],
                                                    'name': doc_y['name'],
                                                    'synonyms': synonyms}}, upsert=False)
            else:
                continue

    def remove_dups(self, _key):
        """Remove entries with the same _key.

        Args:
            _key(:obj:`str`): Name of fields in which dups will be identified.
        """
        num, docs = self.get_duplicates('metabolites_meta', _key)
        return num, docs

    def reset_cellular_locations(self, start=0):
        """Github (https://github.com/KarrLab/datanator_rest_api/issues/69)
        """
        query = {'cellular_locations': {'$ne': None}}
        count = self.collection.count_documents(query) - start
        for i, doc in enumerate(self.collection.find(filter=query, skip=start,
                                                     projection={'m2m_id': 1, 'ymdb_id': 1,
                                                                 'cellular_locations': 1})):
            if i == self.max_entries:
                break
            if self.verbose and i % 100 == 0:
                print('Processing doc {} out of {} ...'.format(i, count))
            cell_locations = doc['cellular_locations']
            obj = []
            if doc.get('ymdb_id'):
                for loc in cell_locations:
                    location = loc['cellular_location']['cellular_location']
                    obj.append({
                                'reference': ['YMDB'],
                                'cellular_location': location
                                })

            else:
                for loc in cell_locations:
                    location = loc['cellular_location']['cellular_location']
                    obj.append({
                                'reference': ['ECMDB'],
                                'cellular_location': location
                                })

            self.collection.update_one({'_id': doc['_id']},
                                       {'$set': {'cellular_locations': obj}},
                                       upsert=False)                
                                
                

def main():
    db = 'datanator'
    meta_loc = 'datanator'
    username = datanator.config.core.get_config()['datanator']['mongodb']['user']
    password = datanator.config.core.get_config()['datanator']['mongodb']['password']
    MongoDB = datanator.config.core.get_config()['datanator']['mongodb']['server']
    manager = MetabolitesMeta(cache_dirname=None, MongoDB=MongoDB, db=db, 
                                verbose=True, max_entries=float('inf'), 
                                username = username, password = password, meta_loc = meta_loc)

    # # manager.load_content()
    # collection_name = 'metabolites_meta'
    # manager.fill_metabolite_fields(fields=['m2m_id', 'inchi', 'synonyms.synonym'],
    #     collection_src='ecmdb', collection_des = collection_name)

    # manager.fill_metabolite_fields(fields=['ymdb_id', 'inchi', 'synonyms.synonym'], 
    #     collection_src='ymdb', 
    #     collection_des = collection_name)
    # manager.fill_names()
    # manager.fill_standard_id(skip=0)

    # num, _ = manager.remove_dups('InChI_Key')
    # print(num)

    manager.reset_cellular_locations()

if __name__ == '__main__':
    main()
