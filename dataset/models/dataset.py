# -*- coding: utf-8 -*-

from odoo import models, fields


class Dataset(models.Model):
    _name = 'dataset'
    _description = 'Dataset'
    _order = 'id desc'

    name = fields.Char(string='Label', required=True)
    code = fields.Char(string='Code', required=True)
    source_id = fields.Many2one('dataset.source', string='Source', required=True)
    package_id = fields.Many2one('dataset.package', string='Package', index=True)
    description = fields.Text(string='Description')
    state = fields.Selection([
        ('missing', 'Missing'),
        ('exists', 'Exists'),
        ('checked', 'Checked'),
    ], string='State', default='missing')
    chunk_data_type = fields.Selection([
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
        ('xlsx', 'XLSX'),
        ('parquet', 'Parquet'),
    ], string='Chunk Data Type')
    key_fields = fields.Json(string='Key Fields', help='List of metadata keys used as chunk keys')
    record_count = fields.Integer(string='Record Count', default=0)

    _code_source_unique = models.Constraint(
        'unique(code, source_id)',
        "Dataset code must be unique per source!",
    )

    _code_package_unique = models.Constraint(
        'unique(code, package_id)',
        "Dataset code must be unique per package!",
    )

    _name_parent_unique = models.Constraint(
        'unique(name, parent_id)',
        "Dataset name must be unique per package!",
    )

    _name_source_unique = models.Constraint(
        'unique(name, source_id)',
        "Dataset name must be unique per source!",
    )