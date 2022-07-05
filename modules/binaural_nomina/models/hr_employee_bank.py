from odoo import fields, models, _


class HrEmployeeBank(models.Model):
    _name = "hr.employee.bank"
    _description = "Información bancaria de un empleado"

    name = fields.Char(string="Número de Cuenta", required=True)
    employee_id = fields.Many2one("hr.employee", string="Empleado")
    bank_name = fields.Char(string="Banco", required=True)
    account_type = fields.Selection(
        selection=[("checking", "Corriente"), ("saving", "Ahorro")],
        string="Tipo de cuenta")
    details = fields.Text(string="Observaciones")
