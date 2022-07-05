from odoo import api, fields, models, _


class HrPayrollMove(models.Model):
    _name = "hr.payroll.move"
    _description = "Pagos de nómina"
    _rec_name = "employee_name"
    _inherit = ["mail.thread"]

    move_type = fields.Selection([
        ("salary", "Salario"),
        ("vacation", "Vacaciones"),
        ("benefits", "Prestaciones"),
        ("profit_sharing", "Utilidades"),
        ("liquidation", "Liquidación"),
    ], string="Tipo", default="salary")
    employee_id = fields.Many2one(
        "hr.employee", string="Empleado", required=True)
    employee_name = fields.Char(
        string="Nombre", related="employee_id.name", store=True)
    employee_prefix_vat = fields.Selection(
        related="employee_id.prefix_vat", store=True)
    employee_vat = fields.Char(
        string="RIF", related="employee_id.vat", store=True)
    employee_private_mobile_phone = fields.Char(
        string="Teléfono personal", related="employee_id.private_mobile_phone", store=True)
    date = fields.Date(string="Fecha del recibo de pago", default=fields.Date.today())
    department_id = fields.Many2one(
        "hr.department", string="Departamento",
        related="employee_id.department_id", store=True)

    total_basic = fields.Float(string="Salario base")
    total_deduction = fields.Float(string="Total deducción")
    total_accrued = fields.Float(string="Total devengado")
    total_net = fields.Float(string="Total neto")

    total_assig = fields.Float(string="Total asignaciones")
    advance_of_benefits = fields.Float(string="Anticipo de prestaciones")
    profit_sharing_payment = fields.Float(string="Utilidades")
    integral_wage = fields.Float(string="Salario integral mensual")

    vacational_period = fields.Char(string="Periodo vacaional")
    vacation_days = fields.Integer(string="Días correspondientes de vacaciones")
    consumed_vacation_days = fields.Integer(string="Días consumidos de vacaciones")
    total_vacation = fields.Float(string="Total bono vacacional")
