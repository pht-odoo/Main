# -*- coding: utf-8 -*-
{
    'name': "GlasBox: Accounting budget calculated field",

    'summary': """
        This feature allows the user to keep track of the actual income and expenses for a project. 
        The theoretical amount and percentage do not get affected over time. Hence the period field is not relevant at all.""",

    'description': """
        Task ID: 2528354
        Long description of module's purpose
    """,

    'author': "Odoo Inc.",
    'website': "http://www.odoo.com",
    'category': 'Customizations',
    'license': 'OEEL-1',
    'version': '0.1',
    'depends': ['account_accountant', 'purchase', 'sale_management'],
    'data': [
        'views/sale_views.xml',
        'views/purchase_views.xml',
        'views/crossovered_budget_views.xml',
    ],
}
