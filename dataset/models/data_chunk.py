# -*- coding: utf-8 -*-

from odoo import models, fields


class DataChunk(models.Model):
    _name = 'dataset.data_chunk'
    _description = 'Dataset Data Chunk'
    _order = 'id desc'

    key = fields.Char(
        string='Key',
        compute='_compute_key',
        store=True,
        readonly=False,
        tracking=True,
        index=True,
    )
    dataset_id = fields.Many2one('dataset', string='Dataset', required=True, index=True, ondelete='cascade')
    description = fields.Text(string='Description')
    size = fields.Integer(string='Size in bytes')
    metadata = fields.Json(string='Metadata', tracking=True)
    raw_data = fields.Binary(string='Raw Data', attachment=True)
    raw_data_filename = fields.Char(string='Raw Data Filename')
    state = fields.Selection([
        ('missing', 'Missing'),
        ('exists', 'Exists'),
        ('checked', 'Checked'),
    ], string='State', default='missing', tracking=True)

    _key_dataset_unique = models.Constraint(
        'unique(key, dataset_id)',
        "Chunk key must be unique within dataset!",
    )

    def action_edit_metadata(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Edit Metadata"),
            'res_model': 'dataset.data_chunk.metadata_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_chunk_id': self.id},
        }

    def _compute_key(self):
        for record in self:
            if not record.dataset_id:
                record.key = False
                continue
            source_code = record.dataset_id.source_id.code or ''
            dataset_code = record.dataset_id.code or ''
            data_type = record.dataset_id.chunk_data_type or ''
            key_fields = record.dataset_id.key_fields or []

            if key_fields:
                meta_values = [str(record.metadata.get(k, '')) for k in key_fields]
                key = f"{source_code}/{dataset_code}/{'/'.join(meta_values)}.{data_type}"
            else:
                key = f"{source_code}/{dataset_code}.{data_type}"
            record.key = key