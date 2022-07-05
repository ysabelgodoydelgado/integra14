from odoo import api, fields, models, _


class BinauralHrContractInherit(models.Model):
    _inherit = 'hr.contract'
    _description = 'Herencia contrato para Venezuela'

    daily_wage = fields.Float(
        string="Salario diario", compute="_compute_daily_wage", store=True)
    hourly_daily_wage = fields.Float(
        string="Salario diario por hora", compute="_compute_hourly_daily_wage", store=True)
    schedule_payment_type = fields.Selection(
        [("weekly", "Semanal"),
         ("half-monthly", "Quincenal"),
         ("monthly", "Mensual"),],
        "Pago programado", default="monthly")
    salary_type = fields.Selection(
        [("fixed", "Fijo"),
         ("variable", "Variable")],
        "Tipo de salario", default="fixed")

    @api.model
    def create(self, vals):
        res = super().create(vals)
        register_salary_change(self, res, vals)
        return res

    def write(self, vals):
        res = super().write(vals)
        contract = self.env["hr.contract"].search([("id", '=', self.id)])
        register_salary_change(self, contract, vals)
        return res

    @api.depends("wage")
    def _compute_daily_wage(self):
        for contract in self:
            contract.daily_wage = contract.wage / 30

    @api.depends("daily_wage", "resource_calendar_id.hours_per_day")
    def _compute_hourly_daily_wage(self):
        for contract in self:
            hours = contract.resource_calendar_id.hours_per_day
            contract.hourly_daily_wage = contract.hourly_daily_wage / hours


def register_salary_change(self, contract, vals):
    salary_changed = False
    keys = ("wage", "wage_type", "hourly_wage")
    for key in keys:
        if key in vals:
            salary_changed = True
            break;
    if salary_changed:
        self.env["hr.employee.salary.change"].sudo().create({
            "contract_id": contract.id,
            "wage_type": contract.wage_type,
            "wage": contract.wage,
            "hourly_wage": contract.hourly_wage,
        })
