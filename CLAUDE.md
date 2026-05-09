# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **Odoo addon** for dataset management - provides models and views for organizing training and evaluation data in Odoo.

## Code Architecture

The addon follows standard Odoo addon structure:

```
dataset/
├── __init__.py          # Imports models package
├── __manifest__.py     # Odoo addon manifest (depends on 'base')
├── models/
│   ├── __init__.py     # Imports all model modules
│   ├── source.py       # dataset.source model
│   ├── package.py      # dataset.package model (hierarchical)
│   ├── dataset.py      # dataset model
│   ├── data_chunk.py   # dataset.data_chunk model
│   └── storage.py      # dataset.storage model
├── security/
│   └── ir.model.access.csv
└── views/
    ├── dataset_views.xml
    └── menu.xml
```

## Models

| Model | Description |
|-------|-------------|
| `dataset.source` | Data source (name, code, URL, description) |
| `dataset.package` | Hierarchical package (supports tree structure via parent_id/parent_path) |
| `dataset` | Dataset with source/package relations, state, chunk data type, record count |
| `dataset.data_chunk` | Individual data chunk linked to a dataset |
| `dataset.storage` | Storage provider config (S3, GCS, Azure, local file) |

## Common Development Tasks

- This is a self-contained Odoo addon - no build/lint/test commands exist in this repo
- To develop: clone into an Odoo addons path and run with Odoo server
- Models use Odoo ORM with `models.Model`, `fields.*`, and constraint definitions