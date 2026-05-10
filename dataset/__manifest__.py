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
    'icon': '/dataset/static/description/stock.svg',
    'depends': ['base'],
    'data': [
        'security/dataset_manager.xml',
        'security/ir.model.access.csv',
        'views/dataset_views.xml',
        'views/menu.xml',
    ],
    'images': [
        'static/description/stock.svg',
    ],
    'installable': True,
    'application': True,
}