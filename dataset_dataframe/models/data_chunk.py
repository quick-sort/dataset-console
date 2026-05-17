# -*- coding: utf-8 -*-

import base64
import io
import logging

import polars as pl

from odoo import models, fields

_logger = logging.getLogger(__name__)


_READERS = {
    'csv': pl.read_csv,
    'parquet': pl.read_parquet,
}


class DataChunk(models.Model):
    _inherit = 'dataset.data_chunk'

    record_count = fields.Integer(
        string='Record Count',
        readonly=True,
        help="Number of rows in the chunk's payload, refreshed by to_dataframe().",
    )

    def to_dataframe(self) -> pl.DataFrame | None:
        self.ensure_one()
        chunk_type = self.dataset_id.chunk_type
        reader = _READERS.get(chunk_type)
        if reader is None:
            return None
        if not self.raw_data:
            if self.record_count != 0:
                self.record_count = 0
            return None
        try:
            data = base64.b64decode(self.raw_data)
        except Exception:
            _logger.warning("Invalid raw_data for chunk %s", self.key)
            self.record_count = 0
            return None
        df = reader(io.BytesIO(data))
        metadata = self.metadata or {}
        existing = set(df.columns)
        extra = [
            pl.lit(metadata.get(k)).alias(k)
            for k in (self.dataset_id.key_fields or [])
            if k not in existing and k in metadata
        ]
        if extra:
            df = df.with_columns(extra)
        if self.record_count != df.height:
            self.record_count = df.height
        return df