# -*- coding: utf-8 -*-

from unittest import mock

from odoo.tests import common


class TestStorage(common.TransactionCase):

    def test_storage_create(self):
        storage = self.env['dataset.storage'].create({
            'name': 'Local',
            'backend_type': 'fsspec',
            'config': {'protocol': 'file', 'root': '/tmp/datasets'},
        })
        self.assertEqual(storage.name, 'Local')

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

    def test_resolve_key_parquet_skips_gzip(self):
        storage = self.env['dataset.storage'].create({
            'name': 'Local',
            'backend_type': 'fsspec',
            'config': {'protocol': 'file', 'root': '/var/lib/datasets'},
        })
        key = storage._resolve_key('hf/imdb/train.parquet')
        self.assertEqual(key, '/var/lib/datasets/hf/imdb/train.parquet')

    def test_resolve_key_json_gets_gzip(self):
        storage = self.env['dataset.storage'].create({
            'name': 'Local',
            'backend_type': 'fsspec',
            'config': {'protocol': 'file', 'root': '/var/lib/datasets'},
        })
        key = storage._resolve_key('hf/squad/train.json')
        self.assertEqual(key, '/var/lib/datasets/hf/squad/train.json.gz')

    def test_resolve_key_no_root(self):
        storage = self.env['dataset.storage'].create({
            'name': 'Local',
            'backend_type': 'fsspec',
            'config': {},
        })
        self.assertEqual(storage._resolve_key('hf/imdb/train.parquet'), 'hf/imdb/train.parquet')
        self.assertEqual(storage._resolve_key('hf/squad/train.json'), 'hf/squad/train.json.gz')

    def test_list_keys_strips_root_and_gz(self):
        """list_keys delegates to list_keys_sized; both strip root + .gz."""
        storage = self.env['dataset.storage'].create({
            'name': 'Local',
            'backend_type': 'fsspec',
            'config': {'protocol': 'file', 'root': 'ai-datasets'},
        })
        with mock.patch.object(storage, '_adapter') as mock_adapter:
            mock_comp = mock.MagicMock()
            mock_comp.list_keys_sized.return_value = [
                ('ai-datasets/hf/squad/train.json.gz', 1024),
                ('ai-datasets/hkex/stock_quote/2026-01-02.parquet', 4096),
            ]
            mock_adapter.return_value = mock_comp

            sized = storage.list_keys_sized('')
            self.assertEqual(sized, [
                ('hf/squad/train.json', 1024),
                ('hkex/stock_quote/2026-01-02.parquet', 4096),
            ])
            self.assertEqual(
                storage.list_keys(''),
                ['hf/squad/train.json', 'hkex/stock_quote/2026-01-02.parquet'],
            )


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
        })
        dataset = self.env['dataset'].create({
            'name': 'Test Dataset',
            'code': 'test_ds',
            'source_id': source.id,
            'chunk_type': 'parquet',
            'storage_id': storage.id,
        })
        chunk = self.env['dataset.data_chunk'].create({
            'dataset_id': dataset.id,
            'key': 'test/test_ds/train.parquet',
        })

        with mock.patch.object(storage, '_adapter') as mock_adapter:
            mock_comp = mock.MagicMock()
            mock_comp.key_exist.return_value = True
            mock_comp.read_key.return_value = b'PAR1...'
            mock_comp.get_size.return_value = 7
            mock_adapter.return_value = mock_comp

            raw = chunk.raw_data
            self.assertEqual(raw, b'PAR1...')

    def test_chunk_raw_data_inverse(self):
        source = self.env['dataset.source'].create({
            'name': 'Test',
            'code': 'test',
        })
        storage = self.env['dataset.storage'].create({
            'name': 'Test Storage',
            'backend_type': 'fsspec',
            'config': {'protocol': 'memory'},
        })
        dataset = self.env['dataset'].create({
            'name': 'Test Dataset',
            'code': 'test_ds',
            'source_id': source.id,
            'chunk_type': 'parquet',
            'storage_id': storage.id,
        })
        chunk = self.env['dataset.data_chunk'].create({
            'dataset_id': dataset.id,
            'key': 'test/test_ds/train.parquet',
        })

        with mock.patch.object(storage, '_adapter') as mock_adapter:
            mock_comp = mock.MagicMock()
            mock_adapter.return_value = mock_comp

            chunk.raw_data = b'PAR1...'

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
        })
        dataset = self.env['dataset'].create({
            'name': 'Test Dataset',
            'code': 'test_ds',
            'source_id': source.id,
            'chunk_type': 'parquet',
            'storage_id': storage.id,
        })
        self.assertEqual(dataset.storage_id, storage)

    def test_dataset_size_sums_chunk_size_without_storage_io(self):
        """_compute_size now sums chunk.size — no get_size() round trips."""
        source = self.env['dataset.source'].create({
            'name': 'Test',
            'code': 'test',
        })
        storage = self.env['dataset.storage'].create({
            'name': 'Local',
            'backend_type': 'fsspec',
            'config': {'protocol': 'memory'},
        })
        dataset = self.env['dataset'].create({
            'name': 'Test Dataset',
            'code': 'test_ds',
            'source_id': source.id,
            'chunk_type': 'parquet',
            'storage_id': storage.id,
        })
        with mock.patch.object(storage, '_adapter') as mock_adapter:
            mock_comp = mock.MagicMock()
            mock_adapter.return_value = mock_comp
            self.env['dataset.data_chunk'].create([
                {'dataset_id': dataset.id, 'key': 'test/test_ds/train.parquet', 'size': 100},
                {'dataset_id': dataset.id, 'key': 'test/test_ds/test.parquet', 'size': 200},
            ])

            self.assertEqual(dataset.size, 300)
            # Storage adapter must NOT be hit during _compute_size.
            mock_comp.get_size.assert_not_called()


