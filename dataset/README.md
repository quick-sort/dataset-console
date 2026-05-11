# Dataset Management

Odoo 19 addon for cataloging and managing datasets used in AI/ML training and
evaluation. Provides a hierarchical taxonomy of sources and packages, dataset
records, and individually addressable data chunks with auto-computed keys and
per-chunk lifecycle state.

This addon is purely a metadata catalog — it does **not** read, write or
otherwise touch dataset payloads. Physical storage (local file, S3, GCS,
Azure, …) is handled by the separate
[`dataset_storage`](../dataset_storage) addon and its backend-specific
extensions.

---

## Installation

1. Clone this repository into your Odoo addons path.
2. Update the apps list and install **Dataset Management** from the Apps menu.

The addon depends only on `base`. To enable storage backends, also install
`dataset_storage` (which itself depends on the OCA `component` addon bundled in
this repo).

## Models

| Model                | Description                                                                          |
| -------------------- | ------------------------------------------------------------------------------------ |
| `dataset.source`     | External data provider (name, code, URL, description).                               |
| `dataset.package`    | Hierarchical grouping of datasets (`_parent_store = True`).                          |
| `dataset`            | A dataset belonging to a source and (optionally) a package and a manifest.           |
| `dataset.data_chunk` | A single addressable chunk inside a dataset, with metadata and size.                 |
| `dataset.manifest`   | A typed descriptor pointing at a dataset (extensible via `type`; currently `dataset`).|

### `dataset.source`

| Field         | Type | Notes                                |
| ------------- | ---- | ------------------------------------ |
| `name`        | Char | Required, unique.                    |
| `code`        | Char | Required, unique. Used in chunk keys.|
| `url`         | Char | Optional source URL.                 |
| `description` | Text | Free-form description.               |

### `dataset.package`

A folder-like grouping. Packages can be nested via `parent_id`; Odoo maintains
`parent_path` automatically (`_parent_store = True`), enabling hierarchical
search-panel navigation.

| Field         | Type     | Notes                                          |
| ------------- | -------- | ---------------------------------------------- |
| `name`        | Char     | Required, unique within the same parent.       |
| `code`        | Char     | Required, unique within the same parent.       |
| `description` | Text     | Free-form description.                         |
| `parent_id`   | Many2one | Parent package (self-reference).               |
| `child_ids`   | One2many | Inverse of `parent_id`.                        |

### `dataset`

| Field             | Type          | Notes                                                                                                       |
| ----------------- | ------------- | ----------------------------------------------------------------------------------------------------------- |
| `name`            | Char          | Required. Unique per source.                                                                                |
| `code`            | Char          | Required. Unique per source. Used in chunk keys.                                                            |
| `source_id`       | Many2one      | Required. Tracked.                                                                                          |
| `package_id`      | Many2one      | Optional, indexed.                                                                                          |
| `manifest_id`     | Many2one      | Optional link to a `dataset.manifest`. `ondelete='set null'`.                                               |
| `description`     | Text          | Free-form description.                                                                                      |
| `chunk_data_type` | Selection     | `pdf`, `csv`, `docx`, `xlsx`, `json`, `jsonl`, `parquet`. Default `csv`. Tracked.                           |
| `key_fields`      | Json          | List of metadata keys used to compose each chunk's key. Tracked.                                            |
| `chunk_ids`       | One2many      | Linked chunks.                                                                                              |
| `total_chunks`    | Integer       | Computed and stored. `len(chunk_ids)`. Depends on `chunk_ids`.                                              |
| `fill_rate`       | Float         | Computed and stored. `total_chunks / manifest_id.total_chunks`, or 0 if no manifest / expected is 0. Depends on `total_chunks` and `manifest_id.total_chunks`. Displayed with `widget="percentage"`. |

### `dataset.manifest`

A descriptor record that can point at a dataset. The `type` selection is the
extension point — today it only declares `dataset`, but additional types can
be added later (with a corresponding typed reference field). A dataset
references its current manifest via `dataset.manifest_id`, and the manifest
itself records its target via `dataset_id`.

| Field          | Type      | Notes                                                                                       |
| -------------- | --------- | ------------------------------------------------------------------------------------------- |
| `name`         | Char      | Required, **unique**.                                                                       |
| `description`  | Text      | Free-form description.                                                                      |
| `type`         | Selection | Required. Currently only `dataset`. Default `dataset`.                                      |
| `dataset_id`   | Many2one  | Linked dataset. `ondelete='set null'`. Required when `type='dataset'`.                      |
| `total_chunks` | Integer   | **Expected** chunk count declared by this manifest. User-entered, default 0. Used as the denominator of `dataset.fill_rate`. |

