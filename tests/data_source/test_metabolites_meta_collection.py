import unittest
from datanator.data_source import metabolites_meta_collection
import datanator.config.core
import pymongo
import tempfile
import shutil


class TestMetabolitesMeta(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cache_dirname = tempfile.mkdtemp()
        cls.db = 'test'
        cls.meta_loc = 'datanator'
        cls.username = datanator.config.core.get_config()['datanator']['mongodb']['user']
        cls.password = datanator.config.core.get_config()['datanator']['mongodb']['password']
        cls.MongoDB = datanator.config.core.get_config()['datanator']['mongodb']['server']
        port = datanator.config.core.get_config()['datanator']['mongodb']['port']
        replSet = datanator.config.core.get_config()['datanator']['mongodb']['replSet']
        cls.src = metabolites_meta_collection.MetabolitesMeta(cache_dirname=cls.cache_dirname,
                                                              MongoDB=cls.MongoDB,  db=cls.db,
                                                              verbose=True, max_entries=20, username = cls.username,
                                                              password = cls.password, meta_loc = cls.meta_loc)
        cls.client, cls.db_obj, cls.collection_obj = cls.src.con_db(cls.db)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.cache_dirname)
        cls.client.close()


    # def test_fill_metabolite_fields(self):
    #     dict_list = self.src.fill_metabolite_fields(
    #     	fields = ['m2m_id', 'inchi'], collection_src = 'ecmdb', collection_des = 'metabolites_meta')
    #     self.assertEqual(
    #         dict_list[0]['inchi'], 'InChI=1S/C4H6O3/c1-2-3(5)4(6)7')

    def test_load_content(self):
        self.src.load_content()
        meta_db = self.src.client[self.meta_loc]
        collection = meta_db['metabolites_meta']
        cursor = collection.find_one({'inchi': 'InChI=1S/C4H8O3/c1-3(2-5)4(6)7/h3,5H,2H2,1H3,(H,6,7)'})
        self.assertEqual(cursor['InChI_Key'], 'DBXBTMSZEOQQDU-UHFFFAOYSA-N')
        
    def test_replace_key_in_similar_compounds(self):
        self.src.replace_key_in_similar_compounds()