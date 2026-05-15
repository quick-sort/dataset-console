# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import config

_logger = logging.getLogger(__name__)


class Dataset(models.Model):
    _inherit = 'dataset'

    SCAN_BATCH_SIZE = 1000

    storage_id = fields.Many2one('dataset.storage', string='Storage', ondelete='restrict')
    size = fields.Integer(
        string='Size in bytes',
        compute='_compute_size',
        store=True,
        readonly=True,
    )

    @api.depends('chunk_ids.size')
    def _compute_size(self):
        for record in self:
            record.size = sum(record.chunk_ids.mapped('size'))

    def action_scan_chunks(self):
        """Schedule a background scan via queue_job. Returns immediately.

        First-time scans against large buckets can list millions of keys and
        run for hours; running the worker inline would hit Odoo's
        ``--limit-time-cpu`` / ``--limit-time-real`` worker limits.
        """
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

    def scan_chunks(self, batch_size: int | None = None, max_batches: int | None = None) -> int:
        """Sync worker. Run inline only for small datasets; otherwise use
        ``action_scan_chunks`` to dispatch via queue_job.

        - One backend listing call returns ``(key, size)`` pairs (no per-key HEAD).
        - Existing chunk keys come from a SQL query, not the ORM relationship,
          so re-scans of large datasets don't materialize every record.
        - Pre-existing chunks are LEFT UNTOUCHED — sizes are not refreshed.
        - Inserts are batched; ``cr.commit`` runs between batches so a
          long-running scan persists progress (and can survive worker restart
          when re-launched). ``max_batches`` lets a cron checkpoint cap work
          per call.
        - Bad keys are logged and skipped, not raised — one rogue file does
          not abort a multi-hour scan.
        """
        self.ensure_one()
        if not self.storage_id:
            raise ValueError("no storage configured")
        if batch_size is None:
            batch_size = self.SCAN_BATCH_SIZE

        prefix = self._scan_prefix()
        sized = self.storage_id.list_keys_sized(prefix)

        # Existing keys via SQL — avoids loading every chunk record into the ORM.
        self.env.cr.execute(
            "SELECT key FROM dataset_data_chunk "
            "WHERE dataset_id = %s AND key IS NOT NULL",
            (self.id,),
        )
        existing = {row[0] for row in self.env.cr.fetchall()}

        new_pairs = [(k, s) for k, s in sized if k not in existing]
        if not new_pairs:
            return 0

        key_fields = self.key_fields or []
        Dataset = self.env['dataset']
        DataChunk = self.env['dataset.data_chunk']

        total_created = 0
        batch_count = 0
        batch: list[dict] = []

        for key, size in new_pairs:
            try:
                parsed = Dataset.parse_chunk_key(key, key_fields)
            except ValueError as e:
                _logger.warning(
                    "Skipping unparseable key %r in dataset %s: %s",
                    key, self.display_name, e,
                )
                continue
            batch.append({
                'dataset_id': self.id,
                'metadata': parsed.get('metadata'),
                'state': 'exists',
                'size': size,
            })
            if len(batch) >= batch_size:
                DataChunk.create(batch)
                total_created += len(batch)
                self._scan_commit()
                batch = []
                batch_count += 1
                if max_batches is not None and batch_count >= max_batches:
                    return total_created

        if batch:
            DataChunk.create(batch)
            total_created += len(batch)
            self._scan_commit()

        return total_created

    def _scan_prefix(self) -> str:
        source_code = self.source_id.code
        dataset_code = self.code
        prefix = f"{source_code}/{dataset_code}"
        prefix += "/" if self.key_fields else "."
        return prefix

    def _scan_commit(self) -> None:
        """Commit between scan batches so progress persists. Skipped under
        the test runner so TransactionCase rollback still works."""
        if not config['test_enable']:
            self.env.cr.commit()
