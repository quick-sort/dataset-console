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

| Field              | Type      | Notes                                                                       |
| ------------------ | --------- | --------------------------------------------------------------------------- |
| `name`             | Char      | Required, **unique**.                                                       |
| `backend_type`     | Selection | Required. Default `fsspec`. Component `_usage` to dispatch to.              |
| `config`           | Json      | Backend-specific connection config (see *fsspec config* below).             |
| `gzip_chunk_types` | Json      | List of chunk-type extensions to gzip-wrap. Default `["csv", "json", "jsonl"]`. Parquet (and anything else not in the list) passes through untouched. Set to `[]` to disable gzip entirely for this storage. |

Gzip handling is decided per-key from the chunk type encoded in the key
suffix. Same storage record can therefore handle mixed chunk types with the
correct compression behavior for each.

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
| `size`       | Integer  | Computed and stored. Sum of `chunk_ids.size` (no storage I/O). Recomputes when any chunk's size changes. |

#### Scanning storage to back-fill the catalog

When payloads already exist in storage (e.g. an S3 prefix that's been
populated by an upstream pipeline) and you want odoo to learn about them:

**Recommended — async via the form button:**

The dataset form has a **Scan** stat button. Clicking it calls
`action_scan_chunks`, which dispatches `scan_chunks` to a `queue_job`
worker via `with_delay()` and returns immediately with a notification.
Watch progress in **Settings → Technical → Queue Jobs**.

This is the right path for any non-trivial bucket — first-time scans
against millions of keys can run for hours, well past Odoo's default
`--limit-time-cpu` / `--limit-time-real` worker limits.

**Synchronous, for small datasets or scripts:**

```python
ds = env.ref('dataset.dataset_hkex_quote')
created = ds.scan_chunks()   # returns count of NEW chunks
```

##### How scan works

1. Builds a listing prefix from `source.code` and `dataset.code`. With
   `key_fields`, the prefix ends in `/` (`hkex/stock_quote/`); without it,
   in `.` (`kaggle/titanic.`) — the no-`key_fields` form doesn't currently
   round-trip through `fsspec.find()` for single-file datasets.
2. Calls `storage.list_keys_sized(prefix)` — **one** backend call returning
   `(canonical_key, size)` pairs. Sizes piggyback on the listing response
   (`fs.find(detail=True)`, S3 `ListObjectsV2`); there is **no per-key
   HEAD request**. Root prefix and `.gz` suffix are stripped so the
   catalog key is always the canonical uncompressed form.
3. Loads existing keys via a single SQL `SELECT key FROM
   dataset_data_chunk WHERE dataset_id = %s` — does not materialize chunk
   records through the ORM, so re-scans of million-chunk datasets stay
   cheap.
4. Diffs the listing against existing keys. Pre-existing chunks are
   **left untouched** — no size refresh, no state flip, no metadata
   rewrite. This is deliberate: re-scanning a 10M-key dataset shouldn't
   issue 10M ORM writes just to confirm what we already know.
5. For each new key, `Dataset.parse_chunk_key(key, key_fields)` reverses
   `build_chunk_key`: positional path segments → metadata dict. A key that
   fails parsing (wrong number of segments) is **skipped with a warning**;
   it does not abort the batch.
6. New chunks are created in batches of `SCAN_BATCH_SIZE` (default 1000).
   `cr.commit()` runs between batches so a multi-hour scan persists
   progress. Skipped under the test runner so `TransactionCase` rollback
   still works.
7. Returns the count of newly created chunks.

```python
def scan_chunks(self,
                batch_size: int | None = None,
                max_batches: int | None = None) -> int
```

`max_batches` caps the number of batches processed in a single call —
useful for cron-driven incremental scans where each invocation should
cap its work and let the next tick pick up the rest.

##### What scan does NOT do

- It does not update or refresh existing chunks. A chunk that's already in
  the catalog stays as-is regardless of what `list_keys_sized` reports for
  its key.
- It does not delete. A chunk record whose key vanishes from storage
  remains in the catalog (deletion is a separate, explicit action).
