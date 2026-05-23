# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Manifest(models.Model):
    _inherit = 'dataset.manifest'

    dataset_id = fields.Many2one('dataset', string='Dataset', ondelete='set null')
    values = fields.Json(
        string='Values',
        compute='_compute_values',
        store=True,
        readonly=True,
        help="All columns of the linked dataset's dataframe as a list of dicts.",
    )

    @api.depends('dataset_id', 'dataset_id.chunk_ids')
    def _compute_values(self):
        for record in self:
            values = []
            if record.dataset_id:
                df = record.dataset_id.to_dataframe()
                if df is not None and not df.is_empty():
                    values = df.to_dicts()
                
            record.values = values
            record.total_chunks = len(values)

    def action_refresh_values(self):
        self.ensure_one()
        self._compute_values()
        self.flush_recordset()