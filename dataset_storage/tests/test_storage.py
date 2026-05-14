# -*- coding: utf-8 -*-

import io
from unittest import mock

from odoo.tests import common


class TestStorage(common.TransactionCase):

    def test_storage_create(self):
        storage = self.env['dataset.storage'].create({
            'name': 'Local',
            'backend_type': 'fsspec',
            'config': {'protocol': 'file', 'root': '/tmp/datasets'},
            'gzip': True,
        })
        self.assertEqual(storage.name, 'Local')
        self.assertTrue(storage.gzip)

    def test_storage_unique_name(self):
        self.env['dataset.storage'].create({
            'name': 'Local',
            'backend_type': 'fsspec',
        })
        with self.assertRaises(Exception):
            self.env['dataset.storage'].create({
                'name': 'Local',
                'backend_type': 'fsspec',
            })

    def test_resolve_key_without_gzip(self):
        storage = self.env['dataset.storage'].create({
            'name': 'Local',
            'backend_type': 'fsspec',
            'config': {'protocol': 'file', 'root': '/var/lib/datasets'},
            'gzip': False,
        })
        key = storage._resolve_key('hf/imdb/train.parquet')
        self.assertEqual(key, '/var/lib/datasets/hf/imdb/train.parquet')

    def test_resolve_key_with_gzip(self):
        storage = self.env['dataset.storage'].create({
            'name': 'Local',
            'backend_type': 'fsspec',
            'config': {'protocol': 'file', 'root': '/var/lib/datasets'},
            'gzip': True,
        })
        key = storage._resolve_key('hf/imdb/train.parquet')
        self.assertEqual(key, '/var/lib/datasets/hf/imdb/train.parquet.gz')

    def test_resolve_key_no_root(self):
        storage = self.env['dataset.storage'].create({
            'name': 'Local',
            'backend_type': 'fsspec',
            'config': {},
            'gzip': True,
        })
        key = storage._resolve_key('hf/imdb/train.parquet')
        self.assertEqual(key, 'hf/imdb/train.parquet.gz')


class TestDataChunk(common.TransactionCase):

    def test_chunk_raw_data_computed(self):
        source = self.env['dataset.source'].create({
            'name': 'Test',
            'code': 'test',
        })
        storage = self.env['dataset.storage'].create({
            'name': 'Test Storage',
            'backend_type': 'fsspec',
            'config': {'protocol': 'memory'},
            'gzip': False,
        })
        dataset = self.env['dataset'].create({
            'name': 'Test Dataset',
            'code': 'test_ds',
            'source_id': source.id,
            'chunk_type': 'json',
            'storage_id': storage.id,
        })
        chunk = self.env['dataset.data_chunk'].create({
            'dataset_id': dataset.id,
            'key': 'test/test_ds/train.json',
        })

        with mock.patch.object(storage, '_adapter') as mock_adapter:
            mock_comp = mock.MagicMock()
            mock_comp.key_exist.return_value = True
            mock_comp.read_key.return_value = b'{"text": "hello"}'
            mock_comp.get_size.return_value = 18
            mock_adapter.return_value = mock_comp

            raw = chunk.raw_data
            self.assertEqual(raw, b'{"text": "hello"}')

    def test_chunk_raw_data_inverse(self):
        source = self.env['dataset.source'].create({
            'name': 'Test',
            'code': 'test',
        })
        storage = self.env['dataset.storage'].create({
            'name': 'Test Storage',
            'backend_type': 'fsspec',
            'config': {'protocol': 'memory'},
            'gzip': False,
        })
        dataset = self.env['dataset'].create({
            'name': 'Test Dataset',
            'code': 'test_ds',
            'source_id': source.id,
            'chunk_type': 'json',
            'storage_id': storage.id,
        })
        chunk = self.env['dataset.data_chunk'].create({
            'dataset_id': dataset.id,
            'key': 'test/test_ds/train.json',
        })

        with mock.patch.object(storage, '_adapter') as mock_adapter:
            mock_comp = mock.MagicMock()
            mock_adapter.return_value = mock_comp

            chunk.raw_data = b'{"text": "world"}'

            mock_comp.write_key.assert_called_once()


class TestDatasetStorage(common.TransactionCase):

    def test_dataset_storage_link(self):
        source = self.env['dataset.source'].create({
            'name': 'Test',
            'code': 'test',
        })
        storage = self.env['dataset.storage'].create({
            'name': 'Local',
            'backend_type': 'fsspec',
            'config': {'protocol': 'memory'},
            'gzip': False,
        })
        dataset = self.env['dataset'].create({
            'name': 'Test Dataset',
            'code': 'test_ds',
            'source_id': source.id,
            'chunk_type': 'json',
            'storage_id': storage.id,
        })
        self.assertEqual(dataset.storage_id, storage)

    def test_dataset_size_computed(self):
        source = self.env['dataset.source'].create({
            'name': 'Test',
            'code': 'test',
        })
        storage = self.env['dataset.storage'].create({
            'name': 'Local',
            'backend_type': 'fsspec',
            'config': {'protocol': 'memory'},
            'gzip': False,
        })
        dataset = self.env['dataset'].create({
            'name': 'Test Dataset',
            'code': 'test_ds',
            'source_id': source.id,
            'chunk_type': 'json',
            'storage_id': storage.id,
        })
        self.env['dataset.data_chunk'].create([
            {'dataset_id': dataset.id, 'key': 'test/test_ds/train.json'},
            {'dataset_id': dataset.id, 'key': 'test/test_ds/test.json'},
        ])

        with mock.patch.object(storage, '_adapter') as mock_adapter:
            mock_comp = mock.MagicMock()
            mock_comp.get_size.side_effect = [100, 200]
            mock_adapter.return_value = mock_comp

            dataset._compute_size()
            self.assertEqual(dataset.size, 300)