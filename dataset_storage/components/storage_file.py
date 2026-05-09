# -*- coding: utf-8 -*-

import os

from odoo.addons.component.core import Component
import hashlib
import logging

logger = logging.getLogger(__name__)


class FileDatasetStorage(Component):
    _name = "dataset.storage.file"
    _inherit = "dataset.storage.base"
    _usage = "file"

    def init_storage(self, dataset_id):
        pass

    def _base_path(self, dataset_id):
        return os.path.join(dataset_id.source_id.code, dataset_id.code)

    def _key2path(self, dataset_id, key):
        file_path = self._base_path(dataset_id)
        keys = dataset_id.get_fields(key=True)
        for i in keys:
            if i in key:
                file_path = os.path.join(file_path, str(key[i]))
        return file_path + '.csv'

    def key_exist(self, dataset_id, key):
        file_path = self._key2path(dataset_id, key)
        return os.path.exists(file_path)

    def add_binary(self, dataset_id, key, data):
        file_path = self._key2path(dataset_id, key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(data)

    def get_md5(self, dataset_id, key):
        file_path = self._key2path(dataset_id, key)
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'rb') as f:
            data = f.read()
        md5 = hashlib.md5()
        md5.update(data)
        return md5.hexdigest()

    def get_binary(self, dataset_id, key):
        file_path = self._key2path(dataset_id, key)
        with open(file_path, 'rb') as f:
            return f.read()

    def list(self, dataset_id):
        key_names = dataset_id.get_fields(key=True)
        key_depth = len(key_names)
        if key_depth == 0:
            if self.key_exist(dataset_id, {}):
                return [{}]
            return []
        return []

    def delete(self, dataset_id, key):
        file_path = self._key2path(dataset_id, key)
        if os.path.exists(file_path):
            os.remove(file_path)