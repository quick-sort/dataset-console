# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


OPERATORS = {
    '=': lambda a, b: a == b,
    '==': lambda a, b: a == b,
    '!=': lambda a, b: a != b,
    '>': lambda a, b: a > b,
    '<': lambda a, b: a < b,
    '>=': lambda a, b: a >= b,
    '<=': lambda a, b: a <= b,
    'in': lambda a, b: a in b if b else False,
    'not in': lambda a, b: a not in b if b else False,
    'like': lambda a, b: b in str(a) if a and b else False,
}


def _match_domain(row: dict, domain) -> bool:
    """递归解析 Odoo domain 表达式并匹配 row"""
    if not domain:
        return True

    if isinstance(domain, str):
        domain = safe_eval(domain)

    if not domain:
        return True

    op = domain[0] if domain else '&'
    if op not in ('&', '|'):
        return all(_match_single_condition(row, item) for item in domain)

    if op == '&':
        for i in range(1, len(domain)):
            item = domain[i]
            if item in ('&', '|'):
                continue
            if not _match_single_condition(row, item):
                return False
        return True
    else:  # OR
        for i in range(1, len(domain)):
            item = domain[i]
            if item in ('&', '|'):
                continue
            if _match_single_condition(row, item):
                return True
        return False


def _match_single_condition(row: dict, condition) -> bool:
    """匹配单个条件 [field, op, value]"""
    if not condition or len(condition) < 3:
        return True

    field, operator, value = condition[0], condition[1], condition[2]
    row_value = row.get(field)

    # 处理 '!' 前缀的操作符
    if isinstance(operator, str) and operator.startswith('!'):
        operator = operator[1:]
        negated = True
    else:
        negated = False

    # 处理 'not' 前缀
    if isinstance(operator, str) and operator.startswith('not '):
        operator = operator[4:]
        negated = True

    # 列表/元组格式的 domain (支持 and/or 嵌套)
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        # 递归处理嵌套 domain
        if value[0] in ('&', '|'):
            result = _match_domain(row, value)
        else:
            # 多个独立条件，用 AND 连接
            result = all(_match_single_condition(row, c) for c in value)
        return not result if negated else result

    # 比较
    op_func = OPERATORS.get(operator)
    if op_func:
        result = op_func(row_value, value)
    else:
        result = row_value == value

    return not result if negated else result


class Dataset(models.Model):
    _name = 'dataset'
    _description = 'Dataset'
    _order = 'id desc'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    source_id = fields.Many2one('dataset.source', string='Source', required=True)
    package_id = fields.Many2one('dataset.package', string='Package', index=True)
    manifest_id = fields.Many2one('dataset.manifest', string='Manifest', ondelete='set null')
    description = fields.Text(string='Description')
    chunk_type = fields.Selection([
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
        ('docx', 'Word'),
        ('xlsx', 'Excel'),
        ('pptx', 'PowerPoint'),
        ('json', 'JSON'),
        ('jsonl', 'JSONL'),
        ('parquet', 'Parquet'),
        ('txt', 'Text'),
        ('md', 'Markdown'),
        ('image', 'Image'),
    ], string='Chunk Type', default='csv')
    key_fields = fields.Json(string='Key Fields', default=[], help='List of metadata keys used as chunk keys')
    chunk_ids = fields.One2many('dataset.data_chunk', 'dataset_id', string='Chunks')
    filter_domain = fields.Char(
        string='Filter Domain',
        help="Odoo domain expression to filter manifest values, e.g. [('date', '=', '2024')]"
    )
    total_chunks = fields.Integer(
        string='Total Chunks',
        compute='_compute_total_chunks',
        store=True,
    )
    filtered_total_chunks = fields.Integer(
        string='Expected Chunks',
        compute='_compute_filtered_total_chunks',
        store=True,
        help="Number of values after applying filter_domain",
    )
    fill_rate = fields.Float(
        string='Fill Rate',
        compute='_compute_fill_rate',
        store=True,
        digits=(5, 4),
        help="Actual chunk count divided by the filtered expected chunk count. "
             "0 if no manifest is set or its expected count is 0.",
    )
    tag_ids = fields.Many2many(
        'dataset.tag',
        'dataset_tag_rel',
        'dataset_id',
        'tag_id',
        string='Tags',
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

    @classmethod
    def parse_chunk_key(cls, key: str, key_fields: list[str] | None = None) -> dict:
        if not key:
            raise ValueError("key cannot be empty")
        parts = key.rsplit('.', 1)
        if len(parts) != 2:
            raise ValueError(f"invalid key format: {key}")
        prefix, chunk_type = parts
        path_parts = prefix.split('/')
        if len(path_parts) < 2:
            raise ValueError(f"invalid key format: {key}")
        source_code, dataset_code = path_parts[0], path_parts[1]
        meta = {}
        expected_meta_count = len(path_parts) - 2
        if key_fields:
            if len(key_fields) != expected_meta_count:
                raise ValueError(
                    f"key_fields length mismatch: expected {expected_meta_count}, got {len(key_fields)}"
                )
            values = path_parts[2:]
            meta = dict(zip(key_fields, values))
        return {
            'source_code': source_code,
            'dataset_code': dataset_code,
            'chunk_type': chunk_type,
            'metadata': meta,
        }

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

    @api.depends('manifest_id', 'manifest_id.values', 'filter_domain')
    def _compute_filtered_total_chunks(self):
        for record in self:
            total = 0
            if record.manifest_id and record.manifest_id.values:
                values = record.manifest_id.values
                if record.filter_domain:
                    domain = safe_eval(record.filter_domain)
                    total = len([v for v in values if _match_domain(v, domain)])
                else:
                    total = len(values)
            record.filtered_total_chunks = total

    @api.depends('total_chunks', 'filtered_total_chunks')
    def _compute_fill_rate(self):
        for record in self:
            expected = record.filtered_total_chunks
            record.fill_rate = (record.total_chunks / expected) if expected else 0.0
