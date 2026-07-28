# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Paye',
    'version': '1.1',
    'summary': 'Permet de gérer la paie ',
    'sequence': 180,
    'description': """
Gestion de la paie
====================
    """,
    'license': 'OPL-1',
    'author': 'HSN Consult',
    'category': 'Ressources humaines',
    'website': 'http://www.hsnconsult.com',
    'depends': ['hr', 'hr_contract', 'hr_payroll', 'resource', 'account', 'report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'views/paye_view.xml',
        'reports/paye_report.xml',
        'reports/report_virement.xml',
        'reports/report_bulletin.xml',
        'reports/report_rubrique.xml',
        'reports/report_cnss.xml',
        'reports/report_its.xml',
        'reports/report_salarie.xml',
        'reports/report_fiche.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
