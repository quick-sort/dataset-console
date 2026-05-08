# -*- coding: utf-8 -*-

{
    'name': 'Dataset Management',
    'version': '1.0',
    'category': 'Uncategorized',
    'summary': 'Manage datasets for training and evaluation',
    'description': """
Dataset Management
==================
Provides dataset management capabilities for organizing training
and evaluation data in Odoo.
    """,
    'author': 'Quick Sort',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/dataset_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
}