# -*- coding: utf-8 -*-

from odoo import models, fields


class Package(models.Model):
    _name = 'dataset.package'
    _description = 'Dataset Package'
    _order = 'id desc'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    description = fields.Text(string='Description')
    parent_id = fields.Many2one('dataset.package', string='Parent Package', index=True)
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('dataset.package', 'parent_id', string='Child Packages')

    _parent_store = True

    _name_parent_unique = models.Constraint(
        'unique(name, parent_id)',
        "Package name must be unique within same parent!",
    )

    _code_parent_unique = models.Constraint(
        'unique(code, parent_id)',
        "Package code must be unique within same parent!",
    )