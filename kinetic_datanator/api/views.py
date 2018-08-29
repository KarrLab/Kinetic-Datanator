"""
:Author: Saahith Pochiraju <saahith116@gmail.com>
:Date: 2018-08-13
:Copyright: 2018, Karr Lab
:License: MIT
"""

from flask_restplus import Api, Resource, reqparse
import json
from flask import  Blueprint, Response, render_template, make_response
from kinetic_datanator.core import common_schema, models
from kinetic_datanator.api.lib.search.manager import search_manager
from kinetic_datanator.api.lib.metabolite.manager import metabolite_manager
from kinetic_datanator.api.lib.subunit.manager import subunit_manager
from kinetic_datanator.api.lib.complex.manager import complex_manager
from kinetic_datanator.api.lib.reaction.manager import reaction_manager
from kinetic_datanator.api.serializer import *
import json
import os



api_blueprint = Blueprint('api', __name__, url_prefix='/api')
api = Api(api_blueprint, version='0.0', title='Datanator API',
    description='Providing Data for Modelers', doc='/docs/')

@api.representation('text/html')
def output_html(data, code, headers=None):
    resp = make_response(render_template('api/api.html', content = json.dumps(data, sort_keys=True, indent=4)), code)
    resp.headers.extend(headers or {})
    return resp

@api.representation('application/json')
def output_json(data, code, headers=None):
    resp = make_response(json.dumps(data, sort_keys=True, indent=4), code)
    resp.headers.extend(headers or {})
    return resp

cachedir = os.path.join(os.path.abspath(os.path.dirname(__file__)),'..', 'cache')


class Search(Resource):

    @api.doc(params={'value': 'Value to search for over the database'})
    def get(self, value):
        search_dict = search_manager.search(value)

        metabolite_data = CompoundSerializer().dump(search_dict['Compound'], many=True).data
        complex_data = ProteinComplexSerializer().dump(search_dict['ProteinComplex'], many=True).data
        subunuit_data = ProteinSubunitSerializer().dump(search_dict['ProteinSubunit'], many=True).data
        reaction_data = ReactionSerializer().dump(search_dict['Reaction'], many=True).data
        return [metabolite_data, complex_data, subunuit_data, reaction_data]

class MetaboliteSearch(Resource):
    @api.doc(params={'value': 'Value to search over in the metabolite space'})
    def get(self,value):
        return CompoundSerializer().dump(metabolite_manager._search(value) , many=True).data

class ProteinSubunitSearch(Resource):
    @api.doc(params={'value': 'Value to search over in the protein subunit space'})
    def get(self,value):
        return ProteinSubunitSerializer().dump(subunit_manager._search(value) , many=True).data

class ProteinComplexSearch(Resource):
    @api.doc(params={'value': 'Value to search over in the protein complex space'})
    def get(self,value):
        return ProteinComplexSerializer().dump(complex_manager._search(value) , many=True).data


class Metabolite(Resource):

    def get(self, id):
        metabolite = metabolite_manager.get_compound_by_id(id)
        observed_concentrations = metabolite_manager.get_observed_concentrations(metabolite)
        reactions = reaction_manager.get_reaction_by_compound(metabolite)

        serialized_metabolite = CompoundSerializer().dump(metabolite).data
        serialized_concentrations = ObservedValueSerializer().dump(observed_concentrations, many=True).data
        serialized_reactions =  ReactionSerializer().dump(reactions, many=True).data

        return [serialized_metabolite, serialized_concentrations, serialized_reactions]

class MetaboliteConcentration(Resource):

    @api.doc(params={'id': 'ID number of the given compound'})
    def get(self, id):
        compound = metabolite_manager.get_compound_by_id(id)
        observed_concentrations = metabolite_manager.get_observed_concentrations(compound)
        return ObservedValueSerializer().dump(observed_concentrations, many=True).data

class ProteinAbundance(Resource):

    def get(self, id):
        subunit = subunit_manager.get_subunit_by_id(id)
        observed_abundances = subunit_manager.get_observed_abundances(subunit)
        return ObservedValueSerializer().dump(observed_abundances, many=True).data

class ProteinInteraction(Resource):

    def get(self,id):
        pass

class ReactionParameter(Resource):

    def get(self,id):
        reaction = reaction_manager.get_reaction_by_kinetic_law_id(id)
        observed_parameters = reaction_manager.get_observed_parameter_value(reaction)
        return ObservedValueSerializer().dump(observed_parameters, many=True).data






# class DataDump(Resource):
#     """
#     Represents the API data dump from the common schema database
#
#     """
#     #TODO: Account for other filetypes/Cache data tables
#
#     def get(self, table):
#         type_mappings = {'INTEGER': int, 'VARCHAR(255)': str, 'BOOLEAN': bool, 'FLOAT': float, 'VARCHAR': str}
#
#         table_obj = getattr(model, table)
#
#         parser = reqparse.RequestParser()
#         parser.add_argument('download', type=bool)
#         parser.add_argument('format', type=str)
#         for c in table_obj.__table__.columns:
#             parser.add_argument(str(c.name), type=type_mappings[str(c.type)])
#
#         ## Full Table Return
#         if all(value == None for value in parser.parse_args().values()):
#             with open(cachedir+'/'+str(table)+'.json') as json_data:
#                 return json.load(json_data)
#
#         ##Filtered Return and Download
#         results = flk.session.query(table_obj)
#         for key,value in parser.parse_args().items():
#             if value == None or key=='download' or key=='format':
#                 continue
#             condition = getattr(table_obj, key) == value
#             results = results.filter(condition)
#
#         ans = {}
#         for item in results.all():
#             ans[item.id] = item.serialize()
#
#         json_return = jsonify({table: ans})
#
#         if parser.parse_args()['download'] == True and parser.parse_args()['format'] == 'json' :
#             json_return.headers['Content-Disposition'] = "attachment; filename="+str(table)+'.json'
#
#         return json_return
