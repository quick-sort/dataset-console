# Dataset Storage

Odoo 19 addon providing the storage backend for the
[`dataset`](../dataset) addon. Adds a `dataset.storage` model that exposes a
small key/value interface (`key_exist`, `read_key`, `write_key`,
`delete_key`), backed by [`fsspec`](https://filesystem-spec.readthedocs.io/)
and pluggable via the OCA [`component`](../component) framework.

The dataset addon is purely a metadata catalog. This addon is what actually
reads/writes chunk payloads on disk, S3, GCS, Azure, HTTP, etc.

---

## Installation

1. Install the `dataset` and `component` addons (both bundled in this repo).
2. Install **Dataset Storage** from the Apps menu.
3. Install the `fsspec` Python package, plus any protocol-specific extras
   (`s3fs`, `gcsfs`, `adlfs`, …).

```bash
pip install fsspec s3fs gcsfs
```

The manifest declares `fsspec` as an external Python dependency.

## Models

### `dataset.storage`

A storage backend definition. Records are addressable by name and dispatch
all I/O to a component selected by `backend_type`.

| Field          | Type      | Notes                                                                       |
| -------------- | --------- | --------------------------------------------------------------------------- |
| `name`         | Char      | Required, **unique**.                                                       |
| `backend_type` | Selection | Required. Default `fsspec`. Component `_usage` to dispatch to.              |
| `config`       | Json      | Backend-specific connection config (see *fsspec config* below).             |
| `gzip`         | Boolean   | Default `True`. When on, payloads are gzip-compressed and `.gzip` is appended to the storage path. |

`dataset.storage` inherits `collection.base`, so the model is a *component
collection* — `self.work_on(self._name)` yields a working environment in
which `work.component(usage=…)` resolves the right backend component.

#### Storage interface

The model exposes four methods. Each delegates to the component selected by
`backend_type`:

```python
storage.key_exist(key: str) -> bool
storage.read_key(key: str) -> bytes
storage.write_key(key: str, data: bytes) -> None
storage.delete_key(key: str) -> None
```

`key` is the chunk key produced by `dataset.build_chunk_key(metadata)` (see
the dataset addon's README).

### Extensions to `dataset`

| Field        | Type     | Notes                                                |
| ------------ | -------- | ---------------------------------------------------- |
| `storage_id` | Many2one | Optional link to a `dataset.storage`. `ondelete='restrict'`. |

### Extensions to `dataset.data_chunk`

| Field      | Type   | Notes                                                                |
| ---------- | ------ | -------------------------------------------------------------------- |
| `raw_data` | Binary | Overridden — `attachment=False`, `compute='_compute_raw_data'`, `inverse='_inverse_raw_data'`. The dataset addon stores `raw_data` as an `ir.attachment`; this addon re-binds it to a compute/inverse pair so reads/writes go through the dataset's storage backend instead of the filestore. |

> `_compute_raw_data` / `_inverse_raw_data` are stubs in this addon — wire
> them to `dataset.storage_id` / `key` according to your deployment.

## Components

```
dataset.storage.base   (AbstractComponent, _collection = "dataset.storage")
└── dataset.storage.fsspec   (Component, _usage = "fsspec")
```

### `dataset.storage.base`

Defines the abstract interface (`key_exist`, `read_key`, `write_key`,
`delete_key`). Backends inherit it and set `_usage` to the value used by
`storage.backend_type`.

### `dataset.storage.fsspec`

Default backend. Builds an `fsspec` filesystem from the storage's `config`.

| Key               | Notes                                                          |
| ----------------- | -------------------------------------------------------------- |
| `protocol`        | Any fsspec protocol (`file`, `s3`, `gcs`, `abfs`, `http`, …). Default `file`. |
| `root`            | Optional path prefix prepended to every key.                   |
| `storage_options` | Forwarded as `**kwargs` to `fsspec.filesystem(protocol, …)` (credentials, endpoint, region, …). |

Path resolution: `f"{root}/{key}"` (root-stripped trailing slash). When
`storage.gzip` is true, `.gzip` is appended to the resolved path and the
payload is gzip-compressed on write / decompressed on read.

#### Config examples

**Local file:**

```json
{
  "protocol": "file",
  "root": "/var/lib/datasets",
  "storage_options": {}
}
```

**S3:**

```json
{
  "protocol": "s3",
  "root": "my-bucket/datasets",
  "storage_options": {
    "key": "AKIAIOSFODNN7EXAMPLE",
    "secret": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "region": "us-east-1"
  }
}
```

The S3 protocol requires the `s3fs` package (`pip install s3fs`).

**GCS** (uses `gcsfs`):

```json
{
  "protocol": "gcs",
  "root": "my-bucket/datasets",
  "storage_options": {
    "token": "/path/to/credentials.json"
  }
}
```

#### Adding a backend

1. Subclass `Component` with `_inherit = "dataset.storage.base"` and a unique
   `_usage` (e.g., `"my_backend"`).
2. Implement `key_exist`, `read_key`, `write_key`, `delete_key`.
3. Add the `_usage` value to `dataset.storage.backend_type`'s selection
   (extend the field in your addon).

## Views & Menus

* Form / list view for `dataset.storage`.
* Adds a **Storages** menu under `Dataset → Settings` (sequence 15).

## Security

`security/ir.model.access.csv` grants:

* `dataset.storage.user` — read.
* `dataset.storage.manager` — full CRUD.

Group fields are blank — assign groups in your deployment.

## Constraints

| Model            | SQL constraint  | Message                       |
| ---------------- | --------------- | ----------------------------- |
| `dataset.storage`| `unique(name)`  | Storage name must be unique!  |

Plus: `dataset.data_chunk.dataset_id` is `ondelete='restrict'` (set by the
`dataset` addon) — datasets with chunks cannot be deleted.

## Usage example

```python
storage = env['dataset.storage'].create({
    'name': 'local',
    'backend_type': 'fsspec',
    'config': {'protocol': 'file', 'root': '/var/lib/datasets'},
    'gzip': True,
})

ds = env['dataset'].browse(dataset_id)
ds.storage_id = storage

key = ds.build_chunk_key({'lang': 'en', 'shard': '0001'})
storage.write_key(key, b'...payload...')
assert storage.key_exist(key)
data = storage.read_key(key)
storage.delete_key(key)
```

## License

LGPL-3.
