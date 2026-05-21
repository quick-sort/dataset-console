# -*- coding: utf-8 -*-

import logging
from typing import TYPE_CHECKING

from odoo import models, fields, api, _
from odoo.exceptions import UserError

if TYPE_CHECKING:
    pass

_logger = logging.getLogger(__name__)

BATCH_SIZE = 1000


class Dataset(models.Model):
    _inherit = 'dataset'

    storage_id = fields.Many2one(
        'dataset.storage',
        string='Storage',
        ondelete='restrict',
        default=lambda self: self._get_default_storage(),
    )

    @api.model
    def _default_storage_id(self):
        """Return the default file storage, creating one if needed."""
        Storage = self.env['dataset.storage']
        storage = Storage.search([('backend_type', '=', 'fsspec')], limit=1)
        if not storage:
            storage = Storage.create({
                'name': 'file',
                'backend_type': 'fsspec',
                'config': {'protocol': 'file', 'root': '/var/lib/datasets'},
            })
        return storage.id

    @api.model
    def _get_default_storage(self):
        """Return default storage by XML external ID, creating one if needed."""
        try:
            return self.env.ref('dataset_storage.default_storage').id
        except Exception:
            return self._default_storage_id()
    size = fields.Float(
        string='Size (GB)',
        compute='_compute_size',
        store=True,
        readonly=True,
        digits=(16, 3),
    )

    @api.depends('chunk_ids.size')
    def _compute_size(self):
        for record in self:
            total_bytes = sum(float(s) for s in record.chunk_ids.mapped('size'))
            record.size = total_bytes / (1024 * 1024 * 1024) if total_bytes else 0.0

    def action_scan_chunks(self):
        """List all keys, split into batches of 1000, dispatch child jobs
        for creating new chunks and updating existing chunks."""
        self.ensure_one()
        if not self.storage_id:
            raise UserError(_("No storage configured for this dataset."))
        self.with_delay(
            description=_("Scan chunks: %s") % self.display_name,
        ).scan_chunks()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Scan started"),
                'message': _("Scanning %s in the background. Watch Queue Jobs for progress.")
                           % self.display_name,
                'type': 'success',
                'sticky': False,
            },
        }

    def scan_chunks(self) -> int:
        """List all keys from storage, split into batches of 1000,
        dispatch child jobs for create/update."""
        self.ensure_one()
        if not self.storage_id:
            raise ValueError("no storage configured")

        prefix = self._scan_prefix()
        storage_keys = self.storage_id.list_keys_sized(prefix)

        # Existing keys from DB
        self.env.cr.execute(
            "SELECT key, size FROM dataset_data_chunk "
            "WHERE dataset_id = %s AND key IS NOT NULL",
            (self.id,),
        )
        existing = {row[0]: row[1] for row in self.env.cr.fetchall()}

        # 分类
        new_keys = []       # storage 有，数据库没有
        missing_keys = []   # 数据库有，storage 没有
        size_changed = []   # size 有变化

        for key, size in storage_keys:
            if key in existing:
                if existing[key] != size:
                    size_changed.append((key, size))
                del existing[key]
            else:
                new_keys.append((key, size))

        # 剩余的 key 只在数据库中存在，storage 已删除
        missing_keys = list(existing.keys())

        # 分发任务
        for i in range(0, len(new_keys), BATCH_SIZE):
            batch = new_keys[i:i + BATCH_SIZE]
            self.with_delay(
                description=_("Scan: create %d chunks") % len(batch),
            )._scan_create_batch(batch)

        for i in range(0, len(size_changed), BATCH_SIZE):
            batch = size_changed[i:i + BATCH_SIZE]
            self.with_delay(
                description=_("Scan: update %d chunks") % len(batch),
            )._scan_update_batch(batch)

        _logger.info(
            "Scan dispatched for dataset %s: %d new, %d size-changed, %d missing",
            self.display_name, len(new_keys), len(size_changed), len(missing_keys),
        )

        # 标记 missing
        if missing_keys:
            self.env.cr.execute(
                "UPDATE dataset_data_chunk SET state = 'missing' "
                "WHERE dataset_id = %s AND key = ANY(%s)",
                (self.id, missing_keys),
            )

        return len(new_keys) + len(size_changed) + len(missing_keys)

    def _scan_create_batch(self, batch: list[tuple[str, int]]) -> int:
        """Create a batch of new chunks."""
        Dataset = self.env['dataset']
        DataChunk = self.env['dataset.data_chunk']
        key_fields = self.key_fields or []

        to_create = []
        for key, size in batch:
            try:
                parsed = Dataset.parse_chunk_key(key, key_fields)
            except ValueError as e:
                _logger.warning("Skipping unparseable key %r: %s", key, e)
                continue
            to_create.append({
                'dataset_id': self.id,
                'metadata': parsed.get('metadata'),
                'state': 'exists',
                'size': size,
                'raw_data_filename': key.rsplit('/', 1)[-1],
            })

        if to_create:
            DataChunk.create(to_create)

        return len(to_create)

    def _scan_update_batch(self, batch: list[tuple[str, int]]) -> int:
        """Update size for existing chunks that have changed."""
        DataChunk = self.env['dataset.data_chunk']
        updated = 0
        for key, size in batch:
            chunk = DataChunk.search([('key', '=', key), ('dataset_id', '=', self.id)], limit=1)
            if chunk:
                chunk.write({'size': size})
                updated += 1
        return updated

    def _scan_prefix(self) -> str:
        source_code = self.source_id.code
        dataset_code = self.code
        prefix = f"{source_code}/{dataset_code}"
        prefix += "/" if self.key_fields else "."
        return prefix