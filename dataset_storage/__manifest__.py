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
    'depends': ['base', 'dataset', 'component', 'queue_job'],
    'external_dependencies': {
        'python': ['fsspec', 's3fs'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/storage_data.xml',
        'views/storage_views.xml',
        'views/dataset_views.xml',
        'views/data_chunk_views.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'test': [
        'tests/test_storage.py',
    ],
    'installable': True,
    'application': True,
}