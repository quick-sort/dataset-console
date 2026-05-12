# -*- coding: utf-8 -*-

from odoo import models, fields


class Dataset(models.Model):
    _inherit = 'dataset'

    storage_id = fields.Many2one('dataset.storage', string='Storage', ondelete='restrict')

    def scan_chunks(self) -> int:
        self.ensure_one()
        if not self.storage_id:
            raise ValueError("no storage configured")
        source_code = self.source_id.code
        dataset_code = self.code
        prefix = f"{source_code}/{dataset_code}"
        if self.key_fields:
            prefix += "/"
        else:
            prefix += "."
        keys = self.storage_id.list_keys(prefix)
        existing_keys = {chunk.key for chunk in self.chunk_ids if chunk.key}
        new_keys = [k for k in keys if k not in existing_keys]
        if not new_keys:
            return 0
        key_fields = self.key_fields or []
        Dataset = self.env['dataset']
        to_create = []
        for key in new_keys:
            parsed = Dataset.parse_chunk_key(key, key_fields)
            to_create.append({
                'dataset_id': self.id,
                'metadata': parsed.get('metadata'),
            })
        self.env['dataset.data_chunk'].create(to_create)
        return len(to_create)
