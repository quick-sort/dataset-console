# -*- coding: utf-8 -*-

from odoo import models, fields


class Dataset(models.Model):
    _name = 'dataset'
    _description = 'Dataset'
    _order = 'id desc'

    name = fields.Char(string='Label', required=True)
    code = fields.Char(string='Code', required=True)
    source_id = fields.Many2one('dataset.source', string='Source', required=True, tracking=True)
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
        ('docx', 'Word'),
        ('xlsx', 'Excel'),
        ('json', 'JSON'),
        ('jsonl', 'JSONL'),
        ('parquet', 'Parquet'),
    ], string='Chunk Data Type', default='csv', tracking=True)
    key_fields = fields.Json(string='Key Fields', help='List of metadata keys used as chunk keys', tracking=True)
    chunk_ids = fields.One2many('dataset.data_chunk', 'dataset_id', string='Chunks')
    total_chunks = fields.Integer(
        string='Total Chunks',
        compute='_compute_total_chunks',
        store=True,
    )

    _code_source_unique = models.Constraint(
        'unique(code, source_id)',
        "Dataset code must be unique per source!",
    )

    _name_source_unique = models.Constraint(
        'unique(name, source_id)',
        "Dataset name must be unique per source!",
    )

    def _compute_total_chunks(self):
        for record in self:
            record.total_chunks = self.env['dataset.data_chunk'].search_count([
                ('dataset_id', '=', record.id)
            ])