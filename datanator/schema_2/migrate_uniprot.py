from datanator_query_python.config import motor_client_manager
import asyncio
import simplejson as json
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
from pprint import pprint


class MigrateUniprot:

    def __init__(self, collection="uniprot", to_database="datanator-test",
                 from_database="datanator", max_entries=float("inf")):
        self.collection = collection
        self.from_database = from_database
        self.to_database = to_database
        self.from_collection = motor_client_manager.client.get_database(from_database)[collection]
        self.to_collection = motor_client_manager.client.get_database(to_database)[collection]
        self.max_entries = max_entries

    def index_primary(self, _key, background=True):
        """Index key (single key ascending)

        Args:
            _key(:obj:`str`): Name of key to be indexed
        """
        yield self.to_collection.create_index(_key, background=background)
    
    async def process_cursor(self, skip=0):
        """Process mongodb cursor
        Transform data and move to new database

        Args:
            docs(:obj:`pymongo.Cursor`): documents to be processed
        """
        bulk_write = []
        query = {}
        if self.max_entries == float('inf'):
            limit = 0
        else:
            limit = self.max_entries
        docs = self.from_collection.find(filter=query, projection={'_id': 0},
                                        no_cursor_timeout=True, batch_size=500,
                                        skip=skip, limit=limit)
        i = 0
        async for doc in docs:
            i += 1
            if i == self.max_entries:
                break
            if i != 0 and i % 50 == 0:
                print("Processing file {}".format(i + skip))
                try:
                    await self.to_collection.bulk_write(bulk_write)
                    bulk_write = []
                except BulkWriteError as bwe:
                    pprint(bwe.details)
                    bulk_write = []
            uniprot_id = doc.get('uniprot_id')
            doc["add_id"] = [{"name_space": "gene_name_alt", "value": doc.get("gene_name_alt")},
                             {"name_space": "gene_name_orf", "value": doc.get("gene_name_orf")},
                             {"name_space": "gene_name_oln", "value": doc.get("gene_name_oln")}]
            doc.pop('gene_name_alt', None)
            doc.pop('gene_name_orf', None)
            doc.pop('gene_name_oln', None)
            doc['schema_version'] = "2"
            tax_doc = await motor_client_manager.client.get_database(
                "datanator-test")["taxon_tree"].find_one(filter={"tax_id": doc["ncbi_taxonomy_id"]},
                projection={'canon_anc_ids': 1, 'canon_anc_names': 1})
            if tax_doc is not None:
                doc['canon_anc_names'] = tax_doc["canon_anc_names"] 
                doc['canon_anc_ids'] = tax_doc["canon_anc_ids"] 
            modifications = doc.get('modifications')
            if modifications is not None:
                bw = []
                for mod in modifications:
                    mod['uniprot_id'] = uniprot_id
                    mod['schema_version'] = "2"
                    reference = mod['reference']
                    mod['reference'] = {"namespace": "doi", "value": reference["doi"]}
                    bw.append(json.loads(json.dumps(mod, ignore_nan=True)))  
                motor_client_manager.client.get_database(self.to_database)['protein_modifications'].insert_many(bw)
            doc.pop('modifications', None)
            bulk_write.append(UpdateOne({'uniprot_id': uniprot_id}, {'$set': json.loads(json.dumps(doc, ignore_nan=True))}, upsert=True))
        if len(bulk_write) != 0:
            try:
                self.to_collection.bulk_write(bulk_write)
            except BulkWriteError as bwe:
                pprint(bwe.details)
            finally:
                print("Done.")   


def main():
    loop = asyncio.get_event_loop()
    src = MigrateUniprot()
    src.index_primary('uniprot_id')
    loop.run_until_complete(src.process_cursor(skip=11000))

if __name__ == '__main__':
    main()