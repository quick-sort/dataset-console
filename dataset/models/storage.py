# -*- coding: utf-8 -*-

from odoo import models, fields


class Storage(models.Model):
    _name = 'dataset.storage'
    _description = 'Dataset Storage'
    _order = 'id desc'

    name = fields.Char(string='Name', required=True)
    provider = fields.Selection([
        ('file', 'Local File'),
        ('s3', 'Amazon S3'),
        ('gs', 'Google Cloud Storage'),
        ('azure', 'Azure Blob'),
        ('http', 'HTTP/HTTPS'),
    ], string='Provider', required=True, default='file')
    config = fields.Json(string='Configuration', help='Connection configuration as JSON')
    is_default = fields.Boolean(string='Default', default=False)

    _name_unique = models.Constraint(
        'unique(name)',
        "Storage name must be unique!",
    )