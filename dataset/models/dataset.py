# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Dataset(models.Model):
    _name = 'dataset'
    _description = 'Dataset'
    _order = 'id desc'

    name = fields.Char(string='Label', required=True)
    code = fields.Char(string='Code', required=True)
    source_id = fields.Many2one('dataset.source', string='Source', required=True, tracking=True)
    package_id = fields.Many2one('dataset.package', string='Package', index=True)
    manifest_id = fields.Many2one('dataset.manifest', string='Manifest', ondelete='set null')
    description = fields.Text(string='Description')
    chunk_type = fields.Selection([
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
        ('docx', 'Word'),
        ('xlsx', 'Excel'),
        ('json', 'JSON'),
        ('jsonl', 'JSONL'),
        ('parquet', 'Parquet'),
    ], string='Chunk Type', default='csv', tracking=True)
    key_fields = fields.Json(string='Key Fields', help='List of metadata keys used as chunk keys', tracking=True)
    chunk_ids = fields.One2many('dataset.data_chunk', 'dataset_id', string='Chunks')
    total_chunks = fields.Integer(
        string='Total Chunks',
        compute='_compute_total_chunks',
        store=True,
    )
    fill_rate = fields.Float(
        string='Fill Rate',
        compute='_compute_fill_rate',
        store=True,
        digits=(5, 4),
        help="Actual chunk count divided by the manifest's expected chunk count. "
             "0 if no manifest is set or its expected count is 0.",
    )

    _code_source_unique = models.Constraint(
        'unique(code, source_id)',
        "Dataset code must be unique per source!",
    )

    _name_source_unique = models.Constraint(
        'unique(name, source_id)',
        "Dataset name must be unique per source!",
    )

    def build_chunk_key(self, metadata: dict | None) -> str:
        self.ensure_one()
        source_code: str = self.source_id.code
        dataset_code: str = self.code
        data_type: str = self.chunk_type
        if not source_code or not dataset_code or not data_type:
            raise ValueError("source code, dataset code, and chunk data type are required to build a chunk key")
        key_fields: list[str] = self.key_fields or []
        metadata = metadata or {}
        if key_fields:
            meta_values: list[str] = [str(metadata.get(k, '')) for k in key_fields]
            return f"{source_code}/{dataset_code}/{'/'.join(meta_values)}.{data_type}"
        return f"{source_code}/{dataset_code}.{data_type}"

    def action_view_chunks(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('dataset.action_data_chunk')
        action['domain'] = [('dataset_id', '=', self.id)]
        action['context'] = {'default_dataset_id': self.id}
        return action

    @api.depends('chunk_ids')
    def _compute_total_chunks(self):
        for record in self:
            record.total_chunks = len(record.chunk_ids)

    @api.depends('total_chunks', 'manifest_id.total_chunks')
    def _compute_fill_rate(self):
        for record in self:
            expected = record.manifest_id.total_chunks
            record.fill_rate = (record.total_chunks / expected) if expected else 0.0