import calendar
import pandas

from datetime import date, datetime
from dateutil import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

import logging
_logger = logging.getLogger(__name__)


class HrPayrollBenefit(models.Model):
    _name = "hr.payroll.benefits.accumulated"
    _rec_name = "employee_name"
    _description = "Acumulado de Prestaciones"

    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True)
    employee_name = fields.Char(related="employee_id.name")
    accumulated_benefits = fields.Float(string="Acumulado de prestaciones", required=True)
    accumulated_benefits_advance = fields.Float(string="Saldo acumulado de anticipos de prestaciones")
    available_benefits = fields.Float(
        string="Saldo disponible de prestaciones", compute="_compute_available_benefits")
    accumulated_interest = fields.Float(string="Acumulado de intereses", required=True)
    date = fields.Date(string="Fecha del último cálculo", required=True)

    _sql_constraints = [
        ('unique_employee_id','UNIQUE(employee_id)',
            'Este empleado ya tiene acumulado de prestaciones'),
    ]

    @api.depends("accumulated_benefits", "accumulated_benefits_advance")
    def _compute_available_benefits(self):
        for employee in self:
            employee.available_benefits = employee.accumulated_benefits - employee.accumulated_benefits_advance

    @api.model
    def _compute_employee_mixed_monthly_wage(self):
        employee = self.employee_id
        seniority = employee._get_months_since_last_seniority_year()

        if seniority == 0:
            employee.mixed_monthly_wage = 0
            return

        months = seniority if seniority < 3 else 3
        moves = self.env["hr.payroll.move"].search([
            ("employee_id", '=', employee.id),
            ("move_type", '=', "salary"),
        ])
        date_from = date.today() + relativedelta.relativedelta(months=-(months))
        moves_in_between_three_months_and_now = moves.filtered(lambda m: m.date > date_from)
        moves_accrued_sum = sum(move.total_accrued for move in moves_in_between_three_months_and_now)
        employee.mixed_monthly_wage = moves_accrued_sum / months

    @api.model
    def _compute_employee_average_annual_wage(self):
        employee = self.employee_id
        self._cr.execute("""
            SELECT
                EXTRACT(MONTH FROM date) AS month,
                SUM(total_basic) as wage
            FROM hr_payroll_move as move
            WHERE
                employee_id = %s AND
                move_type = 'salary' AND
                EXTRACT(YEAR FROM date) = EXTRACT(YEAR FROM CURRENT_DATE)
            GROUP BY month
            ORDER BY month asc;
        """ %(employee.id))
        moves = self._cr.dictfetchall()
        last_month = int(moves[-1]["month"])
        last_month_wage = int(moves[-1]["wage"])
        for month in range(last_month+1, 13):
            moves.append({
                "month": month,
                "wage": last_month_wage,
            })
        annual_average = sum(move["wage"] for move in moves) / 12
        employee.average_annual_wage = annual_average

    @api.model
    def get_quarterly_benefits(self):
        one_month = relativedelta.relativedelta(months=1)
        today = datetime.today().date()
        last_day_of_current_month = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        last_month = today - one_month
        last_month = last_month.replace(day=calendar.monthrange(last_month.year, last_month.month)[1])

        three_months_ago = today - relativedelta.relativedelta(months=3)
        three_months_ago = three_months_ago.replace(day=1)

        _logger.warning("Three months ago: %s" % (three_months_ago.month + 1))
        _logger.warning("This month: %s" % (today.month + 1))

        last_three_months = pandas.date_range(three_months_ago + one_month, last_day_of_current_month)
        _logger.warning("Date range: %s" % (last_three_months))

        benefits_days = int(self.env["ir.config_parameter"].sudo().get_param("dias_prestaciones_mes")) * 3
        if not bool(benefits_days):
            raise UserError(_(
                "No se ha definido la cantidad de días de prestaciones por mes en la configuración de nómina."))

        employees = self.env["hr.employee"].search([])
        _logger.warning("Employees: %s" % (employees))
        for employee in employees:
            # Si al empleado ya se le realizo el calculo del trimestre en curso no se vuelve a realizar
            if employee.last_quarterly_calculated_benefits in last_three_months:
                continue
            employee._get_benefits(three_months_ago, last_month, benefits_days)

    @api.model
    def get_annual_benefits(self):
        one_month = relativedelta.relativedelta(months=1)
        today = datetime.today().date()
        last_day_of_current_month = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        last_month = today - one_month
        last_month = last_month.replace(day=calendar.monthrange(last_month.year, last_month.month)[1])

        three_months_ago = today - relativedelta.relativedelta(months=3)
        three_months_ago = three_months_ago.replace(day=1)

        employees = self.env["hr.employee"].search([])
        for employee in employees:
            _logger.warning("Today: %s" %(today))
            _logger.warning("Entry date: %s" %(employee.entry_date))
            entry_date = employee.entry_date
            if not entry_date or today.day != entry_date.day or today.month != entry_date.month:
                continue

            days_per_year = int(self.env["ir.config_parameter"].sudo().get_param("dias_prestaciones_anno"))
            if not bool(days_per_year):
                raise UserError(_(
                    "No se ha definido la cantidad de días de prestaciones por año en la configuración de nómina."))

            maximum_of_days = int(self.env["ir.config_parameter"].sudo().get_param("maximo_dias_prestaciones_anno"))
            if not bool(maximum_of_days):
                raise UserError(_(
                    "No se ha definido la cantidad máxima de días de prestaciones por año en la configuración de nómina."))

            seniority = employee._get_seniority_in_years()
            _logger.warning("Seniority: %s" %(seniority))
            days_per_employee_years = days_per_year * seniority

            benefits_days = days_per_employee_years if days_per_employee_years < maximum_of_days else maximum_of_days

            employee._get_benefits(three_months_ago, last_month, benefits_days, True)

    def get_benefits_interest(self):
        benefit_interest_type = self.env["ir.config_parameter"].sudo().get_param("tipo_calculo_intereses_prestaciones")
        if benefit_interest_type != "interno":
            return

        interest_rate = float(self.env["ir.config_parameter"].sudo().get_param("tasa_intereses_prestaciones"))
        if not bool(interest_rate):
            raise UserError(_(
                "No se ha definido la tasa mensual de intereses de prestaciones en la configuración de nómina."))
        daily_interest_rate = interest_rate / 30
        _logger.warning("Daily interest rate: %s" % (daily_interest_rate))

        employees = self.env["hr.employee"].search([])
        _logger.warning("Employees: %s" % (employees))
        for employee in employees:
            _logger.warning("Employee: %s" %(employee))
            benefits_accumulated = self.env["hr.payroll.benefits.accumulated"].search([
                ("employee_id", '=', employee.id),
            ])
            _logger.warning("Benefits accumulated: %s" % (benefits_accumulated))
            if not any(benefits_accumulated):
                continue

            available_benefits = benefits_accumulated[-1]["available_benefits"]
            daily_interest =available_benefits * (daily_interest_rate / 100)
            employee._register_payroll_benefits(interests=daily_interest)
