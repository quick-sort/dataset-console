# -*- coding: utf-8 -*-

from odoo import models, fields


class DatasetTag(models.Model):
    _name = 'dataset.tag'
    _description = 'Dataset Tag'

    name = fields.Char(string='Name', required=True, index=True)
    color = fields.Integer(string='Color Index', default=0)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Tag name must be unique!'),
    ]