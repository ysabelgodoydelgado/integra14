# -*- coding: utf-8 -*-
# from odoo import http


# class BinauralNomina(http.Controller):
#     @http.route('/binaural_nomina/binaural_nomina/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/binaural_nomina/binaural_nomina/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('binaural_nomina.listing', {
#             'root': '/binaural_nomina/binaural_nomina',
#             'objects': http.request.env['binaural_nomina.binaural_nomina'].search([]),
#         })

#     @http.route('/binaural_nomina/binaural_nomina/objects/<model("binaural_nomina.binaural_nomina"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('binaural_nomina.object', {
#             'object': obj
#         })
