# -*- coding: utf-8 -*-

from odoo.addons.component.core import AbstractComponent


class DatasetStorageBase(AbstractComponent):
    _name = "dataset.storage.base"
    _collection = "dataset.storage"

    def key_exist(self, key: str) -> bool:
        raise NotImplementedError

    def read_key(self, key: str) -> bytes:
        raise NotImplementedError

    def write_key(self, key: str, data: bytes) -> None:
        raise NotImplementedError

    def delete_key(self, key: str) -> None:
        raise NotImplementedError
