# -*- coding: utf-8 -*-

import io

import polars as pl

from odoo import models, fields, _


_READERS = {
    'csv': pl.read_csv,
    'parquet': pl.read_parquet,
}

_PREVIEW_ROWS = 50


class DataChunk(models.Model):
    _inherit = 'dataset.data_chunk'

    record_count = fields.Integer(
        string='Record Count',
        readonly=True,
        help="Number of rows in the chunk's payload, refreshed by to_dataframe().",
    )
    html_preview = fields.Html(
        string='Preview',
        compute='_compute_html_preview',
        sanitize=False,
    )

    def _compute_html_preview(self):
        for record in self:
            try:
                df = record.to_dataframe()
            except Exception as e:  # noqa: BLE001
                record.html_preview = f"<p><em>Preview error:</em> {e}</p>"
                continue
            if df is None:
                record.html_preview = "<p><em>No data.</em></p>"
                continue
            record.html_preview = df.head(_PREVIEW_ROWS)._repr_html_()

    def action_preview(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Preview: %s") % (self.key or self.display_name),
            'res_model': 'dataset.data_chunk',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('dataset_dataframe.view_data_chunk_preview').id,
            'target': 'new',
        }

    def to_dataframe(self) -> pl.DataFrame | None:
        self.ensure_one()
        dataset = self.dataset_id
        chunk_type = dataset.chunk_type
        reader = _READERS.get(chunk_type)
        if reader is None:
            raise ValueError(
                f"to_dataframe only supports {sorted(_READERS)}, got {chunk_type!r}"
            )
        storage = dataset.storage_id
        if not storage:
            raise ValueError("no storage configured on dataset")
        if not self.key:
            raise ValueError("chunk has no key")
        if not storage.key_exist(self.key):
            if self.record_count != 0:
                self.record_count = 0
            return None
        data = storage.read_key(self.key)
        if not data:
            if self.record_count != 0:
                self.record_count = 0
            return None
        df = reader(io.BytesIO(data))
        metadata = self.metadata or {}
        existing = set(df.columns)
        extra = [
            pl.lit(metadata.get(k)).alias(k)
            for k in (dataset.key_fields or [])
            if k not in existing and k in metadata
        ]
        if extra:
            df = df.with_columns(extra)
        if self.record_count != df.height:
            self.record_count = df.height
        return df
