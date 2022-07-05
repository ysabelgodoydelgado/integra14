from odoo import api, fields, models, _, exceptions
from datetime import datetime

from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
import math
from odoo.tools import float_compare, date_utils, email_split, email_re
from odoo.tools.misc import formatLang, format_date, get_lang

from datetime import date, timedelta
from collections import defaultdict
from itertools import zip_longest
from hashlib import sha256
from json import dumps

import ast
import json
import re
import warnings

import logging
_logger = logging.getLogger(__name__)


class AccountRetentionBinauralLineFacturacion(models.Model):
    _name = 'account.retention.line'
    _rec_name = 'name'

    @api.model_create_multi
    def create(self, vals_list):
        res = super(AccountRetentionBinauralLineFacturacion, self).create(vals_list)
        _logger.info('LINEA DE RETENCION DE ISLR')
        _logger.info(res)
        _logger.info('LINEA DE RETENCION DE ISLR VALS')
        _logger.info(vals_list)
        if not res.retention_id:
            _logger.info('NO TIENE RETENCION PADRE')
            retention_id = self.env['account.retention'].create({
                'state': 'draft',
                'type': 'in_invoice',
                'partner_id': res.invoice_id.partner_id.id,
                'type_retention': 'islr',
            })
            res.retention_id = retention_id.id
        else:
            _logger.info('SI TIENE RETENCION PADRE')
        return res

    @api.depends('invoice_id')
    def _retention_rate(self):
        for record in self:
            if record.invoice_id.move_type in ['in_invoice', 'in_refund']:
                record.retention_rate = record.invoice_id.partner_id.withholding_type.value
                record.invoice_type = record.invoice_id.move_type

    @api.onchange('retention_amount')
    def _onchange_retention_amount(self):
        foreign_currency_id = int(self.env['ir.config_parameter'].sudo().get_param('curreny_foreign_id'))
        decimal_function = self.env['decimal.precision'].search(
            [('name', '=', 'decimal_quantity')], limit=1)
        for record in self:
            if not self.env.context.get("noonchange"):
                if foreign_currency_id == 2:
                    value_rate = decimal_function.getCurrencyValue(
                        rate=record.invoice_id.foreign_currency_rate, base_currency="VEF", foreign_currency="USD")
                    if record.retention_amount > record.iva_amount and record.retention_id.type_retention in ['iva']:
                        return {
                            'warning': {
                                'title': 'El monto retenido excedende',
                                'message': 'El monto a retener no debe superar al IVA de la factura, por favor verificar'
                            },
                            'value': {
                                'retention_amount': 0
                            },
                        }
                    if float_compare(record.retention_amount,record.invoice_id.amount_residual,precision_digits=2) == 1 and record.retention_id:
                        return {
                            'warning': {
                                'title': 'El monto retenido excedende',
                                'message': 'El monto a retener no debe superar el monto adeudado de la factura, por favor verificar'
                            },
                            'value': {
                                'retention_amount': 0
                            },
                        }
                    record.foreign_retention_amount = record.retention_amount * value_rate
                elif foreign_currency_id == 3:
                    value_rate = decimal_function.getCurrencyValue(
                        rate=record.invoice_id.foreign_currency_rate, base_currency="USD", foreign_currency="VEF")
                    _logger.warning(value_rate)
                    record.foreign_retention_amount = record.retention_amount * value_rate
            self.env.context = self.with_context(noonchange=True).env.context

    @api.onchange('porcentage_retention')
    def _onchange_porcentage_retention(self):
        foreign_currency_id = int(self.env['ir.config_parameter'].sudo().get_param('curreny_foreign_id'))
        for record in self:
            if foreign_currency_id == 3:
                return {
                    'value': {
                        'retention_amount': record.facture_amount * (record.porcentage_retention/100)
                    },
                }
            elif foreign_currency_id == 2:
                return {
                    'value': {
                        'foreign_retention_amount': record.facture_amount * (record.porcentage_retention/100)
                    },
                }

    @api.onchange("payment_concept_id")
    @api.depends('payment_concept_id', 'invoice_id')
    def _get_value_related(self):
        self.related_tariff_id = None
        foreign_currency_id = int(self.env['ir.config_parameter'].sudo().get_param('curreny_foreign_id'))
        decimal_function = self.env['decimal.precision'].search(
            [('name', '=', 'decimal_quantity')], limit=1)
        for record in self:
            if (record.retention_id and record.retention_id.type_retention in ['islr'] and record.retention_id.type in ['in_invoice']) or (record.invoice_id and record.invoice_id.move_type in ['in_invoice', 'in_refund'] and not record.retention_id):
                currency_ut = self.env.ref('base.VEF')
                _logger.info('Moneda del sistema')
                _logger.info(record.company_currency_id)
                _logger.info('Moneda de la ut')
                _logger.info(currency_ut)
                if record.payment_concept_id:
                    for line in record.payment_concept_id.line_payment_concept_ids:
                        if record.invoice_id.partner_id.type_person_ids.id == line.type_person_ids.id:
                            amount_sustract = line.tariffs_ids.amount_sustract
                            from_pay = line.pay_from
                            _logger.info('Sustraendo')
                            _logger.info(amount_sustract)
                            record.related_pay_from = from_pay
                            record.related_percentage_tax_base = line.percentage_tax_base
                            _logger.warning(line.percentage_tax_base)
                            record.related_percentage_tariffs = line.tariffs_ids.percentage
                            record.related_tariff_id = line.tariffs_ids.id
                            record.related_amount_sustract_tariffs = amount_sustract
                if record.invoice_id:
                    _logger.info('invoice_idddddddddddddddddd')
                    _logger.info(record.facture_total)
                    _logger.info(record.facture_amount)
                    _logger.info(record.iva_amount)
                    record.facture_total = record.invoice_id.amount_total
                    record.facture_amount = record.invoice_id.amount_untaxed
                    record.iva_amount = record.invoice_id.amount_tax
                    record.invoice_type = record.invoice_id.move_type
                    record.foreign_facture_amount = record.invoice_id.foreign_amount_untaxed
                    record.foreign_facture_total = record.invoice_id.foreign_amount_total
                    record.foreign_iva_amount = record.invoice_id.foreign_amount_tax
                    record.foreign_currency_rate = record.invoice_id.foreign_currency_rate
            if (record.retention_id and record.retention_id.type_retention in ['islr'] and record.retention_id.type in ['in_invoice']) or (record.invoice_id and record.invoice_id.move_type in ['in_invoice', 'in_refund'] and not record.retention_id):
                if record.payment_concept_id and record.invoice_id:
                    if record.facture_amount > record.related_pay_from:
                        _logger.info('Calculos')
                        _logger.info(record.facture_amount)
                        _logger.info(record.related_percentage_tax_base/100)
                        _logger.info(record.related_percentage_tariffs/100)
                        _logger.info(record.related_amount_sustract_tariffs)
                        if foreign_currency_id == 2:
                            value_rate = decimal_function.getCurrencyValue(
                                rate=record.invoice_id.foreign_currency_rate, base_currency="VEF", foreign_currency="USD")
                            _logger.warning(record.invoice_id.foreign_currency_rate)
                            _logger.warning(value_rate)

                            record.retention_amount = (record.facture_amount * (record.related_percentage_tax_base/100) *\
                                    (record.related_percentage_tariffs/100)) - record.related_amount_sustract_tariffs

                            _logger.warning(record.facture_amount)
                            _logger.warning(record.related_percentage_tax_base)
                            _logger.warning((record.facture_amount * (record.related_percentage_tax_base/100) *
                                    (record.related_percentage_tariffs/100)) - record.related_amount_sustract_tariffs)
                            record.foreign_retention_amount = record.retention_amount * value_rate
                        elif foreign_currency_id == 3:
                            value_rate = decimal_function.getCurrencyValue(
                                rate=record.invoice_id.foreign_currency_rate, base_currency="VEF", foreign_currency="USD")
                            record.foreign_retention_amount = (record.foreign_facture_amount * (record.related_percentage_tax_base/100) *\
                                    (record.related_percentage_tariffs/100)) - record.related_amount_sustract_tariffs
                            record.retention_amount = record.foreign_retention_amount * value_rate
                        
    @api.onchange('facture_amount')
    def _onchange_base_islr(self):
        foreign_currency_id = int(self.env['ir.config_parameter'].sudo().get_param('curreny_foreign_id'))
        decimal_function = self.env['decimal.precision'].search(
            [('name', '=', 'decimal_quantity')], limit=1)
        base_currency = "VEF" if foreign_currency_id == 2 else "USD"
        foreign_currency = "USD" if foreign_currency_id == 2 else "VEF"
        for record in self:
            value_rate = decimal_function.getCurrencyValue(
                rate=record.invoice_id.foreign_currency_rate, base_currency=base_currency, foreign_currency=foreign_currency)
            if (record.retention_id and record.retention_id.type_retention in ['islr'] and record.retention_id.type in [
                'in_invoice']) or (
                    record.invoice_id and record.invoice_id.move_type in ['in_invoice', 'in_refund'] and not record.retention_id):
                if record.payment_concept_id and record.invoice_id:
                    if record.facture_amount > record.related_pay_from:
                        if foreign_currency_id == 2:
                            record.retention_amount = (record.facture_amount * (record.related_percentage_tax_base/100) *\
                                    (record.related_percentage_tariffs/100)) - record.related_amount_sustract_tariffs
                            record.foreign_retention_amount = record.retention_amount * value_rate
                        elif foreign_currency_id == 3:
                            record.foreign_retention_amount = (record.foreign_facture_amount * (record.related_percentage_tax_base/100) *\
                                    (record.related_percentage_tariffs/100)) - record.related_amount_sustract_tariffs
                            record.retention_amount = record.foreign_retention_amount * value_rate
                record.foreign_facture_amount = record.facture_amount * value_rate
            else:
                if record.retention_id and record.retention_id.type in ['in_invoice'] or (record.invoice_id and record.invoice_id.move_type in ['in_invoice', 'in_refund'] and not record.retention_id):
                    record.foreign_facture_amount = record.facture_amount * value_rate


    @api.onchange('foreign_facture_amount')
    def _onchange_foreign_facture_amount(self):
        foreign_currency_id = int(self.env['ir.config_parameter'].sudo().get_param('curreny_foreign_id'))
        decimal_function = self.env['decimal.precision'].search(
            [('name', '=', 'decimal_quantity')], limit=1)
        base_currency = "VEF" if foreign_currency_id == 2 else "USD"
        foreign_currency = "USD" if foreign_currency_id == 2 else "VEF"
        for record in self:
            value_rate = decimal_function.getCurrencyValue(
                rate=record.invoice_id.foreign_currency_rate, base_currency=base_currency, foreign_currency=foreign_currency)
            if record.retention_id and record.retention_id.type in ['out_invoice']:
                record.facture_amount = record.foreign_facture_amount * value_rate

    @api.onchange('foreign_retention_amount')
    def _onchange_foreigh_retention_amount(self):
        foreign_currency_id = int(self.env['ir.config_parameter'].sudo().get_param('curreny_foreign_id'))
        decimal_function = self.env['decimal.precision'].search(
            [('name', '=', 'decimal_quantity')], limit=1)
        for record in self:
            if not self.env.context.get("noonchange"):
                if record.retention_id and record.retention_id.type in ['out_invoice'] and record.foreign_currency_rate > 0:
                    if foreign_currency_id == 3:
                        if record.retention_amount > record.iva_amount and record.retention_id.type_retention in ['iva']:
                            return {
                                'warning': {
                                    'title': 'El monto retenido excedende',
                                    'message': 'El monto a retener no debe superar al IVA de la factura, por favor verificarc'
                                },
                                'value': {
                                    'retention_amount': 0
                                },
                            }
                        if float_compare(record.retention_amount,record.invoice_id.amount_residual,precision_digits=2) == 1 and record.retention_id:
                            return {
                                'warning': {
                                    'title': 'El monto retenido excedende',
                                    'message': 'El monto a retener no debe superar el monto adeudado de la factura, por favor verificarc'
                                },
                                'value': {
                                    'retention_amount': 0
                                },
                            }
                        value_rate = decimal_function.getCurrencyValue(
                            rate=record.foreign_currency_rate, base_currency="VEF", foreign_currency="USD")
                        _logger.warning(value_rate)
                        record.retention_amount = record.foreign_retention_amount * value_rate
                    elif foreign_currency_id == 2:
                        value_rate = decimal_function.getCurrencyValue(
                            rate=record.foreign_currency_rate, base_currency="VEF", foreign_currency="USD")
                        record.foreign_retention_amount = record.retention_amount * value_rate
            self.env.context = self.with_context(noonchange=True).env.context


    @api.depends("currency_id")
    def _compute_bs_currency_id(self):
        self.bs_currency_id = 3
                
    name = fields.Char('Descripción', size=64, select=True, required=True, default="Retención ISLR")
    currency_id = fields.Many2one(related="retention_id.company_currency_id")
    company_id = fields.Many2one('res.company', string='Company', change_default=True, required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency",
                                          readonly=True)
    retention_id = fields.Many2one('account.retention', 'Comprobante', ondelete='cascade', select=True,
                                   help="Comprobante")
    invoice_id = fields.Many2one('account.move', 'Factura', required=True, ondelete='cascade',
                                 select=True, help="Factura a retener")
    invoice_type = fields.Selection(selection=[
        ('out_invoice', 'Factura de Cliente'),
        ('out_refund', 'Nota de Crédito Cliente'),
        ('out_debit', 'Nota de Débito de Cliente'),
        ('in_invoice', 'Factura de Proveedor'),
        ('in_refund', 'Nota de Crédito de Proveedor'),
        ('in_debit', 'Nota de Crédito de Proveedor'),
    ], string='Tipo de Factura',)
    reference_invoice_number = fields.Char(string="Número de factura", related="invoice_id.name", store=True)
    tax_line = fields.Float(string='Alicuota')
    amount_tax_ret = fields.Float(string='Impuesto retenido',
                                  help="Total impuesto retenido de la factura")
    base_ret = fields.Float(string='Base imponible',
                            help="Base retenida de la factura")
    imp_ret = fields.Float(string='Impuesto Causado')
    retention_rate = fields.Float(compute=_retention_rate, store=True, string='Portancentaje de Retención',
                                  help="Porcentaje de Retencion ha aplicar a la factura")
    move_id = fields.Many2one('account.move', 'Movimiento Contable', help="Asiento Contable", ondelete='cascade')
    is_retention_client = fields.Boolean(string='registro de retencion de cliente', default=True)
    display_invoice_number = fields.Char(string='Display', compute='_compute_fields_combination_iva', store=True)
    
    facture_amount = fields.Float(string='Base Imponible')
    facture_total = fields.Float(string='Total Facturado')
    iva_amount = fields.Float(string="IVA factura")
    retention_amount = fields.Float(string='Monto Retenido')
    retention_amount = fields.Float(string='Monto Retenido')

    payment_concept_id = fields.Many2one('payment.concept', 'Concepto de pago', ondelete='cascade', select=True)
    
    #Campos para uso en ISLR
    porcentage_retention = fields.Float(string='% Retención')
    bs_currency_id = fields.Many2one("res.currency", compute="_compute_bs_currency_id")

    related_pay_from = fields.Float(string='Pagos desde', compute=_get_value_related, store=True)
    related_percentage_tax_base = fields.Float(string='% Base Imponible', compute=_get_value_related, store=True)
    related_percentage_tariffs = fields.Float(string='% Tarifa', compute=_get_value_related, store=True)
    related_amount_sustract_tariffs = fields.Float(string='Sustraendo', compute=_get_value_related, store=True)
    related_tariff_id = fields.Many2one('tarif.retention', compute=_get_value_related)
    
    # Moneda Alterna
    foreign_facture_amount = fields.Float(string='Base Imponible Anterna')
    foreign_facture_total = fields.Float(string='Total Facturado Alterno')
    foreign_iva_amount = fields.Float(string="Iva factura Alterno")
    foreign_retention_amount = fields.Float(string='Monto Retenido Alterno')
    foreign_retention_amount = fields.Float(string='Monto Retenido Alterno')
    foreign_currency_rate = fields.Float(string="Tasa", tracking=True)
