from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

class BinauralHrSalaryRuleInherit(models.Model):
    _inherit = 'hr.salary.rule'
    _description = 'Herencia para agregar nuevas variables a las reglas salariales'

    condition_python = fields.Text(string='Python Condition', required=True,
        default='''
            # Available variables:
            #----------------------
            # payslip: object containing the payslips
            # employee: hr.employee object
            # contract: hr.contract object
            # rules: object containing the rules code (previously computed)
            # categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
            # worked_days: object containing the computed worked days
            # inputs: object containing the computed inputs.
            # salario_minimo_actual: salario minimo actual asignado por configuracion general
            # porc_faov: float con porcentaje de deduccion FAOV asignado por configuracion general
            # porc_ince: float con porcentaje de deduccion INCE asignado por configuracion general
            # porc_ivss: float con porcentaje de deduccion IVSS asignado por configuracion general
            # tope_ivss: int con tope de salarios para deduccion IVSS asignado por configuracion
            # maximo_deduccion_ivss: float con monto maximo de deduccion IVSS (calculado automatico por configuracion)
            # porc_pf: float con porcentaje de deduccion paro forzoso asignado por configuracion general
            # tope_pf: int con tope de salarios para deduccion paro forzoso asignado por configuracion
            # maximo_deduccion_pf: float con monto maximo de deduccion paro forzoso (calculado automatico por configuracion)
            # porcentaje_recargo_nocturno: porcentaje de recargo para bono nocturno mensual

            # Note: returned value have to be set in the variable 'result'

            result = rules.NET > categories.NET * 0.10''',
        help='Applied this rule for calculation if condition is true. You can specify condition like basic > 1000.')

    amount_python_compute = fields.Text(string='Python Code',
        default='''
            # Available variables:
            #----------------------
            # payslip: object containing the payslips
            # employee: hr.employee object
            # contract: hr.contract object
            # rules: object containing the rules code (previously computed)
            # categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
            # worked_days: object containing the computed worked days.
            # inputs: object containing the computed inputs.
            # salario_minimo_actual: salario minimo actual asignado por configuracion general
            # porc_faov: float con porcentaje de deduccion FAOV asignado por configuracion general
            # porc_ince: float con porcentaje de deduccion INCE asignado por configuracion general
            # porc_ivss: float con porcentaje de deduccion IVSS asignado por configuracion general
            # tope_ivss: int con tope de salarios para deduccion IVSS asignado por configuracion
            # maximo_deduccion_ivss: float con monto maximo de deduccion IVSS (calculado automatico por configuracion)
            # porc_pf: float con porcentaje de deduccion paro forzoso asignado por configuracion general
            # tope_pf: int con tope de salarios para deduccion paro forzoso asignado por configuracion
            # maximo_deduccion_pf: float con monto maximo de deduccion paro forzoso (calculado automatico por configuracion)
            # porcentaje_recargo_nocturno: porcentaje de recargo para bono nocturno mensual

            # Note: returned value have to be set in the variable 'result'

            result = contract.wage * 0.10''')