# -*- coding: utf-8 -*-

import polars as pl

from odoo import models


class Dataset(models.Model):
    _inherit = 'dataset'

    def to_dataframe(self) -> pl.DataFrame | None:
        self.ensure_one()
        frames = [df for df in (chunk.to_dataframe() for chunk in self.chunk_ids) if df is not None]
        if not frames:
            return None
        return pl.concat(frames, how='vertical_relaxed')
