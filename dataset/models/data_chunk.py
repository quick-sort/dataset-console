# -*- coding: utf-8 -*-

from odoo import models, fields


class DataChunk(models.Model):
    _name = 'dataset.data_chunk'
    _description = 'Dataset Data Chunk'
    _order = 'id desc'

    key = fields.Char(
        string='Key',
        compute='_compute_key',
        store=True,
        readonly=False,
        tracking=True,
        index=True,
    )
    dataset_id = fields.Many2one('dataset', string='Dataset', required=True, index=True, ondelete='restrict')
    description = fields.Text(string='Description')
    size = fields.Integer(
        string='Size in bytes',
        compute='_compute_size',
        store=True,
        readonly=True,
    )
    metadata = fields.Json(string='Metadata', tracking=True)
    raw_data = fields.Binary(string='Raw Data', attachment=True)
    raw_data_filename = fields.Char(string='Raw Data Filename')
    state = fields.Selection([
        ('missing', 'Missing'),
        ('exists', 'Exists'),
        ('checked', 'Checked'),
    ], string='State', default='missing', tracking=True)

    _key_dataset_unique = models.Constraint(
        'unique(key, dataset_id)',
        "Chunk key must be unique within dataset!",
    )

    def _compute_key(self):
        for record in self:
            if not record.dataset_id:
                record.key = False
                continue
            record.key = record.dataset_id.build_chunk_key(record.metadata)

    def _compute_size(self):
        for record in self:
            if not record.dataset_id or not record.key:
                record.size = 0
                continue
            storage = record.dataset_id.storage_id
            if not storage:
                record.size = 0
                continue
            try:
                record.size = storage.get_size(record.key)
            except Exception:
                record.size = 0