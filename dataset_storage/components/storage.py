# -*- coding: utf-8 -*-

from odoo.addons.component.core import AbstractComponent


class DatasetStorageBase(AbstractComponent):
    _name = "dataset.storage.base"
    _collection = "dataset.storage"

    def init_storage(self, dataset_id):
        raise NotImplementedError

    def key_exist(self, dataset_id, key):
        raise NotImplementedError

    def add_binary(self, dataset_id, key, data):
        raise NotImplementedError

    def get_binary(self, dataset_id, key):
        raise NotImplementedError

    def list(self, dataset_id):
        raise NotImplementedError

    def delete(self, dataset_id, key):
        raise NotImplementedError

    def get_md5(self, dataset_id, key):
        raise NotImplementedError