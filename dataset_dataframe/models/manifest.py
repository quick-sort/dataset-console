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
        help="Per-row dicts of the linked dataset's key_fields, derived by "
             "loading dataset_id.to_dataframe() and projecting only the "
             "key_fields columns. e.g. [{'split': 'train', 'shard': '0001'}, ...].",
    )

    @api.depends('dataset_id', 'dataset_id.key_fields', 'dataset_id.chunk_ids.metadata')
    def _compute_values(self):
        for record in self:
            record.values = self._derive_values(record.dataset_id)
            record.total_chunks = len(record.values or [])

    @staticmethod
    def _derive_values(dataset) -> list:
        if not dataset:
            return []
        key_fields = dataset.key_fields or []
        if not key_fields:
            return []
        df = dataset.to_dataframe()
        if df is None:
            return []
        cols = [k for k in key_fields if k in df.columns]
        if not cols:
            return []
        return df.select(cols).to_dicts()
