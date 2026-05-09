# -*- coding: utf-8 -*-

from odoo import models, fields
import json


class Storage(models.Model):
    _name = 'dataset.storage'
    _description = 'Dataset Storage'
    _order = 'id desc'
    _inherit = ['collection.base']

    name = fields.Char(string='Name', required=True)
    backend_type = fields.Selection(
        selection=[],
    )
    config = fields.Json(string='Configuration', help='Connection configuration as JSON')
    is_default = fields.Boolean(string='Default', default=False)

    _name_unique = models.Constraint(
        'unique(name)',
        "Storage name must be unique!",
    )

    def init_storage(self, dataset_id):
        with self.work_on(self._name) as work:
            adapter = work.component(usage=self.backend_type)
            return adapter.init_storage(dataset_id)

    def key_exist(self, dataset_id, key):
        if isinstance(key, str):
            key = json.loads(key)
        with self.work_on(self._name) as work:
            adapter = work.component(usage=self.backend_type)
            return adapter.key_exist(dataset_id, key)

    def add_binary(self, dataset_id, key, binary):
        if isinstance(key, str):
            key = json.loads(key)
        with self.work_on(self._name) as work:
            adapter = work.component(usage=self.backend_type)
            return adapter.add_binary(dataset_id, key, binary)

    def get_md5(self, dataset_id, key):
        if isinstance(key, str):
            key = json.loads(key)
        with self.work_on(self._name) as work:
            adapter = work.component(usage=self.backend_type)
            return adapter.get_md5(dataset_id, key)

    def get_binary(self, dataset_id, key):
        if isinstance(key, str):
            key = json.loads(key)
        with self.work_on(self._name) as work:
            adapter = work.component(usage=self.backend_type)
            return adapter.get_binary(dataset_id, key)

    def list(self, dataset_id):
        with self.work_on(self._name) as work:
            adapter = work.component(usage=self.backend_type)
            return adapter.list(dataset_id)

    def delete(self, dataset_id, key):
        if isinstance(key, str):
            key = json.loads(key)
        with self.work_on(self._name) as work:
            adapter = work.component(usage=self.backend_type)
            return adapter.delete(dataset_id, key)