import json
import requests
import re
import os
import requests
from bs4 import BeautifulSoup
from datanator_query_python.util import mongo_util
from pymongo.collation import Collation, CollationStrength


class KeggOrgCode(mongo_util.MongoUtil):

    def __init__(self, MongoDB, db, cache_dirname=None, replicaSet=None, verbose=False, max_entries=float('inf'),
                username=None, password=None, readPreference=None, authSource='admin'):
        super().__init__(cache_dirname=cache_dirname, MongoDB=MongoDB, verbose=verbose, max_entries=max_entries,
                        db=db, username=username, password=password, authSource=authSource, readPreference=readPreference)
        self.ENDPOINT_DOMAINS = {
            'root': 'https://www.genome.jp/kegg/catalog/org_list.html',
        }
        self.cache_dirname = cache_dirname
        self.MongoDB = MongoDB
        self.db = db
        self.verbose = verbose
        self.max_entries = max_entries
        self.collection_str = 'kegg_organisms_code'
        r = requests.get(self.ENDPOINT_DOMAINS['root'])
        self.soups = BeautifulSoup(r.content, 'html.parser')
        self.client, self.db, self.collection = self.con_db(self.collection_str)
        self.collation = Collation(locale='en', strength=CollationStrength.SECONDARY)

    def has_href_and_id(self, tag):
        return tag.has_attr('href') and tag.has_attr('id')

    def has_href_but_no_id(self, tag):
        return tag.has_attr('href') and not tag.has_attr('id')

    def parse_ids(self):
        """Parse HTML to get kegg organism codes.
        """
        for soup in self.soups.find_all(self.has_href_and_id):
            yield soup.get('id')

    def parse_names(self):
        """Parse HTML to get kegg organism names.
        """
        not_in = ['prag']
        for soup in self.soups.find_all(self.has_href_but_no_id):
            if soup.get('href') == '/dbget-bin/www_bfind?T00544': # special case
                yield 'Haemophilus influenzae PittGG (nontypeable)'
            result = re.search('.>(.*)<\/a>', str(soup))
            if result is not None and soup.get('href').startswith('/dbget-bin'):
                if result.group(1) not in not_in:
                    yield result.group(1)
                else:
                    continue
            else:
                continue

    def make_bulk(self, offset=0, bulk_size=100):
        """Make bulk objects to be inserted into MongoDB.

        Args:
            offset(:obj:`int`): Position of beginning (zero-indexed). Defaults to 0.
            bulk_size(:obj:`int`): number of objects. Defaults to 100.

        Return:
            (:obj:`list` of :obj:`dict`): list of objects to be inserted.
        """
        ids = self.parse_ids()
        names = self.parse_names()
        count = 0
        result = []
        for i, (_id, name) in enumerate(zip(ids, names)):
            if count == bulk_size:
                break
            if i < offset:
                continue
            if count < bulk_size:   
                result.append({"kegg_organism_id": _id, "org_name": name})
                count += 1
        return result

    def bulk_load(self, bulk_size=100):
        """Loading bulk data into MongoDB.
        
        Args:
            bulk_size(:obj:`int`): number of entries per insertion. Defaults to 100.
        """
        offset = 0
        length = bulk_size
        count = 0
        while length != 0:
            if count == self.max_entries:
                break
            count += 1
            docs = self.make_bulk(offset=offset * count, bulk_size=bulk_size)
            self.collection.insert_many(docs)
            length = len(docs)