# -*- coding: utf-8 -*-

{
    'name': 'Dataset Storage',
    'version': '1.0',
    'category': 'Uncategorized',
    'summary': 'Dataset storage backend',
    'description': """
Dataset Storage
=============
Provides storage backend for datasets.
    """,
    'author': 'Quick Sort',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'dataset', 'component'],
    'data': [
        'security/ir.model.access.csv',
        'views/storage_views.xml',
    ],
    'installable': True,
    'application': True,
}