# -*- coding: utf-8 -*-

import base64
import csv
import io

from odoo import models, fields, api
from odoo.tools.misc import html_escape as _esc

try:
    import pyarrow.parquet as pq
    _PYARROW_AVAILABLE = True
except ImportError:
    _PYARROW_AVAILABLE = False

_DEFAULT_PAGE_SIZE = 50

_PAGE_SIZE_SELECTION = [
    ('10', '10'),
    ('25', '25'),
    ('50', '50'),
    ('100', '100'),
]


class TablePreviewWizard(models.TransientModel):
    _name = 'dataset.table_preview_wizard'
    _description = 'Table Preview Wizard'

    chunk_id = fields.Many2one('dataset.data_chunk', string='Chunk', required=True)
    chunk_name = fields.Char(related='chunk_id.display_name', readonly=True, store=False)
    raw_data = fields.Binary(string='Raw Data', readonly=True)  # Set directly by wizard
    headers = fields.Text(string='Headers', readonly=True)
    total_rows = fields.Integer(string='Total Rows', readonly=True)
    total_pages = fields.Integer(string='Total Pages', readonly=True)
    page = fields.Integer(string='Page', default=1)
    page_size = fields.Selection(
        _PAGE_SIZE_SELECTION,
        string='Page Size',
        default=str(_DEFAULT_PAGE_SIZE),
        required=True,
    )
    page_label = fields.Char(compute='_compute_page_label', string='Page')
    table_html = fields.Html(string='Rows')

    @api.depends('page', 'total_pages')
    def _compute_page_label(self):
        for rec in self:
            total = rec.total_pages or 1
            rec.page_label = f"{rec.page} / {total}"

    def _load_table_data(self, chunk=None):
        if chunk is None:
            chunk = self.chunk_id
        # Check wizard's raw_data first, then chunk.raw_data
        data_bytes = self.raw_data if self.raw_data else (chunk.raw_data if chunk else None)
        if not data_bytes:
            return [], []
        if isinstance(data_bytes, str):
            data_bytes = data_bytes.encode('utf-8')
        data = base64.b64decode(data_bytes)
        chunk_type = chunk.dataset_id.chunk_type if chunk.dataset_id else None
        if chunk_type == 'csv':
            lines = data.decode('utf-8', errors='replace').splitlines()
            reader = csv.DictReader(lines)
            headers = reader.fieldnames or []
            rows = list(reader)
            return headers, rows
        elif chunk_type == 'parquet':
            if not _PYARROW_AVAILABLE:
                return [], []
            table = pq.read_table(io.BytesIO(data))
            df = table.to_pandas()
            return list(df.columns), df.to_dict('records')
        return [], []

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        chunk_id = self.env.context.get('default_chunk_id')
        if chunk_id:
            res['chunk_id'] = chunk_id
        return res

    @api.model
    def _total_pages(self, total, page_size):
        if total <= 0 or page_size <= 0:
            return 1
        return (total + page_size - 1) // page_size

    def _int_page_size(self):
        try:
            return int(self.page_size)
        except (ValueError, TypeError):
            return _DEFAULT_PAGE_SIZE

    @api.model
    def create(self, vals):
        wizard = super().create(vals)
        chunk = wizard.chunk_id
        if chunk and chunk.exists():
            headers, all_rows = self._load_table_data(chunk)
            total = len(all_rows)
            ps = wizard._int_page_size()
            wizard.write({
                'headers': ','.join(str(h) for h in headers) if isinstance(headers, list) else '',
                'total_rows': total,
                'total_pages': self._total_pages(total, ps),
                'table_html': self._build_html_table(headers, all_rows[:ps]),
            })
        return wizard

    def _build_html_table(self, headers, rows):
        if not headers:
            return ''
        th = ''.join(f'<th>{_esc(h)}</th>' for h in headers)
        trs = ''
        for row in rows:
            if isinstance(row, dict):
                cells = ''.join(f'<td>{_esc(row.get(h, ""))}</td>' for h in headers)
            else:
                cells = ''.join(f'<td>{_esc(c)}</td>' for c in row)
            trs += f'<tr>{cells}</tr>'
        return (
            '<table class="table table-striped table-sm" style="font-size:12px;">'
            f'<thead style="background-color: #f8f9fa;"><tr>{th}</tr></thead>'
            f'<tbody>{trs}</tbody>'
            '</table>'
        )

    def _reload_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.chunk_id.display_name,
            'res_id': self.id,
            'res_model': 'dataset.table_preview_wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.onchange('page_size')
    def _onchange_page_size(self):
        self.page = 1

    def action_prev(self):
        if self.page <= 1:
            return self._reload_wizard()
        self._write_page(self.page - 1)
        return self._reload_wizard()

    def action_next(self):
        if self.page >= self._total_pages(self.total_rows, self._int_page_size()):
            return self._reload_wizard()
        self._write_page(self.page + 1)
        return self._reload_wizard()

    def _write_page(self, page):
        headers, all_rows = self._load_table_data(self.chunk_id)
        total = len(all_rows)
        ps = self._int_page_size()
        start = (page - 1) * ps
        self.write({
            'page': page,
            'headers': ','.join(str(h) for h in headers) if isinstance(headers, list) else '',
            'total_rows': total,
            'total_pages': self._total_pages(total, ps),
            'table_html': self._build_html_table(headers, all_rows[start:start + ps]),
        })