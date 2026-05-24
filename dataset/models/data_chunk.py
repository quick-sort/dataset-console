# -*- coding: utf-8 -*-

import base64
import csv
import io

from odoo import models, fields, api
from odoo.tools.misc import human_size

try:
    import pyarrow.parquet as pq
    _PYARROW_AVAILABLE = True
except ImportError:
    _PYARROW_AVAILABLE = False


class DataChunk(models.Model):
    _name = 'dataset.data_chunk'
    _description = 'Dataset Data Chunk'
    _order = 'id desc'
    _rec_name = 'key'

    key = fields.Char(
        string='Key',
        compute='_compute_key',
        store=True,
        readonly=False,
        index=True,
    )
    dataset_id = fields.Many2one('dataset', string='Dataset', required=True, index=True, ondelete='restrict')
    description = fields.Text(string='Description')
    size = fields.Integer(string='Size in bytes')
    display_size = fields.Char(compute='_compute_display_size', string='Size')

    metadata = fields.Json(string='Metadata')
    raw_data = fields.Binary(string='Raw Data', attachment=True)
    raw_data_filename = fields.Char(string='Raw Data Filename')
    state = fields.Selection([
        ('missing', 'Missing'),
        ('exists', 'Exists'),
        ('checked', 'Checked'),
    ], string='State', default='missing', compute='_compute_state', store=True)

    _key_dataset_unique = models.Constraint(
        'unique(key, dataset_id)',
        "Chunk key must be unique within dataset!",
    )

    @api.depends('size')
    def _compute_state(self):
        for record in self:
            record.state = 'exists' if record.size else 'missing'

    @api.depends('size')
    def _compute_display_size(self):
        for record in self:
            record.display_size = human_size(record.size) or ''

    @api.depends('dataset_id', 'metadata')
    def _compute_key(self):
        for record in self:
            if not record.dataset_id:
                record.key = False
                continue
            record.key = record.dataset_id.build_chunk_key(record.metadata)

    def _get_preview_type(self) -> str:
        """Detect preview type from dataset's chunk_type."""
        chunk_type: str | None = self.dataset_id.chunk_type if self.dataset_id else None
        type_map = {
            'pdf': 'pdf',
            'csv': 'table',
            'docx': 'binary',
            'xlsx': 'binary',
            'pptx': 'binary',
            'json': 'text',
            'jsonl': 'text',
            'parquet': 'table',
            'txt': 'text',
            'md': 'text',
            'image': 'binary',
        }
        return type_map.get(chunk_type or '', 'binary')

    def action_preview(self):
        """Preview the chunk file - loads data and opens preview view."""
        self.ensure_one()
        preview_type = self._get_preview_type()
        # For table types, load data and pass to table_preview_wizard
        if preview_type == 'table':
            storage = self.dataset_id.storage_id if self.dataset_id else None
            if storage and self.key:
                data = storage.read_key(self.key)
                if data:
                    wizard = self.env['dataset.table_preview_wizard'].create({
                        'chunk_id': self.id,
                        'raw_data': base64.b64encode(data),
                    })
                    return {
                        'type': 'ir.actions.act_window',
                        'name': self.display_name,
                        'res_model': 'dataset.table_preview_wizard',
                        'res_id': wizard.id,
                        'target': 'new',
                        'view_mode': 'form',
                    }
            raise ValueError("Cannot load preview data")
        # For non-table types, open form view (triggering compute is fine - user clicked preview)
        view_xml_id = f'dataset.view_data_chunk_preview_{preview_type}'
        return {
            'type': 'ir.actions.act_window',
            'name': self.display_name,
            'res_model': 'dataset.data_chunk',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref(view_xml_id).id,
            'target': 'new',
        }

    def action_open_file_wizard(self):
        """Open wizard for file download."""
        return {
            'type': 'ir.actions.act_window',
            'name': self.display_name,
            'res_model': 'dataset.data_chunk',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('dataset.view_data_chunk_download').id,
            'target': 'new',
        }