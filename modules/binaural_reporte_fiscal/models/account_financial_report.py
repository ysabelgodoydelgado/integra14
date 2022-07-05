from odoo import models, fields, api, _
from odoo.tools.misc import formatLang
import logging

_logger = logging.getLogger(__name__)


class AccountFinancialReportBinaural(models.Model):
    _inherit = "account.financial.html.report"

    usd = fields.Boolean(string="¿Es en $?", default=False)


class AccountFinancialReportLineBinaural(models.Model):
    _inherit = 'account.financial.html.report.line'

    account_prefi = fields.Integer(string="Prefijo")
    type_control_ids = fields.Many2many('account.account.type', string='Tipo cuenta')

    @api.model
    def format_value(self, amount, currency=False, blank_if_zero=False):
        ''' Format amount to have a monetary display (with a currency symbol).
        E.g: 1000 => 1000.0 $

        :param amount:          A number.
        :param currency:        An optional res.currency record.
        :param blank_if_zero:   An optional flag forcing the string to be empty if amount is zero.
        :return:                The formatted amount as a string.

        MODIFICACIONES BINAURAL:
            Se agregó una condición para que se muestre el símbolo de la moneda correspondiente en
            cada reporte indistintamente de la moneda base (USD o BSF).
        '''
        parent_financial_report = self._get_financial_report()

        usd_report = True if (self._context.get("USD") or parent_financial_report.usd) else False

        foreign_currency_id = int(self.env['ir.config_parameter'].sudo().get_param('curreny_foreign_id'))
        foreign_currency_id = self.env["res.currency"].search([("id", '=', foreign_currency_id)])

        if foreign_currency_id.id == 2:
            currency_id = foreign_currency_id if usd_report else self.env.company.currency_id
        else:
            currency_id = self.env.company.currency_id if usd_report else foreign_currency_id

        if currency_id.is_zero(amount):
            if blank_if_zero:
                return ''
            # don't print -0.0 in reports
            amount = abs(amount)

        if self.env.context.get('no_format'):
            return amount
        return formatLang(self.env, amount, currency_obj=currency_id)


    def _compute_amls_results(self, options_list, calling_financial_report=None, sign=1):
        ''' Compute the results for the unfolded lines by taking care about the line order and the group by filter.

        Suppose the line has '-sum' as formulas with 'partner_id' in groupby and 'currency_id' in group by filter.
        The result will be something like:
        [
            (0, 'partner 0', {(0,1): amount1, (0,2): amount2, (1,1): amount3}),
            (1, 'partner 1', {(0,1): amount4, (0,2): amount5, (1,1): amount6}),
            ...               |
        ]    |                |
             |__ res.partner ids
                              |_ key where the first element is the period number, the second one being a res.currency id.

        :param options_list:                The report options list, first one being the current dates range, others
                                            being the comparisons.
        :param calling_financial_report:    The financial report called by the user to be rendered.
        :param sign:                        1 or -1 to get negative values in case of '-sum' formula.
        :return:                            A list (groupby_key, display_name, {key: <balance>...}).
        '''
        _logger.warning("USD CONTEXT:")
        _logger.warning(self.env.context.get("USD"))
        self.ensure_one()
        params = []
        queries = []

        foreign_currency_id = int(self.env['ir.config_parameter'].sudo().get_param('curreny_foreign_id'))

        AccountFinancialReportHtml = self.financial_report_id
        horizontal_groupby_list = AccountFinancialReportHtml._get_options_groupby_fields(options_list[0])
        groupby_list = [self.groupby] + horizontal_groupby_list
        groupby_clause = ','.join('account_move_line.%s' % gb for gb in groupby_list)
        groupby_field = self.env['account.move.line']._fields[self.groupby]

        ct_query = self.env['res.currency']._get_query_currency_table(options_list[0])
        parent_financial_report = self._get_financial_report()
        usd_report = parent_financial_report.usd

        # Prepare a query by period as the date is different for each comparison.

        for i, options in enumerate(options_list):
            new_options = self._get_options_financial_line(options)
            line_domain = self._get_domain(new_options, parent_financial_report)

            tables, where_clause, where_params = AccountFinancialReportHtml._query_get(new_options, domain=line_domain)

            if foreign_currency_id == 3:
                if usd_report:
                    currency = "currency_table.rate"
                else:
                    currency = "account_move_line.inverse_rate"
            else:
                if usd_report:
                    currency = "account_move_line.inverse_rate"
                else:
                    currency = "currency_table.rate"
            queries.append('''
                SELECT
                    ''' + (groupby_clause and '%s,' % groupby_clause) + '''
                    %s AS period_index,
                    COALESCE(SUM(ROUND(%s * account_move_line.balance * ''' + currency + ''', currency_table.precision)), 0.0) AS balance
                FROM ''' + tables + '''
                JOIN ''' + ct_query + ''' ON currency_table.company_id = account_move_line.company_id
                WHERE ''' + where_clause + '''
                ''' + (groupby_clause and 'GROUP BY %s' % groupby_clause) + '''
            ''')
            params += [i, sign] + where_params

        # Fetch the results.
        # /!\ Take care of both vertical and horizontal group by clauses.

        results = {}

        parent_financial_report._cr_execute(options_list[0], ' UNION ALL '.join(queries), params)
        for res in self._cr.dictfetchall():
            # Build the key.
            key = [res['period_index']]
            for gb in horizontal_groupby_list:
                key.append(res[gb])
            key = tuple(key)

            results.setdefault(res[self.groupby], {})
            results[res[self.groupby]][key] = res['balance']

        # Sort the lines according to the vertical groupby and compute their display name.
        if groupby_field.relational:
            # Preserve the table order by using search instead of browse.
            sorted_records = self.env[groupby_field.comodel_name].search([('id', 'in', tuple(results.keys()))])
            sorted_values = sorted_records.name_get()
        else:
            # Sort the keys in a lexicographic order.
            sorted_values = [(v, v) for v in sorted(list(results.keys()))]

        return [(groupby_key, display_name, results[groupby_key]) for groupby_key, display_name in sorted_values]

    def _compute_sum(self, options_list, calling_financial_report=None):
        ''' Compute the values to be used inside the formula for the current line.
        If called, it means the current line formula contains something making its line a leaf ('sum' or 'count_rows')
        for example.

        The results is something like:
        {
            'sum':                  {key: <balance>...},
            'sum_if_pos':           {key: <balance>...},
            'sum_if_pos_groupby':   {key: <balance>...},
            'sum_if_neg':           {key: <balance>...},
            'sum_if_neg_groupby':   {key: <balance>...},
            'count_rows':           {period_index: <number_of_rows_in_period>...},
        }

        ... where:
        'period_index' is the number of the period, 0 being the current one, others being comparisons.

        'key' is a composite key containing the period_index and the additional group by enabled on the financial report.
        For example, suppose a group by 'partner_id':

        The keys could be something like (0,1), (1,2), (1,3), meaning:
        * (0,1): At the period 0, the results for 'partner_id = 1' are...
        * (1,2): At the period 1 (first comparison), the results for 'partner_id = 2' are...
        * (1,3): At the period 1 (first comparison), the results for 'partner_id = 3' are...

        :param options_list:                The report options list, first one being the current dates range, others
                                            being the comparisons.
        :param calling_financial_report:    The financial report called by the user to be rendered.
        :return:                            A python dictionary.
        '''
        _logger.warning("USD CONTEXT:")
        _logger.warning(self.env.context.get("USD"))
        self.ensure_one()
        params = []
        queries = []

        foreign_currency_id = int(self.env['ir.config_parameter'].sudo().get_param('curreny_foreign_id'))

        AccountFinancialReportHtml = self.financial_report_id
        groupby_list = AccountFinancialReportHtml._get_options_groupby_fields(options_list[0])
        all_groupby_list = groupby_list.copy()
        groupby_in_formula = any(x in (self.formulas or '') for x in ('sum_if_pos_groupby', 'sum_if_neg_groupby'))
        if groupby_in_formula and self.groupby and self.groupby not in all_groupby_list:
            all_groupby_list.append(self.groupby)
        groupby_clause = ','.join('account_move_line.%s' % gb for gb in all_groupby_list)
        ct_query = self.env['res.currency']._get_query_currency_table(options_list[0])
        parent_financial_report = self._get_financial_report()

        usd_report = parent_financial_report.usd

        # Prepare a query by period as the date is different for each comparison.
        for i, options in enumerate(options_list):
            new_options = self._get_options_financial_line(options)
            line_domain = self._get_domain(new_options, parent_financial_report)

            tables, where_clause, where_params = AccountFinancialReportHtml._query_get(new_options, domain=line_domain)

            if foreign_currency_id == 3:
                if usd_report:
                    currency = "currency_table.rate"
                else:
                    currency = "account_move_line.inverse_rate"
            else:
                if usd_report:
                    currency = "account_move_line.inverse_rate"
                else:
                    currency = "currency_table.rate"
            queries.append('''
                SELECT
                    ''' + (groupby_clause and '%s,' % groupby_clause) + ''' %s AS period_index,
                    COUNT(DISTINCT account_move_line.''' + (self.groupby or 'id') + ''') AS count_rows,
                    COALESCE(SUM(ROUND(account_move_line.balance * ''' + currency + ''', currency_table.precision)), 0.0) AS balance
                FROM ''' + tables + '''
                JOIN ''' + ct_query + ''' ON currency_table.company_id = account_move_line.company_id
                WHERE ''' + where_clause + '''
                ''' + (groupby_clause and 'GROUP BY %s' % groupby_clause) + '''
            ''')
            params.append(i)
            params += where_params

        # Fetch the results.

        results = {
            'sum': {},
            'sum_if_pos': {},
            'sum_if_pos_groupby': {},
            'sum_if_neg': {},
            'sum_if_neg_groupby': {},
            'count_rows': {},
        }

        parent_financial_report._cr_execute(options_list[0], ' UNION ALL '.join(queries), params)
        for res in self._cr.dictfetchall():
            # Build the key.
            key = [res['period_index']]
            for gb in groupby_list:
                key.append(res[gb])
            key = tuple(key)

            # Compute values.
            results['count_rows'].setdefault(res['period_index'], 0)
            results['count_rows'][res['period_index']] += res['count_rows']
            results['sum'][key] = res['balance']
            if results['sum'][key] > 0:
                results['sum_if_pos'][key] = results['sum'][key]
                results['sum_if_pos_groupby'].setdefault(key, 0.0)
                results['sum_if_pos_groupby'][key] += res['balance']
            if results['sum'][key] < 0:
                results['sum_if_neg'][key] = results['sum'][key]
                results['sum_if_neg_groupby'].setdefault(key, 0.0)
                results['sum_if_neg_groupby'][key] += res['balance']
        return results

