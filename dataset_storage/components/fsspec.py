# -*- coding: utf-8 -*-

import gzip

import fsspec

from odoo.addons.component.core import Component


class FsspecDatasetStorage(Component):
    _name = "dataset.storage.fsspec"
    _inherit = "dataset.storage.base"
    _usage = "fsspec"

    def _fs(self) -> fsspec.AbstractFileSystem:
        config: dict = self.collection.config or {}
        protocol: str = config.get('protocol', 'file')
        options: dict = config.get('storage_options') or {}
        return fsspec.filesystem(protocol, **options)

    def _path(self, key: str) -> str:
        config: dict = self.collection.config or {}
        root: str = config.get('root', '')
        path = f"{root.rstrip('/')}/{key}" if root else key
        if self.collection.gzip:
            path += '.gzip'
        return path

    def key_exist(self, key: str) -> bool:
        return self._fs().exists(self._path(key))

    def read_key(self, key: str) -> bytes:
        with self._fs().open(self._path(key), 'rb') as f:
            data: bytes = f.read()
        if self.collection.gzip:
            data = gzip.decompress(data)
        return data

    def write_key(self, key: str, data: bytes) -> None:
        path = self._path(key)
        fs = self._fs()
        parent = path.rsplit('/', 1)[0]
        if parent and parent != path:
            fs.makedirs(parent, exist_ok=True)
        if self.collection.gzip:
            data = gzip.compress(data)
        with fs.open(path, 'wb') as f:
            f.write(data)

    def delete_key(self, key: str) -> None:
        path = self._path(key)
        fs = self._fs()
        if fs.exists(path):
            fs.rm(path)
