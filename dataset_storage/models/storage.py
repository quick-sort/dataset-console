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
    gzip_chunk_types = fields.Json(
        string='Gzip Chunk Types',
        default=lambda _: ['csv', 'json', 'jsonl'],
        help='Chunk types whose payloads are gzip-compressed on write and unwrapped on read. '
             'Keys with any other extension (e.g. parquet) pass through untouched. '
             'Set to [] to disable gzip entirely for this storage.',
    )

    _name_unique = models.Constraint(
        'unique(name)',
        "Storage name must be unique!",
    )

    @classmethod
    def _key_chunk_type(cls, key: str) -> str:
        return key.rsplit('.', 1)[-1] if '.' in key else ''

    def _should_gzip(self, key: str) -> bool:
        return self._key_chunk_type(key) in (self.gzip_chunk_types or [])

    def _resolve_key(self, key: str) -> str:
        config: dict = self.config or {}
        root: str = config.get('root', '')
        resolved = f"{root.rstrip('/')}/{key}" if root else key
        if self._should_gzip(key):
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
        if self._should_gzip(key):
            data = gzip.decompress(data)
        return data

    def write_key(self, key: str, data: bytes) -> None:
        if self._should_gzip(key):
            data = gzip.compress(data)
        return self._adapter().write_key(self._resolve_key(key), data)

    def delete_key(self, key: str) -> None:
        return self._adapter().delete_key(self._resolve_key(key))

    def list_keys(self, prefix: str | None = None) -> list[str]:
        return [k for k, _ in self.list_keys_sized(prefix)]

    def list_keys_sized(self, prefix: str | None = None) -> list[tuple[str, int]]:
        """Return [(canonical_key, size)] under ``prefix``.

        Sizes are taken from the listing response in a single backend call
        (no per-key HEAD). The root prefix and ``.gz`` suffix are stripped so
        the returned keys round-trip through ``parse_chunk_key`` /
        ``build_chunk_key``.
        """
        config: dict = self.config or {}
        root: str = config.get('root', '')
        search = f"{root.rstrip('/')}/{prefix}" if prefix else root
        if not search:
            return []
        pairs = self._adapter().list_keys_sized(search)
        result: list[tuple[str, int]] = []
        for k, size in pairs:
            if root:
                k = k[len(root) + 1:] if k.startswith(root + '/') else k
            if k.endswith('.gz'):
                k = k[:-3]
            result.append((k, size))
        return result

    def get_size(self, key: str) -> int:
        return self._adapter().get_size(self._resolve_key(key))
