# -*- coding: utf-8 -*-

from odoo import models, fields


class Storage(models.Model):
    _name = 'dataset.storage'
    _description = 'Dataset Storage'
    _order = 'id desc'
    _inherit = ['collection.base']

    name = fields.Char(string='Name', required=True)
    backend_type = fields.Selection(
        selection=[('fsspec', 'fsspec')],
        default='fsspec',
        required=True,
    )
    config = fields.Json(string='Configuration', help='Connection configuration as JSON')
    gzip = fields.Boolean(
        string='Gzip',
        default=True,
        help='If enabled, raw data is gzip-compressed when written to storage.',
    )

    _name_unique = models.Constraint(
        'unique(name)',
        "Storage name must be unique!",
    )

    def _adapter(self):
        self.ensure_one()
        with self.work_on(self._name) as work:
            return work.component(usage=self.backend_type)

    def key_exist(self, key: str) -> bool:
        return self._adapter().key_exist(key)

    def read_key(self, key: str) -> bytes:
        return self._adapter().read_key(key)

    def write_key(self, key: str, data: bytes) -> None:
        return self._adapter().write_key(key, data)

    def delete_key(self, key: str) -> None:
        return self._adapter().delete_key(key)

    def list_keys(self, prefix: str | None = None) -> list[str]:
        return self._adapter().list_keys(prefix)

    def get_size(self, key: str) -> int:
        return self._adapter().get_size(key)
