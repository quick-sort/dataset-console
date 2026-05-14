# -*- coding: utf-8 -*-

import gzip

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

    def _resolve_key(self, key: str) -> str:
        config: dict = self.config or {}
        root: str = config.get('root', '')
        resolved = f"{root.rstrip('/')}/{key}" if root else key
        if self.gzip:
            resolved += '.gz'
        return resolved

    def _adapter(self):
        self.ensure_one()
        with self.work_on(self._name) as work:
            return work.component(usage=self.backend_type)

    def key_exist(self, key: str) -> bool:
        return self._adapter().key_exist(self._resolve_key(key))

    def read_key(self, key: str) -> bytes:
        data = self._adapter().read_key(self._resolve_key(key))
        if self.gzip:
            data = gzip.decompress(data)
        return data

    def write_key(self, key: str, data: bytes) -> None:
        if self.gzip:
            data = gzip.compress(data)
        return self._adapter().write_key(self._resolve_key(key), data)

    def delete_key(self, key: str) -> None:
        return self._adapter().delete_key(self._resolve_key(key))

    def list_keys(self, prefix: str | None = None) -> list[str]:
        config: dict = self.config or {}
        root: str = config.get('root', '')
        search = f"{root.rstrip('/')}/{prefix}" if prefix else root
        if not search:
            return []
        keys = self._adapter().list_keys(search)
        result = []
        for k in keys:
            if root:
                k = k[len(root) + 1:] if k.startswith(root + '/') else k
            if self.gzip and k.endswith('.gz'):
                k = k[:-5]
            result.append(k)
        return result

    def get_size(self, key: str) -> int:
        return self._adapter().get_size(self._resolve_key(key))
