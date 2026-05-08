# -*- coding: utf-8 -*-

from odoo import models, fields


class Source(models.Model):
    _name = 'dataset.source'
    _description = 'Dataset Source'
    _order = 'id desc'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    url = fields.Char(string='URL')
    description = fields.Text(string='Description')

    _code_unique = models.Constraint(
        'unique(code)',
        "Source code must be unique!",
    )

    _name_unique = models.Constraint(
        'unique(name)',
        "Source name must be unique!",
    )