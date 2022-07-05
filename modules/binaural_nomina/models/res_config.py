# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

class ResConfigSettingsBinauralNomina(models.TransientModel):
    _inherit = 'res.config.settings'

    _sql_constraints = [
        ('dia_adicional_posterior','CHECK(dia_adicional_posterior > 0)',
            'Dia adicional tiene que ser positivo'),
        ('dia_vacaciones_anno','CHECK(dia_vacaciones_anno > 0)',
            'Cantidad de dias de disfrute tiene que ser positivo'),
        ('dia_adic_cc','CHECK(dia_adic_cc >= 0)',
            'Dias adicionales por contratacion colectiva tiene que ser positivo'),
        ('dia_adic_bono_cc','CHECK(dia_adic_bono_cc >= 0)',
            'Dias adicionales de bono por contratacion colectiva tiene que ser positivo'),
        ('dias_utilidades','CHECK(dias_utilidades >= 0)',
            'Cantidad de días de utilidades tiene que ser positivo'),
        ('dias_prestaciones_mes','CHECK(dias_prestaciones_mes >= 0)',
            'Cantidad de días acumulados de prestaciones al mes tiene que ser positivo'),
        ('dias_prestaciones_anno','CHECK(dias_prestaciones_anno >= 0)',
            'Cantidad de días de prestaciones por año cumplido tiene que ser positivo'),
        ('maximo_dias_prestaciones_anno','CHECK(maximo_dias_prestaciones_anno >= 0)',
            'Cantidad máxima de días por años cumplidos tiene que ser positivo'),
    ]

    sueldo_base_ley = fields.Float(string="Sueldo base de ley", help="Sueldo base de ley", digits=(9,2))
    porcentaje_deduccion_faov = fields.Float(string="Porcentaje de deduccion FAOV", help="Porcentaje que se usara para la deduccion", digits=(5,2))
    porcentaje_deduccion_ince = fields.Float(string="Porcentaje de deduccion INCE", help="Porcentaje que se usara para la deduccion", digits=(5,2))

    porcentaje_deduccion_ivss = fields.Float(string="Porcentaje de deduccion IVSS", help="Porcentaje que se usara para la deduccion", digits=(5,2))
    tope_salario_ivss = fields.Integer(string="Tope salario IVSS", help="Cantidad de salarios maximos usados para el calculo de la deduccion")
    monto_maximo_ivss = fields.Float(string="Monto maximo deduccion", store=True, readonly=True)

    porcentaje_deduccion_pf = fields.Float(string="Porcentaje de deduccion Paro Forzoso", help="Porcentaje que se usara para la deduccion", digits=(5,2))
    tope_salario_pf = fields.Integer(string="Tope salario Paro Forzoso", help="Cantidad de salarios maximos usados para el calculo de la deduccion")
    monto_maximo_pf = fields.Float(string="Monto maximo deduccion Paro Forzoso", store=True, readonly=True)

    #bono nocturno
    porcentaje_recargo_nocturno = fields.Float(string="Porcentaje de recargo para horas nocturas", help="Porcentaje de recargo para calcular el pago de hora nocturna", digits=(5,2))

    #vacaciones
    dia_adicional_posterior = fields.Integer(string="Dias adicionales posterior al primer año", help="Día adicional posterior al primer año de trabajo para el bono")
    dia_vacaciones_anno = fields.Integer(string="Cantidad de días de disfrute año 1", help="Cantidad de días de disfrute año 1")
    dia_adic_cc = fields.Integer(string="Dias adicionales por contratación colectiva", help="Dias adicionales por contratación colectiva", default=0)
    dia_adic_bono_cc = fields.Integer(string="Dias adicionales de bono por contratación colectiva", help="Dias adicionales de bono por contratación colectiva", default=0)

    #utilidades
    tipo_utilidades = fields.Selection(
        [('last_wage','Ultimo sueldo devengado'),
         ('avg_last_month','Promedio de sueldo devengado de los últimos dos meses')],
        "Base para utilidades", default='last_wage')
    dias_utilidades = fields.Integer(string="Cantidad de días de utilidades", help="Cantidad de días de utilidades")

    #prestaciones
    dias_prestaciones_mes = fields.Integer(
        string="Cantidad de días al mes", help="Cantidad de días acumulados de prestaciones al mes")
    dias_prestaciones_anno = fields.Integer(
        string="Cantidad de días por año cumplido", help="Cantidad de días acumulados de prestaciones por año cumplido")
    maximo_dias_prestaciones_anno = fields.Integer(
        string="Cantidad máxima de días por años cumplidos", help="Cantidad máxima de días por años cumplidos")
    tipo_calculo_intereses_prestaciones = fields.Selection(
        [("fideicomiso", "Fideicomiso"),
         ("interno", "Interno")],
        "Tipo de calculo de intereses de prestaciones", default="fideicomiso",
        help="Si los intereses de prestaciones se calculan internamente o por fideicomiso")
    tasa_intereses_prestaciones = fields.Float(
        string="Tasa mensual de intereses de prestaciones",
        help="% de Tasa Mensual de Intereses de Prestaciones.")

    def set_values(self):
        super(ResConfigSettingsBinauralNomina, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('sueldo_base_ley',self.sueldo_base_ley)

        self.env['ir.config_parameter'].sudo().set_param('porcentaje_deduccion_faov',self.porcentaje_deduccion_faov)
        self.env['ir.config_parameter'].sudo().set_param('porcentaje_deduccion_ince',self.porcentaje_deduccion_ince)

        self.env['ir.config_parameter'].sudo().set_param('porcentaje_deduccion_ivss',self.porcentaje_deduccion_ivss)
        self.env['ir.config_parameter'].sudo().set_param('tope_salario_ivss',self.tope_salario_ivss)
        self.env['ir.config_parameter'].sudo().set_param('monto_maximo_ivss',self.monto_maximo_ivss)

        self.env['ir.config_parameter'].sudo().set_param('porcentaje_deduccion_pf',self.porcentaje_deduccion_pf)
        self.env['ir.config_parameter'].sudo().set_param('tope_salario_pf',self.tope_salario_pf)
        self.env['ir.config_parameter'].sudo().set_param('monto_maximo_pf',self.monto_maximo_pf)

        #bono nocturno
        self.env['ir.config_parameter'].sudo().set_param('porcentaje_recargo_nocturno',self.porcentaje_recargo_nocturno)

        #vacaciones
        self.env['ir.config_parameter'].sudo().set_param('dia_adicional_posterior',self.dia_adicional_posterior)
        self.env['ir.config_parameter'].sudo().set_param('dia_vacaciones_anno',self.dia_vacaciones_anno)
        self.env['ir.config_parameter'].sudo().set_param('dia_adic_cc',self.dia_adic_cc)
        self.env['ir.config_parameter'].sudo().set_param('dia_adic_bono_cc',self.dia_adic_bono_cc)
        
        #utilidades
        self.env['ir.config_parameter'].sudo().set_param('tipo_utilidades',self.tipo_utilidades)
        self.env['ir.config_parameter'].sudo().set_param('dias_utilidades',self.dias_utilidades)

        #prestaciones
        self.env['ir.config_parameter'].sudo().set_param('dias_prestaciones_mes',self.dias_prestaciones_mes)
        self.env['ir.config_parameter'].sudo().set_param('dias_prestaciones_anno',self.dias_prestaciones_anno)
        self.env['ir.config_parameter'].sudo().set_param('maximo_dias_prestaciones_anno',self.maximo_dias_prestaciones_anno)
        self.env['ir.config_parameter'].sudo().set_param('tipo_calculo_intereses_prestaciones',self.tipo_calculo_intereses_prestaciones)
        self.env['ir.config_parameter'].sudo().set_param('tasa_intereses_prestaciones',self.tasa_intereses_prestaciones)

    @api.model
    def get_values(self):
        res = super(ResConfigSettingsBinauralNomina, self).get_values()
        res['sueldo_base_ley'] = self.env['ir.config_parameter'].sudo().get_param('sueldo_base_ley')

        res['porcentaje_deduccion_faov'] = self.env['ir.config_parameter'].sudo().get_param('porcentaje_deduccion_faov')
        res['porcentaje_deduccion_ince'] = self.env['ir.config_parameter'].sudo().get_param('porcentaje_deduccion_ince')
        
        res['porcentaje_deduccion_ivss'] = self.env['ir.config_parameter'].sudo().get_param('porcentaje_deduccion_ivss')
        res['tope_salario_ivss'] = self.env['ir.config_parameter'].sudo().get_param('tope_salario_ivss')
        res['monto_maximo_ivss'] = self.env['ir.config_parameter'].sudo().get_param('monto_maximo_ivss')

        res['porcentaje_deduccion_pf'] = self.env['ir.config_parameter'].sudo().get_param('porcentaje_deduccion_pf')
        res['tope_salario_pf'] = self.env['ir.config_parameter'].sudo().get_param('tope_salario_pf')
        res['monto_maximo_pf'] = self.env['ir.config_parameter'].sudo().get_param('monto_maximo_pf')

        #bono nocturno
        res['porcentaje_recargo_nocturno'] = self.env['ir.config_parameter'].sudo().get_param('porcentaje_recargo_nocturno')

        #vacaciones
        res['dia_adicional_posterior'] = self.env['ir.config_parameter'].sudo().get_param('dia_adicional_posterior')
        res['dia_vacaciones_anno'] = self.env['ir.config_parameter'].sudo().get_param('dia_vacaciones_anno')
        res['dia_adic_cc'] = self.env['ir.config_parameter'].sudo().get_param('dia_adic_cc')
        res['dia_adic_bono_cc'] = self.env['ir.config_parameter'].sudo().get_param('dia_adic_bono_cc')

        #utilidades
        res['tipo_utilidades'] = self.env['ir.config_parameter'].sudo().get_param('tipo_utilidades')
        res['dias_utilidades'] = self.env['ir.config_parameter'].sudo().get_param('dias_utilidades')
        
        #prestaciones
        res['dias_prestaciones_mes'] = self.env['ir.config_parameter'].sudo().get_param('dias_prestaciones_mes')
        res['dias_prestaciones_anno'] = self.env['ir.config_parameter'].sudo().get_param('dias_prestaciones_anno')
        res['maximo_dias_prestaciones_anno'] = self.env['ir.config_parameter'].sudo().get_param('maximo_dias_prestaciones_anno')
        res['tipo_calculo_intereses_prestaciones'] = self.env['ir.config_parameter'].sudo().get_param('tipo_calculo_intereses_prestaciones')
        res['tasa_intereses_prestaciones'] = self.env['ir.config_parameter'].sudo().get_param('tasa_intereses_prestaciones')

        return res

    @api.onchange('sueldo_base_ley','tope_salario_ivss','tope_salario_pf')
    def _onchange_topes_maximos(self):
        self.monto_maximo_ivss = self.sueldo_base_ley * self.tope_salario_ivss
        self.monto_maximo_pf = self.sueldo_base_ley * self.tope_salario_pf