- It does not currently stream the listing. `list_keys_sized` materializes
  the full result in memory; for buckets with truly massive object counts
  (tens of millions) you'd want a streaming variant on top of
  `fs.walk()` or a paginated S3 client. Out of scope today.

##### Typical S3 back-fill scenario

```python
# A new dataset record, no chunks yet; HKEX dropped 2026 daily quotes
# into s3://ai-datasets/hkex/stock_quote/2026-*.parquet overnight.
ds = env.ref('dataset.dataset_hkex_quote')
assert not ds.chunk_ids
ds.action_scan_chunks()   # returns immediately; job runs in background

# After the job completes:
# - one chunk per parquet file
# - metadata={'date': '2026-01-02'} etc.
# - state='exists'
# - size populated from the listing response (no HEAD requests)
# - dataset.size auto-recomputes as the sum of chunk sizes
```

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

Path resolution: `f"{root}/{key}"` (root-stripped trailing slash). If the
key's extension is in this storage's `gzip_chunk_types`, `.gz` is appended
to the resolved path and the payload is gzip-compressed on write /
decompressed on read. Other extensions (parquet by default) pass through
unchanged.

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
2. Implement `key_exist`, `read_key`, `write_key`, `delete_key`,
   `list_keys_sized` (the abstract `list_keys` defaults to a wrapper around
   `list_keys_sized` so you don't need to implement it separately).
3. Add the `_usage` value to `dataset.storage.backend_type`'s selection
   (extend the field in your addon).

## Scan architecture

The scan path (storage → catalog) was designed around four constraints:

| Constraint | Why it matters |
|---|---|
| First scans of production buckets can list **millions** of keys. | Naive per-key `HEAD` for size or naive ORM `chunk_ids` enumeration both blow up O(N). |
| Odoo workers have hard `--limit-time-cpu` / `--limit-time-real` ceilings. | Anything that runs inline behind a button risks getting killed mid-flight, leaving the catalog inconsistent. |
| Pre-existing chunks should not pay re-scan cost. | A 10M-key dataset shouldn't issue 10M ORM writes just to confirm what's already in the table. |
| One bad key shouldn't kill a multi-hour job. | Pipelines drop occasional malformed paths (`tmp/foo.bak`, double-extensions, etc.). |

### Component map

```
┌──────────────────────┐    click       ┌────────────────────────────┐
│ Dataset form button  │ ─────────────▶ │ Dataset.action_scan_chunks │
│ (oe_stat_button)     │                │   self.with_delay()        │
└──────────────────────┘                │     .scan_chunks()         │
                                        └─────────────┬──────────────┘
                                          schedules   │
                                                      ▼
                                        ┌─────────────────────────────┐
                                        │ queue.job row (state=pending) │
                                        └─────────────┬───────────────┘
                                          picked up   │
                                                      ▼
                                        ┌─────────────────────────────┐
                                        │ queue_job runner            │
                                        │ (server_wide_modules,       │
                                        │  channels = root:N)         │
                                        └─────────────┬───────────────┘
                                          executes    │
                                                      ▼
            ┌─────────────────────────────────────────────────────────┐
            │ Dataset.scan_chunks (worker)                            │
            │  1. storage.list_keys_sized(prefix)  ← single call      │
            │  2. SELECT key FROM dataset_data_chunk WHERE …          │
            │  3. diff → new_pairs                                    │
            │  4. for new in batches of SCAN_BATCH_SIZE (1000):       │
            │       parse_chunk_key (skip+log on ValueError)          │
            │       create batch                                      │
            │       _scan_commit()  ← cr.commit between batches       │
            │     (max_batches caps work per call)                    │
            └─────────────┬───────────────────────────────────────────┘
                          │ delegates I/O
                          ▼
            ┌─────────────────────────────────────────────────────────┐
            │ Storage.list_keys_sized                                 │
            │  - root prefix + .gz suffix stripped                    │
            │  - returns (canonical_key, size)                        │
            └─────────────┬───────────────────────────────────────────┘
                          │
                          ▼
            ┌─────────────────────────────────────────────────────────┐
            │ Adapter.list_keys_sized (fsspec)                        │
            │  - fs.find(prefix, detail=True)                         │
            │  - sizes piggyback on the listing response              │
            │    (S3 ListObjectsV2 / local stat / ...) — NO HEAD pass │
            └─────────────────────────────────────────────────────────┘
```

### Design decisions and what they cost / save

**Single backend listing call carrying sizes.** `fsspec.find(prefix,
detail=True)` returns `{path: info_dict}` in one paginated S3 listing.
That's `ceil(N/1000)` HTTP round trips for N keys instead of N+ceil(N/1000).
Without this the per-key `HEAD` for size would dominate runtime and S3
API costs.

**SQL for existing keys, ORM for inserts.** `chunk_ids` would force the
ORM to instantiate every existing record just to build a Python set. A
`SELECT key FROM dataset_data_chunk` returns the same data without record
materialization. Inserts still go through ORM `create()` so all the
normal compute fields, constraints, and tracking apply to the new rows.

**Pre-existing chunks are never touched.** The diff happens before any
ORM work; pre-existing chunk records are not loaded, not written, not
even examined for state. Re-scan cost grows only with the count of *new*
keys, not total keys. This is the optimization that makes daily incremental
scans cheap on 10M-key datasets.

**Batched `cr.commit()` between create batches.** Each batch (default
1000) commits independently. Three things follow:

1. A scan that gets killed mid-run loses only the in-flight batch; the
   next invocation skips already-committed keys via the existing-keys SQL.
2. Memory stays bounded — the ORM cache for chunk records doesn't grow
   beyond one batch.
3. Commits are skipped under `tools.config['test_enable']` so
   `TransactionCase` rollback still works in the test runner.

**Skip-and-log on bad keys.** `parse_chunk_key` is the only point that
can raise on per-key data. Wrapping it in `try/except` with a warning
log keeps a 6-hour scan alive when the upstream pipeline drops a stray
file.

**`max_batches` for cron-driven incremental scans.** queue_job covers
the "fire and forget for hours" case. `max_batches` covers the "I want
predictable wall-clock per cron tick" case — a cron calls
`scan_chunks(max_batches=10)` every 5 minutes; each tick processes at
most 10k keys, the next tick picks up where it left off via the
existing-keys SQL.

**`Dataset.size` as a pure sum of `chunk_ids.size`.** The chunk's `size`
is now populated from the scan-time listing, so the dataset-level
compute reduces to summation — no second pass over storage. Recomputes
only when chunk sizes change.

### Operational expectations

- **Job UI**: Settings → Technical → Queue Jobs. Filter by state
  (`pending`, `enqueued`, `started`, `done`, `failed`). Failed jobs show
  the full traceback and can be requeued in place.
- **Channel capacity**: configured in `odoo.conf` `[queue_job]
  channels = root:N`. Scans are I/O bound, so concurrency >1 helps when
  multiple datasets are scanning simultaneously.
- **Worker mode**: queue_job needs the in-process runner to be running.
  In multi-process mode (`workers > 0`) the runner forks alongside HTTP
  workers; in single-thread mode (`workers = 0`) it runs in the main
  process. Either way, `server_wide_modules = base,web,queue_job` must
  be set so the runner starts at boot.
- **Limits per worker**: `--limit-time-cpu` / `--limit-time-real` still
  apply per-batch. The batched-commit design means a worker kill costs
  at most one batch, but if a single batch consistently exceeds the
  limit, raise the limits or shrink `SCAN_BATCH_SIZE`.

### What this design does not yet do

- **Streaming listings.** `fsspec.find()` materializes the full result
  dict in worker memory. For buckets with tens of millions of objects,
  swap in `fs.walk()` (a generator) or a paginated S3 client and process
  keys as they stream in.
- **Updates / reconciliation.** Scan only inserts. A separate
  reconciliation method would be needed to (a) promote pre-seeded
  `missing` chunks to `exists` when their files appear, (b) refresh
  sizes if the upstream rewrites a key, or (c) prune chunks whose keys
  vanished from storage.
- **Single-file datasets.** With empty `key_fields`, the prefix becomes
  `"src/code."` which `fsspec.find()` doesn't treat as a single-file
  glob. Single-file datasets currently can't be scanned — only manually
  catalogued.

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
