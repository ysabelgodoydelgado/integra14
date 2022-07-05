# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, exceptions, fields, models
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError
class AccountFiscalyearClosingTemplate(models.Model):
    _inherit = "account.fiscalyear.closing.abstract"
    _name = "account.fiscalyear.closing.template"

    name = fields.Char(translate=True)
    move_config_ids = fields.One2many(
        comodel_name='account.fiscalyear.closing.config.template',
        inverse_name='template_id', string="Configuración de movimientos",
    )
    chart_template_ids = fields.Many2many(
        comodel_name="account.chart.template", string="Disponible para",
        required=False,
    )


class AccountFiscalyearClosingConfigTemplate(models.Model):
    _inherit = "account.fiscalyear.closing.config.abstract"
    _name = "account.fiscalyear.closing.config.template"
    _order = "sequence asc, id asc"

    #aqui poner funcion que actualice/cargue las cuentas
    @api.onchange('l_map')
    def inchange_l_map(self):
        #if not self.journal_id:
        #    raise exceptions.UserError("Seleccione un diario")
        print("buscar las cuentas y ponerlas en fiscal closing==================================================================")
        ingreso = self.env.ref('account.data_account_type_revenue').id
        gasto = self.env.ref('account.data_account_type_expenses').id
        #costo = self.env.ref('accounting_pdf_reports.data_account_type_direct_costs_cost').id

        #('company_id','=',self.journal_id.company_id.id),
        #('company_id','=',self.journal_id.company_id.id),

        ganancia = self.env.ref('account.data_unaffected_earnings').id
        accounts = self.env['account.account'].sudo().search([('user_type_id','in',[gasto,ingreso])])

        config_a = self.env['account.account'].sudo().search([('user_type_id','=',ganancia)],limit=1)#esta es la de destino siempre es la misma preguntar cual es
        maps = []
        cont = 1
        account_len = int(self.env['ir.config_parameter'].sudo().get_param('account_longitude_report'))
        if not account_len:
            raise exceptions.UserError("Por favor configure la longitud de las cuentas contables.")
        _logger.info("accounts %s",accounts)
        if self.l_map:
            #sync
            
            for a in accounts:
                #en este caso el campo dest_account es string no one2many
                #validar que sean auxiliares
                if len(a.code) == account_len:
                    vals = {'name':a.name,'src_accounts':a.code,'dest_account':config_a.code,'template_config_id':self.id} #fyc_config_id
                    cont +=1
                    print("vals**************",vals)
                    maps.append((0, 0, vals))
            if len(maps) > 0:
                #self.update({'mapping_ids':maps})
                return {'value':{'mapping_ids':maps}}
        else:
            return {'value':{'mapping_ids':[(5, 0, 0)]}}

    l_map = fields.Boolean(string='Cargar Cuentas')

    name = fields.Char(translate=True)
    template_id = fields.Many2one(
        comodel_name='account.fiscalyear.closing.template', index=True,
        readonly=True, string="Plantilla de cierre del año fiscal", required=True,
        ondelete='cascade',
    )
    journal_id = fields.Many2one(company_dependent=True)
    mapping_ids = fields.One2many(
        comodel_name='account.fiscalyear.closing.mapping.template',
        inverse_name='template_config_id', string="Asignaciones de cuentas",
    )
    closing_type_ids = fields.One2many(
        comodel_name='account.fiscalyear.closing.type.template',
        inverse_name='template_config_id', string="Tipos de cierre",
    )
    move_date = fields.Selection(
        selection=[
            ('last_ending', 'Última fecha del período final'),
            ('first_opening', 'Primera fecha del período de apertura'),
        ],
        string="Fecha de movimiento",
        default='last_ending',
        required=True,
    )

    _sql_constraints = [
        ('code_uniq', 'unique(code, template_id)',
         'Code must be unique per fiscal year closing!'),
    ]


class AccountFiscalyearClosingMappingTemplate(models.Model):
    _inherit = "account.fiscalyear.closing.mapping.abstract"
    _name = "account.fiscalyear.closing.mapping.template"

    #este es el detalle llenar automatico

    name = fields.Char(translate=True)
    template_config_id = fields.Many2one(
        comodel_name='account.fiscalyear.closing.config.template', index=True,
        string="Plantilla de configuración de cierre del año fiscal", readonly=True,
        required=True, ondelete='cascade',
    )
    src_accounts = fields.Char(
        string="Cuentas de origen", required=True,
        help="Account code pattern for the mapping source accounts"
    )
    dest_account = fields.Char(
        string="Cuentas de destino",
        help="Account code pattern for the mapping destination account. Only "
             "the first match will be considered. If this field is not "
             "filled, the performed operation will be to remove any existing "
             "balance on the source accounts with an equivalent counterpart "
             "in the same account."
    )


class AccountFiscalyearClosingTypeTemplate(models.Model):
    _inherit = "account.fiscalyear.closing.type.abstract"
    _name = "account.fiscalyear.closing.type.template"

    template_config_id = fields.Many2one(
        comodel_name='account.fiscalyear.closing.config.template', index=True,
        string="Plantilla de configuración de cierre del año fiscal", readonly=True,
        required=True, ondelete='cascade',
    )