The form view hides/requires `dataset_id` based on `type` so adding more
manifest types later is purely additive.

### `dataset.data_chunk`

| Field         | Type     | Notes                                                                       |
| ------------- | -------- | --------------------------------------------------------------------------- |
| `key`         | Char     | Computed (editable, stored, indexed, tracked). See *Chunk key format* below.|
| `dataset_id`  | Many2one | Required, indexed, `ondelete='cascade'`.                                    |
| `description` | Text     | Free-form description.                                                      |
| `size`        | Integer  | Size in bytes.                                                              |
| `metadata`    | Json     | Per-chunk metadata. Source of values for the computed key. Tracked.         |
| `state`       | Selection| `missing` (default) → `exists` → `checked`. Per-chunk lifecycle indicator. Tracked. |
| `raw_data`    | Binary   | Raw chunk payload. `attachment=True` → stored via `ir.attachment` (filestore), not in the chunk row. |
| `raw_data_filename` | Char | Original filename, used by the form's download widget (`filename="..."`). |

#### Chunk key format

`key` is computed by `_compute_key`:

* If the dataset has `key_fields`:
  `{source.code}/{dataset.code}/{metadata[k1]}/{metadata[k2]}/….{chunk_data_type}`
* Otherwise:
  `{source.code}/{dataset.code}.{chunk_data_type}`

The key is unique per dataset and is editable after computation, so manual
overrides are persisted.

## Views

* **Datasets** — kanban (default), list, and form views, plus a search view
  with a side **search panel** that filters by:
  * `source_id` (multi-select checkboxes)
  * `package_id` (single-select hierarchical tree, leveraging `_parent_store`)
* Group-by: source, package, data type.
* List + form views for **Sources**, **Packages**, and **Data Chunks**
  (chunks have their own search view with state filters and group-by on
  dataset/state).

All views use Odoo 19 syntax (`<list>`, kanban `t-name="card"` API).

## Menus

```
Dataset
├── Datasets
├── Chunks
└── Settings
    ├── Sources
    ├── Packages
    └── Manifests
```

The companion `dataset_storage` addon adds a **Storages** entry under
`Dataset`.

## Security

* `Dataset Manager` group declared in `security/dataset_manager.xml` for future
  manager-level permissions.
* `security/ir.model.access.csv` grants full CRUD on the five dataset models
  (`dataset`, `dataset.source`, `dataset.package`, `dataset.data_chunk`,
  `dataset.manifest`) to `base.group_user`. Tighten as needed for production.

## Constraints

| Model                | SQL constraint                       | Message                                            |
| -------------------- | ------------------------------------ | -------------------------------------------------- |
| `dataset.source`     | `unique(code)`                       | Source code must be unique                         |
| `dataset.source`     | `unique(name)`                       | Source name must be unique                         |
| `dataset.manifest`   | `unique(name)`                       | Manifest name must be unique                       |
| `dataset.package`    | `unique(name, parent_id)`            | Package name must be unique within same parent     |
| `dataset.package`    | `unique(code, parent_id)`            | Package code must be unique within same parent     |
| `dataset`            | `unique(code, source_id)`            | Dataset code must be unique per source             |
| `dataset`            | `unique(name, source_id)`            | Dataset name must be unique per source             |
| `dataset.data_chunk` | `unique(key, dataset_id)`            | Chunk key must be unique within dataset            |

Constraints are declared with the Odoo 18+ `models.Constraint(...)`
class-attribute syntax.

## Usage example

```python
source = env['dataset.source'].create({
    'name': 'Wikipedia',
    'code': 'wiki',
    'url': 'https://en.wikipedia.org',
})

pkg = env['dataset.package'].create({'name': 'NLP', 'code': 'nlp'})

ds = env['dataset'].create({
    'name': 'Wiki sentences EN',
    'code': 'wiki_en_sent',
    'source_id': source.id,
    'package_id': pkg.id,
    'chunk_data_type': 'jsonl',
    'key_fields': ['lang', 'shard'],
})

chunk = env['dataset.data_chunk'].create({
    'dataset_id': ds.id,
    'metadata': {'lang': 'en', 'shard': '0001'},
    'size': 1048576,
    'state': 'exists',
})
# chunk.key == 'wiki/wiki_en_sent/en/0001.jsonl'
```

## License

LGPL-3.
