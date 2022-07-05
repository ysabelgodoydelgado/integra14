from datetime import  date
from odoo import api, fields, models, _
from odoo.addons.hr_payroll.models.browsable_object import Payslips
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class BinauralHrPayslipInherit(models.Model):
    _inherit = 'hr.payslip'
    _description = 'Herencia pay slip de odoo para personalizaciones Venezuela'

    benefits_advance = fields.Float(string="Anticipo")
    benefits_advance_percentage = fields.Float(
        string="% Anticipo", store=True,
        compute="_compute_benefits_advance_percentage",
        inverse="_inverse_benefits_advance_percentage")
    is_benefits = fields.Boolean(
        string="¿Es una nomina de prestaciones?", compute="_compute_is_benefits")

    @api.depends("benefits_advance")
    def _compute_benefits_advance_percentage(self):
        for payslip in self:
            benefits_available_amount = payslip._get_employee_benefits_available_amount()
            if benefits_available_amount == 0:
                payslip.benefits_advance_percentage = 0
            else:
                payslip.benefits_advance_percentage = payslip.benefits_advance * 100 / benefits_available_amount

    def _inverse_benefits_advance_percentage(self):
        for payslip in self:
            if not payslip.is_benefits:
                payslip.benefits_advance = 0
            else:
                benefits_available_amount = payslip._get_employee_benefits_available_amount()
                payslip.benefits_advance = benefits_available_amount * (
                                           payslip.benefits_advance_percentage / 100)

    def _get_employee_benefits_available_amount(self):
        self.ensure_one()
        benefits_accumulated = self.env["hr.payroll.benefits.accumulated"].search([
            ("employee_id", '=', self.employee_id.id),
        ])
        return benefits_accumulated[-1].available_benefits if any(benefits_accumulated) else 0

    @api.depends("struct_id")
    def _compute_is_benefits(self):
        for payslip in self:
            payslip.is_benefits = payslip.struct_id.id == self.env.ref("binaural_nomina.structure_payroll_benefits").id

    #Inherit functions
    def _get_base_local_dict(self):                
        local_dict_return = super(BinauralHrPayslipInherit, self)._get_base_local_dict()
        local_dict_return.update({
            'salario_minimo_actual': float(self.env['ir.config_parameter'].sudo().get_param('sueldo_base_ley')),
            'porc_faov': float(self.env['ir.config_parameter'].sudo().get_param('porcentaje_deduccion_faov')),
            'porc_ince': float(self.env['ir.config_parameter'].sudo().get_param('porcentaje_deduccion_ince')),
            'porc_ivss': float(self.env['ir.config_parameter'].sudo().get_param('porcentaje_deduccion_ivss')),
            'tope_ivss': float(self.env['ir.config_parameter'].sudo().get_param('tope_salario_ivss')),
            'maximo_deduccion_ivss': float(self.env['ir.config_parameter'].sudo().get_param('monto_maximo_ivss')),
            'porc_pf': float(self.env['ir.config_parameter'].sudo().get_param('porcentaje_deduccion_pf')),
            'tope_pf': float(self.env['ir.config_parameter'].sudo().get_param('tope_salario_pf')),
            'maximo_deduccion_pf': float(self.env['ir.config_parameter'].sudo().get_param('monto_maximo_pf')),
            'porcentaje_recargo_nocturno': float(self.env['ir.config_parameter'].sudo().get_param('porcentaje_recargo_nocturno'))
        })        
        return local_dict_return

    def _get_new_worked_days_lines(self):
        if not self.struct_id.use_worked_day_lines:
            return [(5, False, False)]    

        if self.struct_id.category == "liquidation":
            last_move_date_to_now = self.employee_id._get_date_range_since_last_salary_move()
            domain = [
                ("date_start", 'in', last_move_date_to_now),
                ("date_stop", 'in', last_move_date_to_now),
            ]
            worked_days_line_values = self._get_worked_day_lines(check_out_of_contract=False, domain=domain)
        else:
            worked_days_line_values = self._get_worked_day_lines(check_out_of_contract=False)
        worked_days_lines = self.worked_days_line_ids.browse([])            

        for r in worked_days_line_values:
            r['payslip_id'] = self.id
            worked_days_lines |= worked_days_lines.new(r)                
        return worked_days_lines

    def _get_paid_amount(self):
        self.ensure_one()
        daily_wage = self.contract_id.daily_wage

        if self.struct_id.category == "liquidation":
            worked_days = sum(self.worked_days_line_ids.mapped("number_of_days"))
            return daily_wage * worked_days

        SCHEDULE_PAYMENT_DAYS = {
            "weekly": 7,
            "half-monthly": 15,
            "monthly": 30,
        }
        schedule_payment_type = self.contract_id.schedule_payment_type
        return SCHEDULE_PAYMENT_DAYS[schedule_payment_type] * daily_wage

    def action_payslip_done(self):
        payslip_done_name = []
        message = ''
        for slip in self:
            if slip.is_benefits and slip.benefits_advance_percentage > 75:
                raise UserError(_(
                    "No se puede realizar un adelanto de prestaciones por más del 75% del monto disponible del empleado."))
            payslips_done = self.env['hr.payslip'].search([
                ('date_from','=',slip.date_from),
                ('employee_id','=',slip.employee_id.id),
                ('contract_id','=',slip.contract_id.id),
                ('struct_id','=',slip.struct_id.id),
                ('state','=','done')
            ])

            if payslips_done:
                payslip_done_name.append(payslip.number)                            

        if len(payslip_done_name) == 0:
            super(BinauralHrPayslipInherit, self).action_payslip_done()
            for slip in self:
                if slip.struct_id.category == "benefits":
                    slip.employee_id._register_payroll_benefits(benefits_advance=slip.benefits_advance)
                self._register_payroll_move(slip)
        elif len(payslip_done_name) == 1:
            message = 'El recibo %s tiene las mismas caracteristicas (contrato y estructura), verifique la informacion e intente nuevamente' % (payslip_done_name[0])
            raise UserError(message)
        else:
            message = 'Los recibios %s tienen las mismas caracteristicas (contrato y estructura), verifique la informacion e intente nuevamente' % (", ".join(payslip_done_name))            
            raise UserError(message)
            
    def _register_payroll_move(self, slip):
        work_entry_type_category = slip.struct_id.category
        move_params = {}
        move_params["move_type"] = work_entry_type_category
        move_params["employee_id"] = slip.employee_id.id

        total_basic = 0
        total_deduction = 0
        total_accrued = 0
        total_net = 0
        total_assig = 0
        advance_of_benefits = 0
        profit_sharing_payment = 0
        vacational_period = 0
        vacation_days = 0
        consumed_vacation_days = 0
        total_vacation = 0
        integral_wage = 0

        for line in slip.line_ids:
            if line.category_id.code == "DED":
                total_deduction += line.total
            if line.category_id.code == "ASIG":
                total_assig += line.total
            if line.code == "BASIC":
                total_basic += line.total
            if line.code == "DEV":
                total_accrued += line.total
            if line.code == "NET":
                total_net += line.total
            if line.code == "DDBVM":
                vacation_days += line.total
            if line.code == "DDVM":
                consumed_vacation_days += line.total
            if line.code == "SID":
                integral_wage += line.total
            if line.code == "ADPRESTA":
                advance_of_benefits += line.total

        move_params["total_basic"] = total_basic
        move_params["total_deduction"] = total_deduction
        move_params["total_accrued"] = total_accrued
        move_params["total_net"] = total_net
        move_params["total_assig"] = total_assig
        move_params["advance_of_benefits"] = advance_of_benefits
        move_params["profit_sharing_payment"] = profit_sharing_payment
        move_params["vacational_period"] = vacational_period
        move_params["vacation_days"] = vacational_period
        move_params["consumed_vacation_days"] = consumed_vacation_days
        move_params["total_vacation"] = total_vacation

        self.env["hr.payroll.move"].create(move_params)

    ## FUNCIONES PARA REGLAS
    def _compute_monday_in_range(self, id):        
        count = 0

        if id:    
            payslip = self.env['hr.payslip'].browse(id)

            date_from = date(payslip.date_from.year, payslip.date_from.month, payslip.date_from.day)
            date_to = date(payslip.date_to.year, payslip.date_to.month, payslip.date_to.day)            

            for d_ord in range(date_from.toordinal(), date_to.toordinal()+1):                
                d = date.fromordinal(d_ord)                                
                if (d.weekday() == 0):                    
                    count += 1
        else:
            raise UserWarning('Debe agregar un id de hr.payslip para el calculo de lunes')
                
        return count
