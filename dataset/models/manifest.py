# -*- coding: utf-8 -*-

from odoo import models, fields


class Manifest(models.Model):
    _name = 'dataset.manifest'
    _description = 'Manifest'
    _order = 'id desc'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    type = fields.Selection([
        ('dataset', 'Dataset'),
    ], string='Type', required=True, default='dataset')
    dataset_id = fields.Many2one('dataset', string='Dataset', ondelete='set null')
    total_chunks = fields.Integer(
        string='Expected Chunks',
        default=0,
        help="Expected number of chunks declared by this manifest. "
             "Used as the denominator for the dataset Fill Rate.",
    )

    _name_unique = models.Constraint(
        'unique(name)',
        "Manifest name must be unique!",
    )
