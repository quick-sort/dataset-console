# -*- coding: utf-8 -*-

{
    'name': 'Dataset Management',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'summary': 'Catalog and manage datasets for AI training and evaluation',
    'description': """
Dataset Management
==================

Catalog, organize and track datasets used for AI/ML training and evaluation.

Features
--------
* **Sources** — register external data providers (name, code, URL, description).
* **Packages** — group datasets into a hierarchical, tree-structured taxonomy.
* **Datasets** — track each dataset with its source, package, lifecycle state
  (missing / exists / checked) and chunk data type (PDF, CSV, DOCX, XLSX,
  JSON, JSONL, Parquet).
* **Data chunks** — break datasets into individually addressable chunks with
  auto-computed keys derived from source/dataset codes and configurable
  metadata key fields.
* **Kanban, list and search-panel views** — browse datasets visually and
  filter by source or hierarchical package.
* **Dataset Manager** security group for elevated access.

Storage backends (S3, GCS, Azure, local file, ...) are provided by the
companion ``dataset_storage`` addon and its backend-specific extensions.
    """,
    'author': 'Quick Sort',
    'website': '',
    'license': 'LGPL-3',
    'icon': '/dataset/static/description/stock.svg',
    'depends': ['base'],
    'data': [
        'security/dataset_manager.xml',
        'security/ir.model.access.csv',
        'views/source_views.xml',
        'views/package_views.xml',
        'views/manifest_views.xml',
        'views/data_chunk_views.xml',
        'views/dataset_views.xml',
        'wizards/data_chunk_metadata_wizard_views.xml',
        'views/menu.xml',
    ],
    'demo': [
        'demo/dataset_demo.xml',
    ],
    'images': [
        'static/description/stock.svg',
    ],
    'installable': True,
    'application': True,
}