class TestScanChunks(common.TransactionCase):
    """Scan flow: storage already has files, no chunk records in odoo yet."""

    def _setup_hkex(self):
        source = self.env['dataset.source'].create({
            'name': 'HKEX', 'code': 'hkex',
        })
        storage = self.env['dataset.storage'].create({
            'name': 'S3 Bucket',
            'backend_type': 'fsspec',
            'config': {'protocol': 's3', 'root': 'ai-datasets'},
        })
        dataset = self.env['dataset'].create({
            'name': 'Stock Quote',
            'code': 'stock_quote',
            'source_id': source.id,
            'chunk_type': 'parquet',
            'key_fields': ['date'],
            'storage_id': storage.id,
        })
        return storage, dataset

    def test_scan_populates_empty_dataset(self):
        storage, dataset = self._setup_hkex()

        with mock.patch.object(storage, '_adapter') as mock_adapter:
            mock_comp = mock.MagicMock()
            # Sizes piggyback on the listing — no separate get_size call.
            mock_comp.list_keys_sized.return_value = [
                ('ai-datasets/hkex/stock_quote/2026-01-02.parquet', 62914560),
                ('ai-datasets/hkex/stock_quote/2026-01-05.parquet', 61865984),
                ('ai-datasets/hkex/stock_quote/2026-05-14.parquet', 63438848),
            ]
            mock_adapter.return_value = mock_comp

            created = dataset.scan_chunks()

            # Single network pass. get_size must NOT be called per key.
            mock_comp.list_keys_sized.assert_called_once()
            mock_comp.get_size.assert_not_called()

        self.assertEqual(created, 3)
        self.assertEqual(len(dataset.chunk_ids), 3)
        chunks = dataset.chunk_ids.sorted(key=lambda c: c.key)
        self.assertEqual(
            [c.key for c in chunks],
            [
                'hkex/stock_quote/2026-01-02.parquet',
                'hkex/stock_quote/2026-01-05.parquet',
                'hkex/stock_quote/2026-05-14.parquet',
            ],
        )
        self.assertEqual(chunks[0].metadata, {'date': '2026-01-02'})
        self.assertEqual(chunks[0].state, 'exists')
        self.assertEqual(chunks[0].size, 62914560)
        self.assertEqual(chunks[2].size, 63438848)

    def test_scan_is_idempotent(self):
        storage, dataset = self._setup_hkex()
        listing = [
            ('ai-datasets/hkex/stock_quote/2026-01-02.parquet', 10),
            ('ai-datasets/hkex/stock_quote/2026-01-05.parquet', 20),
        ]

        with mock.patch.object(storage, '_adapter') as mock_adapter:
            mock_comp = mock.MagicMock()
            mock_comp.list_keys_sized.return_value = listing
            mock_adapter.return_value = mock_comp

            self.assertEqual(dataset.scan_chunks(), 2)
            self.assertEqual(dataset.scan_chunks(), 0)
            self.assertEqual(len(dataset.chunk_ids), 2)

    def test_scan_does_not_refresh_existing_chunks(self):
        """Pre-existing chunks: state, size, metadata are NOT touched even
        when the storage listing reports a different size."""
        storage, dataset = self._setup_hkex()

        self.env['dataset.data_chunk'].create([
            {'dataset_id': dataset.id, 'metadata': {'date': '2026-01-02'},
             'state': 'checked', 'size': 999},
            {'dataset_id': dataset.id, 'metadata': {'date': '2026-05-15'},
             'state': 'missing', 'size': 0},
        ])

        with mock.patch.object(storage, '_adapter') as mock_adapter:
            mock_comp = mock.MagicMock()
            # Note: storage reports a *different* size for 01-02 — must be ignored.
            mock_comp.list_keys_sized.return_value = [
                ('ai-datasets/hkex/stock_quote/2026-01-02.parquet', 12345),
                ('ai-datasets/hkex/stock_quote/2026-01-05.parquet', 50),
            ]
            mock_adapter.return_value = mock_comp

            created = dataset.scan_chunks()

        self.assertEqual(created, 1)
        by_date = {c.metadata['date']: c for c in dataset.chunk_ids}
        # Pre-existing chunk untouched: original state + original size.
        self.assertEqual(by_date['2026-01-02'].state, 'checked')
        self.assertEqual(by_date['2026-01-02'].size, 999)
        # Pre-seeded missing chunk for absent key: unchanged.
        self.assertEqual(by_date['2026-05-15'].state, 'missing')
        # Newly scanned chunk: state + size from listing.
        self.assertEqual(by_date['2026-01-05'].state, 'exists')
        self.assertEqual(by_date['2026-01-05'].size, 50)

    def test_scan_strips_gz_suffix_for_gzipped_chunk_types(self):
        source = self.env['dataset.source'].create({'name': 'HF', 'code': 'hf'})
        storage = self.env['dataset.storage'].create({
            'name': 'S3 JSON',
            'backend_type': 'fsspec',
            'config': {'protocol': 's3', 'root': 'ai-datasets'},
        })
        dataset = self.env['dataset'].create({
            'name': 'SQuAD', 'code': 'squad',
            'source_id': source.id,
            'chunk_type': 'json',
            'key_fields': ['split'],
            'storage_id': storage.id,
        })

        with mock.patch.object(storage, '_adapter') as mock_adapter:
            mock_comp = mock.MagicMock()
            mock_comp.list_keys_sized.return_value = [
                ('ai-datasets/hf/squad/train.json.gz', 1024),
                ('ai-datasets/hf/squad/dev.json.gz', 512),
            ]
            mock_adapter.return_value = mock_comp

            self.assertEqual(dataset.scan_chunks(), 2)

        chunks = dataset.chunk_ids.sorted(key=lambda c: c.key)
        self.assertEqual([c.key for c in chunks],
                         ['hf/squad/dev.json', 'hf/squad/train.json'])
        # Sizes from the listing (gzipped on-disk size) preserved.
        self.assertEqual(chunks[0].size, 512)
        self.assertEqual(chunks[1].size, 1024)

    def test_scan_skips_unparseable_keys(self):
        """One key with the wrong number of path segments should be skipped
        (logged warning), the rest of the batch must succeed."""
        storage, dataset = self._setup_hkex()  # key_fields=['date']

        with mock.patch.object(storage, '_adapter') as mock_adapter:
            mock_comp = mock.MagicMock()
            mock_comp.list_keys_sized.return_value = [
                ('ai-datasets/hkex/stock_quote/2026-01-02.parquet', 10),
                # Extra path segment — parse_chunk_key length-mismatches.
                ('ai-datasets/hkex/stock_quote/2026-01-05/extra.parquet', 20),
                ('ai-datasets/hkex/stock_quote/2026-01-06.parquet', 30),
            ]
            mock_adapter.return_value = mock_comp

            created = dataset.scan_chunks()

        self.assertEqual(created, 2)  # bad one skipped, good two created
        keys = sorted(c.key for c in dataset.chunk_ids)
        self.assertEqual(keys, [
            'hkex/stock_quote/2026-01-02.parquet',
            'hkex/stock_quote/2026-01-06.parquet',
        ])

    def test_scan_batches_commits(self):
        """Verify cr.commit fires once per batch — the durability mechanism
        for long-running scans on huge buckets."""
        storage, dataset = self._setup_hkex()

        # 25 keys, batch_size=10 → 2 full batches + 1 partial = 3 commits.
        listing = [
            (f'ai-datasets/hkex/stock_quote/2026-01-{i:02d}.parquet', i * 100)
            for i in range(1, 26)
        ]

        with mock.patch.object(storage, '_adapter') as mock_adapter, \
             mock.patch.object(dataset, '_scan_commit') as mock_commit:
            mock_comp = mock.MagicMock()
            mock_comp.list_keys_sized.return_value = listing
            mock_adapter.return_value = mock_comp

            created = dataset.scan_chunks(batch_size=10)

        self.assertEqual(created, 25)
        self.assertEqual(mock_commit.call_count, 3)

    def test_scan_max_batches_caps_work(self):
        """max_batches lets a cron checkpoint cap work per call so long
        scans split into multiple resumable runs."""
        storage, dataset = self._setup_hkex()

        listing = [
            (f'ai-datasets/hkex/stock_quote/2026-01-{i:02d}.parquet', i)
            for i in range(1, 26)
        ]
        with mock.patch.object(storage, '_adapter') as mock_adapter:
            mock_comp = mock.MagicMock()
            mock_comp.list_keys_sized.return_value = listing
            mock_adapter.return_value = mock_comp

            created = dataset.scan_chunks(batch_size=10, max_batches=2)

        # Two full batches inserted, third batch (of 5) skipped.
        self.assertEqual(created, 20)
        self.assertEqual(len(dataset.chunk_ids), 20)

    def test_action_scan_chunks_dispatches_via_queue_job(self):
        """The button method delays via with_delay and returns a UI notification."""
        _storage, dataset = self._setup_hkex()

        with mock.patch.object(type(dataset), 'with_delay') as mock_with_delay:
            mock_with_delay.return_value = mock.MagicMock()

            result = dataset.action_scan_chunks()

            mock_with_delay.assert_called_once()
            mock_with_delay.return_value.scan_chunks.assert_called_once_with()

        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')

    def test_action_scan_chunks_requires_storage(self):
        from odoo.exceptions import UserError
        source = self.env['dataset.source'].create({'name': 'X', 'code': 'x'})
        dataset = self.env['dataset'].create({
            'name': 'No Storage', 'code': 'nostorage',
            'source_id': source.id, 'chunk_type': 'parquet',
        })
        with self.assertRaises(UserError):
            dataset.action_scan_chunks()
