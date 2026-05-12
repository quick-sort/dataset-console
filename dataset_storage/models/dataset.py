# -*- coding: utf-8 -*-

from odoo import models, fields


class Dataset(models.Model):
    _inherit = 'dataset'

    storage_id = fields.Many2one('dataset.storage', string='Storage', ondelete='restrict')
