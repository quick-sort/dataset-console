# -*- coding: utf-8 -*-

import odoo
from odoo import api
from odoo.tests import common


class TestDataset(common.TransactionCase):

    def test_source_create(self):
        source = self.env['dataset.source'].create({
            'name': 'Hugging Face',
            'code': 'hf',
            'url': 'https://huggingface.co/datasets',
            'description': 'Datasets hosted on the Hugging Face Hub.',
        })
        self.assertEqual(source.name, 'Hugging Face')
        self.assertEqual(source.code, 'hf')

    def test_source_unique_code(self):
        self.env['dataset.source'].create({
            'name': 'Hugging Face',
            'code': 'hf',
        })
        with self.assertRaises(odoo.osv.expression.RedirectError):
            self.env['dataset.source'].create({
                'name': 'Hugging Face 2',
                'code': 'hf',
            })

    def test_package_create(self):
        parent = self.env['dataset.package'].create({
            'name': 'NLP',
            'code': 'nlp',
            'description': 'Natural Language Processing datasets.',
        })
        child = self.env['dataset.package'].create({
            'name': 'Text Classification',
            'code': 'classification',
            'parent_id': parent.id,
        })
        self.assertEqual(child.parent_id, parent)
        self.assertEqual(child.parent_path, f'{parent.id}/')

    def test_dataset_create(self):
        source = self.env['dataset.source'].create({
            'name': 'Hugging Face',
            'code': 'hf',
        })
        dataset = self.env['dataset'].create({
            'name': 'IMDB Reviews',
            'code': 'imdb',
            'source_id': source.id,
            'chunk_type': 'parquet',
            'key_fields': ['split', 'shard'],
        })
        self.assertEqual(dataset.source_id, source)
        self.assertEqual(dataset.chunk_type, 'parquet')

    def test_build_chunk_key(self):
        source = self.env['dataset.source'].create({
            'name': 'Hugging Face',
            'code': 'hf',
        })
        dataset = self.env['dataset'].create({
            'name': 'IMDB Reviews',
            'code': 'imdb',
            'source_id': source.id,
            'chunk_type': 'parquet',
            'key_fields': ['split', 'shard'],
        })
        key = dataset.build_chunk_key({'split': 'train', 'shard': '0001'})
        self.assertEqual(key, 'hf/imdb/train/0001.parquet')

    def test_build_chunk_key_no_metadata(self):
        source = self.env['dataset.source'].create({
            'name': 'Hugging Face',
            'code': 'hf',
        })
        dataset = self.env['dataset'].create({
            'name': 'Titanic',
            'code': 'titanic',
            'source_id': source.id,
            'chunk_type': 'csv',
        })
        key = dataset.build_chunk_key({})
        self.assertEqual(key, 'hf/titanic.csv')

    def test_parse_chunk_key(self):
        result = self.env['dataset'].parse_chunk_key('hf/imdb/train/0001.parquet', ['split', 'shard'])
        self.assertEqual(result['source_code'], 'hf')
        self.assertEqual(result['dataset_code'], 'imdb')
        self.assertEqual(result['chunk_type'], 'parquet')
        self.assertEqual(result['metadata'], {'split': 'train', 'shard': '0001'})

    def test_parse_chunk_key_no_metadata(self):
        result = self.env['dataset'].parse_chunk_key('titanic.csv', None)
        self.assertEqual(result['source_code'], 'titanic')
        self.assertEqual(result['dataset_code'], 'titanic')
        self.assertEqual(result['chunk_type'], 'csv')
        self.assertEqual(result['metadata'], {})

    def test_chunk_key_unique_per_source(self):
        source1 = self.env['dataset.source'].create({
            'name': 'Source 1',
            'code': 'src1',
        })
        source2 = self.env['dataset.source'].create({
            'name': 'Source 2',
            'code': 'src2',
        })
        self.env['dataset'].create({
            'name': 'IMDB',
            'code': 'imdb',
            'source_id': source1.id,
            'chunk_type': 'parquet',
        })
        with self.assertRaises(odoo.osv.expression.RedirectError):
            self.env['dataset'].create({
                'name': 'IMDB',
                'code': 'imdb',
                'source_id': source2.id,
                'chunk_type': 'parquet',
            })

    def test_data_chunk_create(self):
        source = self.env['dataset.source'].create({
            'name': 'Hugging Face',
            'code': 'hf',
        })
        dataset = self.env['dataset'].create({
            'name': 'IMDB Reviews',
            'code': 'imdb',
            'source_id': source.id,
            'chunk_type': 'parquet',
            'key_fields': ['split'],
        })
        chunk = self.env['dataset.data_chunk'].create({
            'dataset_id': dataset.id,
            'metadata': {'split': 'train'},
        })
        self.assertEqual(chunk.key, 'hf/imdb/train.parquet')

    def test_total_chunks_computed(self):
        source = self.env['dataset.source'].create({
            'name': 'Hugging Face',
            'code': 'hf',
        })
        dataset = self.env['dataset'].create({
            'name': 'IMDB Reviews',
            'code': 'imdb',
            'source_id': source.id,
            'chunk_type': 'parquet',
            'key_fields': ['split'],
        })
        self.env['dataset.data_chunk'].create([
            {'dataset_id': dataset.id, 'metadata': {'split': 'train'}},
            {'dataset_id': dataset.id, 'metadata': {'split': 'test'}},
        ])
        self.assertEqual(dataset.total_chunks, 2)

    def test_fill_rate_with_manifest(self):
        source = self.env['dataset.source'].create({
            'name': 'Hugging Face',
            'code': 'hf',
        })
        dataset = self.env['dataset'].create({
            'name': 'IMDB Reviews',
            'code': 'imdb',
            'source_id': source.id,
            'chunk_type': 'parquet',
        })
        manifest = self.env['dataset.manifest'].create({
            'name': 'imdb-v1',
            'values': [{'i': i} for i in range(4)],
        })
        dataset.manifest_id = manifest
        self.env['dataset.data_chunk'].create([
            {'dataset_id': dataset.id},
            {'dataset_id': dataset.id},
            {'dataset_id': dataset.id},
        ])
        self.assertEqual(dataset.fill_rate, 0.75)