from odoo import api, fields, models, _


class HrWorkEntryType(models.Model):
    _inherit = "hr.payroll.structure"

    category = fields.Selection([
        ("salary", "Salario"),
        ("vacation", "Vacaciones"),
        ("benefits", "Prestaciones"),
        ("profit_sharing", "Utilidades"),
        ("liquidation", "Liquidación"),
    ], string="Categoría", default="salary")
