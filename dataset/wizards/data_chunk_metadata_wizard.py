# -*- coding: utf-8 -*-

import json

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DataChunkMetadataWizard(models.TransientModel):
    _name = 'dataset.data_chunk.metadata_wizard'
    _description = 'Edit chunk metadata as JSON'

    chunk_id = fields.Many2one(
        'dataset.data_chunk', string='Chunk', required=True, ondelete='cascade',
    )
    metadata_text = fields.Text(string='Metadata (JSON)')

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        chunk_id = defaults.get('chunk_id') or self.env.context.get('default_chunk_id')
        if chunk_id:
            chunk = self.env['dataset.data_chunk'].browse(chunk_id)
            defaults.setdefault('chunk_id', chunk.id)
            value = chunk.metadata or {}
            # Demo XML may have stored metadata as a JSON string instead of a
            # parsed dict (Odoo's XML loader does not auto-parse Json fields);
            # parse it back here so the editor shows real JSON, not its repr.
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass
            defaults.setdefault(
                'metadata_text',
                json.dumps(value, indent=2, ensure_ascii=False),
            )
        return defaults

    def action_save(self):
        self.ensure_one()
        text = (self.metadata_text or '').strip()
        if not text:
            self.chunk_id.metadata = False
            return {'type': 'ir.actions.act_window_close'}
        try:
            self.chunk_id.metadata = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValidationError(self.env._("Invalid JSON: %s", e))
        return {'type': 'ir.actions.act_window_close'}
