# -*- coding: utf-8 -*-
{
    'name': "binaural facturacion",

    'summary': """
       Modulo para el proceso de Facturacion, Retenciones etc """,

    'description': """
        Modulo para el proceso de Compra/Facturacion/Retenciones asi como Facturacion/Retenciones con manejo de multimonedas
    """,

    'author': "Binauraldev",
    'website': "https://binauraldev.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting/Accounting',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'binaural_contactos_configuraciones', 'account_accountant', 'binaural_currency_extend'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/config_sequence.xml',
        'data/formato_papel.xml',
        'views/igtf_config.xml',
        'views/res_config.xml',
        'views/config_views.xml',
        'views/account_move_form_inh.xml',
        'views/account_move_search_inh.xml',
        'views/account_move_trees_inh.xml',
        'views/account_retention.xml',
        'views/account_retention_islr.xml',
        'views/account_payment.xml',
        'views/account_journal.xml',
        'views/account_bank_statement.xml',
        'views/res_company_views.xml',
        'views/account_move_line_inh.xml',
        'views/account_municipality_retention.xml',
        'wizard/account_payment_register.xml',
        'wizard/minicipality_retentions_xlsx.xml',
        'wizard/municipality_retentions_report_xlsx.xml',
        'wizard/municipality_retentions_report_patent_xlsx.xml',
        'report/invoice_free_form_bs.xml',
        'report/invoice_free_form.xml',
        'report/report_invoice_document_override.xml',
        'views/product_category_views.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'application': True,
}
