import pandas
from datetime import date, datetime
from dateutil import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

import logging
_logger = logging.getLogger(__name__)

class BinauralHrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'
    _description = 'Herencia empleado de odoo para personalizaciones nomina Venezuela'

    porc_ari = fields.Float(string="Porcentaje ARI", help="Porcentaje retencion ISLR", digits=(5,2), default=0.0)

    entry_date = fields.Date(string="Fecha de ingreso", required=True, tracking=True)
    seniority = fields.Char(string="Antigüedad", compute="_compute_seniority")

    dependant_ids = fields.One2many(
        "hr.employee.dependant", "employee_id", string="Dependientes", store=True)
    degree_ids = fields.One2many(
        "hr.employee.degree", "employee_id", string="Estudios Realizados", store=True)
    bank_ids = fields.One2many("hr.employee.bank", "employee_id", string="Información Bancaria")

    type_holidays = fields.Selection(
        [('last_wage','Ultimo sueldo devengado'),
         ('avg_last_month','Promedio de sueldo devengado de los últimos dos meses')],
        "Base para vacaciones", default='last_wage')
    holidays_accrued= fields.Float(string="Devengado para vacaciones", compute="_compute_holidays_accrued")

    # profit_sharing_accrued = fields.Float(
    #     string="Devengado para utilidades", compute="_compute_holidays_accrued")

    surcharge_percentage = fields.Float(string="% Recargo para jornadas nocturnas")

    prefix_vat = fields.Selection([
        ('V', 'V'), ('E', 'E'),
    ], "Prefijo Rif", default='V')
    vat = fields.Char(string="RIF")
    street = fields.Char(string="Calle")
    street2 = fields.Char(string="Calle 2")
    address_country_id = fields.Many2one("res.country", string="País")
    city_id = fields.Many2one(
        "res.country.city", "Ciudad", tracking=True, domain="[('state_id','=',state_id)]")
    state_id = fields.Many2one(
        "res.country.state", "Estado", tracking=True, domain="[('country_id','=',address_country_id)]")
    zip = fields.Char(string="Código Postal", change_default=True)
    municipality_id = fields.Many2one(
        'res.country.municipality', "Municipio", tracking=True, domain="[('state_id','=',state_id)]")
    house_type = fields.Selection(
        [("owned", "Propia"),
         ("rented", "Alquilada"),
         ("family", "Familiar")],
        "Vivienda", default="owned", tracking=True)
    private_mobile_phone = fields.Char(string="Teléfono celular personal", tracking=True)

    has_open_contract = fields.Boolean(string="Tiene Contrato", compute="_compute_has_open_contract")

    mixed_monthly_wage = fields.Float(string="Salario mixto mensual")
    average_annual_wage = fields.Float(string="Salario promedio anual")

    last_quarterly_calculated_benefits = fields.Date(
        string="Fecha del ultimo calculo trimestral de acumulado de prestaciones")

    def default_country_id(self):
        return self.env.ref("base.ve")

    country_id = fields.Many2one(default=default_country_id)

    @api.depends("entry_date", "departure_date")
    def _compute_seniority(self):
        for employee in self:
            seniority = ""
            diff = self._get_seniority()
            if diff:
                years = diff.years
                months = diff.months
                days = diff.days

                years_string = "Años" if years > 1 else "Año"
                months_string = "Meses" if months > 1 else "Mes"
                days_string = "Días" if days > 1 else "Día"

                if days > 0:
                    seniority += f"{days} {days_string}"
                if months > 0 and days > 0:
                    seniority = f"{months} {months_string} / " + seniority
                elif months > 0:
                    seniority = f"{months} {months_string} " + seniority
                if years > 0 and (days > 0 or months > 0):
                    seniority = f"{years} {years_string} / " + seniority
                elif years > 0:
                    seniority = f"{years} {years_string} " + seniority
            employee.seniority = seniority

    @api.depends("type_holidays")
    def _compute_holidays_accrued(self):
        today = datetime.today()
        for employee in self:
            employee.holidays_accrued = 0
            _logger.warning("ID: %s", (employee.id))
            if type(employee.id) == int:
                if today.month == 1:
                    employee_salary_payments = self._get_payroll_moves_grouped_by_months_of_a_specific_year(today.year - 1)
                else:
                    employee_salary_payments = employee._get_payroll_moves_grouped_by_months_of_a_specific_year()
                if employee_salary_payments:
                    if employee.type_holidays == "last_wage":
                        employee.holidays_accrued = employee_salary_payments[-1]["total_accrued"]
                    else:
                        employee.holidays_accrued = (employee_salary_payments[-1]["total_accrued"] + employee_salary_payments[-2]["total_accrued"]) / 2

    @api.depends("contract_ids")
    def _compute_has_open_contract(self):
        for employee in self:
            _logger.warning("ID: %s" % (employee.id))
            employee.has_open_contract = False
            if any(self.env["hr.contract"].search([("state", '=', "open"), ("employee_id", '=', employee.id)])):
                employee.has_open_contract = True

    def _compute_employee_average_annual_wage(self, id):
        employee = self.env["hr.employee"].search([("id", '=', id)])
        _logger.warning("Employee: %s" % (employee))

        moves = employee._get_payroll_moves_grouped_by_months_of_a_specific_year()
        _logger.warning("Moves: %s" % (moves))
        last_month = int(moves[-1]["month"])
        last_month_wage = int(moves[-1]["total_basic"])
        for month in range(last_month+1, 13):
            moves.append({
                "month": month,
                "total_basic": last_month_wage,
            })
        _logger.warning("Moves 2: %s" % (moves))
        annual_average = sum(move["total_basic"] for move in moves) / 12
        _logger.warning("Annual Avg: %s" % (annual_average))
        employee.average_annual_wage = annual_average
        _logger.warning("Annual Avg: %s" % (annual_average))
        return annual_average

    def _get_months_since_last_seniority_year(self):
        self.ensure_one()
        seniority = 0
        diff = self._get_seniority()
        if self.entry_date:
            from_date = self.entry_date
            to_date = self.departure_date if self.departure_date else fields.Date.today()

            diff = relativedelta.relativedelta(to_date, from_date)
            seniority = diff.months
        return seniority

    def _get_seniority_in_years(self):
        self.ensure_one()
        seniority = 0
        if self.entry_date:
            from_date = self.entry_date
            to_date = self.departure_date if self.departure_date else fields.Date.today()

            diff = relativedelta.relativedelta(to_date, from_date)
            seniority = diff.years
        return seniority

    def _get_seniority(self):
        self.ensure_one()
        if self.entry_date:
            from_date = self.entry_date
            to_date = self.departure_date if self.departure_date else fields.Date.today()

            return relativedelta.relativedelta(to_date, from_date)

    def _get_payroll_moves_grouped_by_months_of_a_specific_year(self, year=datetime.today().year):
        for employee in self:
            self._cr.execute("""
                SELECT
                    EXTRACT(MONTH FROM date) AS month,
                    SUM(total_basic) as total_basic,
                    SUM(total_accrued) as total_accrued
                FROM hr_payroll_move as move
                WHERE
                    employee_id = %s AND
                    move_type = 'salary' AND
                    EXTRACT(YEAR FROM date) = %s
                GROUP BY month
                ORDER BY month asc;
            """ %(employee.id, year))
            return self._cr.dictfetchall()

    def _get_benefits(self, three_months_ago, last_month, benefits_days, is_quarterly=False):
        self.ensure_one()
        self._cr.execute("""
            SELECT
                EXTRACT(MONTH FROM date) AS month,
                SUM(total_accrued) as total_accrued
            FROM hr_payroll_move as move
            WHERE
                employee_id = %s AND
                move_type = 'salary' AND
                date BETWEEN '%s'::date AND '%s'::date
            GROUP BY month
            ORDER BY month asc;
        """ %(self.id, three_months_ago, last_month))
        moves = self._cr.dictfetchall()
        _logger.warning("Moves: %s" % (moves))

        # Si el empleado no tiene nominas pagadas no se realiza el calculo
        if not any(moves):
            return False

        if self.contract_id.salary_type == "variable":
            avg_accrued = sum(move["total_accrued"] for move in moves) / 3
            benefits_payment = avg_accrued * benefits_days
        else:
            benefits_payment = moves[-1]["total_accrued"] * benefits_days

        self._register_payroll_benefits(benefits=benefits_payment)
        if is_quarterly:
            self.last_quarterly_calculated_benefits = datetime.today().date()

    def _register_payroll_benefits(self, benefits=0, interests=0, benefits_advance=0):
        for employee in self:
            payroll_benefits_accumulated = self.env["hr.payroll.benefits.accumulated"]
            benefits_accumulated_params = {
                "employee_id": employee.id,
                "accumulated_benefits": benefits,
                "accumulated_interest": interests,
                "accumulated_benefits_advance": benefits_advance,
                "date": fields.Date.today(),
            }
            benefits_accumulated = payroll_benefits_accumulated.search([
                ("employee_id", '=', employee.id)
            ])

            if any(benefits_accumulated):
                benefits_to_update = benefits_accumulated[-1]

                benefits_accumulated_params["accumulated_benefits"] += benefits_to_update.accumulated_benefits
                benefits_accumulated_params["accumulated_interest"] += benefits_to_update.accumulated_interest
                benefits_accumulated_params["accumulated_benefits_advance"] += benefits_to_update.accumulated_benefits_advance

                benefits_to_update.sudo().write(benefits_accumulated_params)
            else:
                payroll_benefits_accumulated.sudo().create(benefits_accumulated_params)

    def _get_integral_wage_by_month(self, month):
        for employee in self:
            self._cr.execute("""
                SELECT
                    EXTRACT(MONTH FROM date) AS month,
                    integral_wage
                FROM hr_payroll_move as move
                WHERE
                    employee_id = %s AND
                    move_type = 'salary' AND
                    EXTRACT(YEAR FROM date) = EXTRACT(YEAR FROM CURRENT_DATE) AND
                    EXTRACT(MONTH FROM date) = %s
            """ %(employee.id, month))
            moves = self._cr.dictfetchall()
            return moves[0]["integral_wage"]

    def _get_date_range_since_last_salary_move(self):
        self.ensure_one()
        last_move = self.env["hr.payroll.move"].search(
            [
                ("employee_id", '=', self.id),
                ("move_type", '=', "salary"),
            ],
            limit=1,
            order="date desc"
        )
        if not last_move:
            raise UserError(_("%s No tiene aún ningún pago de nómina." % (self.name)))
        return pandas.date_range(
            last_move.date + relativedelta.relativedelta(days=1),
            datetime.today().replace(hour=23),
            freq="1h"
        ).to_pydatetime().tolist()

    def _get_not_taken_vacation_days(self):
        self.ensure_one()
        days = 0
        work_entry_vacation_id = self.env.ref(
            "binaural_nomina.hr_work_entry_binaural_vacation").id
        allocations = self.env["hr.leave.allocation"].search([
            ("employee_id", '=', self.id)])
        vacation_allocations = allocations.filtered(
            lambda a: a.holiday_status_id.work_entry_type_id.id == work_entry_vacation_id)
        for allocation in vacation_allocations:
            days += (allocation.max_leaves - allocation.leaves_taken)
        return days

    @api.constrains("entry_date", "departure_date")
    def _check_dates(self):
        for employee in self:
            if employee.departure_date and employee.departure_date <= employee.entry_date:
                raise ValidationError(_(
                    "La fecha de egreso debe ser mayor a la fecha de ingreso."))

    @api.constrains("vat", "prefix_vat")
    def _check_vat(self):
        for employee in self:
            if employee.vat:
                employee_with_the_same_vat = self.env["hr.employee"].sudo().search([
                    ("vat", '=', employee.vat),
                    ("prefix_vat", '=', employee.prefix_vat),
                    ("id", "!=", employee.id),
                ])
                if any(employee_with_the_same_vat):
                    _logger.warning("Empleado: %s" % (employee_with_the_same_vat.vat))
                    raise ValidationError(_("Ya existe un empleado con ese RIF."))

    @api.constrains("type_holidays")
    def _check_employee_has_moves_from_at_least_two_months(self):
        for employee in self:
            if employee.type_holidays == "avg_last_month":
                _logger.warning("ID: %s" % (employee.id))
                if not type(employee.id) != "int":
                    raise ValidationError(_(
                        "No se puede usar como base para vaciones el promedio del devengado de los últimos dos meses " +
                        "porque el empleado acaba de ser registrado."))
                salary_payments = employee._get_payroll_moves_grouped_by_months_of_a_specific_year()
                if len(salary_payments) < 2:
                    raise ValidationError(_(
                        "No se puede usar como base para vaciones el promedio del devengado de los últimos dos meses " +
                        "porque el empleado tiene registrados menos de dos pagos de nómina mensual."))

    def toggle_active(self):
        res = super().toggle_active()
        if len(self) == 1 and not self.active:
            departure_date = self.departure_date or fields.Date.today()
            res["context"]["default_departure_date"] = departure_date
        return res
