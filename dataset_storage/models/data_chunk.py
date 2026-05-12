# -*- coding: utf-8 -*-

import base64

from odoo import models, fields


class DataChunk(models.Model):
    _inherit = 'dataset.data_chunk'

    raw_data = fields.Binary(
        string='Raw Data',
        compute='_compute_raw_data',
        inverse='_inverse_raw_data',
        attachment=False,
    )

    def _compute_raw_data(self) -> None:
        for record in self:
            storage = record.dataset_id.storage_id
            if not storage or not record.key or not storage.key_exist(record.key):
                record.raw_data = False
                continue
            record.raw_data = base64.b64encode(storage.read_key(record.key))

    def _inverse_raw_data(self) -> None:
        for record in self:
            storage = record.dataset_id.storage_id
            if not storage or not record.key:
                continue
            if record.raw_data:
                storage.write_key(record.key, base64.b64decode(record.raw_data))
            elif storage.key_exist(record.key):
                storage.delete_key(record.key)

    def raw_data_exist(self) -> bool:
        self.ensure_one()
        storage = self.dataset_id.storage_id
        if not storage or not self.key:
            return False
        return storage.key_exist(self.key)

    def cleanup_raw_data(self) -> None:
        for record in self:
            storage = record.dataset_id.storage_id
            if not storage or not record.key:
                continue
            if storage.key_exist(record.key):
                storage.delete_key(record.key)
