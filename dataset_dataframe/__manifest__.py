# -*- coding: utf-8 -*-

{
    'name': 'Dataset DataFrame',
    'version': '1.0',
    'category': 'Tools',
    'summary': 'Read dataset chunks as Polars DataFrames',
    'description': """
Dataset DataFrame
=================
Extends ``dataset`` and ``dataset.data_chunk`` with ``to_dataframe()``
helpers backed by Polars. Supports CSV and Parquet chunk types.
    """,
    'author': 'Quick Sort',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['dataset', 'dataset_storage'],
    'external_dependencies': {
        'python': ['polars'],
    },
    'data': [
        'views/manifest_views.xml',
        'views/data_chunk_views.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': False,
}
