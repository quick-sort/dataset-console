# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Manifest(models.Model):
    _name = 'dataset.manifest'
    _description = 'Manifest'
    _order = 'id desc'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    type = fields.Selection([
        ('dataset', 'Dataset'),
    ], string='Type', required=True, default='dataset')
    values = fields.Json(
        string='Values',
        help="List of chunk metadata dicts declared by this manifest, "
             "e.g. [{'split': 'train', 'shard': '0001'}, ...]. Each dict "
             "maps the dataset's key_fields to the value identifying one "
             "expected chunk.",
    )
    total_chunks = fields.Integer(
        string='Expected Chunks',
        compute='_compute_total_chunks',
        store=True,
        help="Expected number of chunks declared by this manifest "
             "(``len(values)``). Used as the denominator for the dataset Fill Rate.",
    )

    _name_unique = models.Constraint(
        'unique(name)',
        "Manifest name must be unique!",
    )

    @api.depends('values')
    def _compute_total_chunks(self):
        for record in self:
            record.total_chunks = len(record.values or [])
