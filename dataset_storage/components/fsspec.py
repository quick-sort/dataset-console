# -*- coding: utf-8 -*-

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

    def key_exist(self, key: str) -> bool:
        return self._fs().exists(key)

    def read_key(self, key: str) -> bytes:
        with self._fs().open(key, 'rb') as f:
            return f.read()

    def write_key(self, key: str, data: bytes) -> None:
        fs = self._fs()
        parent = key.rsplit('/', 1)[0]
        if parent and parent != key:
            fs.makedirs(parent, exist_ok=True)
        with fs.open(key, 'wb') as f:
            f.write(data)

    def delete_key(self, key: str) -> None:
        fs = self._fs()
        if fs.exists(key):
            fs.rm(key)

    def list_keys_sized(self, prefix: str | None = None) -> list[tuple[str, int]]:
        """Return [(path, size)] in a single backend call.

        Uses ``fs.find(prefix, detail=True)`` so the size for each entry is
        read from the listing response (S3 ``ListObjectsV2`` already includes
        it) — no per-key HEAD request.
        """
        fs = self._fs()
        if not prefix:
            return []
        info = fs.find(prefix, detail=True)
        out: list[tuple[str, int]] = []
        for path, meta in info.items():
            if path == prefix:
                continue
            if isinstance(meta, dict):
                if meta.get('type') == 'directory':
                    continue
                size = int(meta.get('size') or 0)
            else:
                size = 0
            out.append((path.rstrip('/'), size))
        return out

    def get_size(self, key: str) -> int:
        info = self._fs().info(key)
        return info.get('size', 0)
