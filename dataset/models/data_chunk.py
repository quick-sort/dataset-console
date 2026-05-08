# -*- coding: utf-8 -*-

from odoo import models, fields


class DataChunk(models.Model):
    _name = 'dataset.data_chunk'
    _description = 'Dataset Data Chunk'
    _order = 'id desc'

    key = fields.Char(string='Key', required=True)
    dataset_id = fields.Many2one('dataset', string='Dataset', required=True, index=True)
    description = fields.Text(string='Description')
    size = fields.Integer(string='Size')
    metadata = fields.Json(string='Metadata')

    _key_dataset_unique = models.Constraint(
        'unique(key, dataset_id)',
        "Chunk key must be unique within dataset!",
    )