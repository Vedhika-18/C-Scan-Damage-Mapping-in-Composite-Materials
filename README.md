# C-Scan Image Generation for Internal Damage Characterization of Composite Plates

This is a small, self-contained college demonstration prototype. It maps the
uploaded CSV's spatial coordinates and signal column into a 2D C-scan image.
An optional ASCII PLY is validated and summarized, and an optional surface
image is shown beside the result.

Inspection metadata is stored in local SQLite by default, or PostgreSQL when
`DATABASE_URL` is configured. Files are stored locally by default, or in an
S3-compatible bucket when `S3_BUCKET` is configured.

There is no paired dataset or ground-truth C-scan in this workspace, so this
version intentionally does **not** claim to train or run an ML model. The
result is labeled as a baseline visualization generated from the uploaded
inspection data. CSV columns are discovered from their headers: `X`/`Y` and
signal-like names such as `Amplitude`, `Signal`, `Intensity`, `Value`, or
`Depth` are preferred; otherwise numeric columns are used.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Open http://127.0.0.1:8000. The CSV must contain at least three valid rows,
two numeric coordinate columns, and one numeric signal column. PLY support is
currently ASCII-only; it is optional when the CSV already contains spatial
data. The health check is available at `/health`.

## Production

Install dependencies and run without reload:

```bash
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
```

For a single-instance hosted demonstration, mount persistent storage and configure:

```text
DATABASE_PATH=/persistent/data/cscan.sqlite3
OUTPUT_DIR=/persistent/outputs
```

For a multi-instance deployment, configure managed PostgreSQL and object storage:

```text
DATABASE_URL=postgresql://user:password@host:5432/cscan
S3_BUCKET=cscan-results
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

`S3_ENDPOINT_URL` is optional and supports providers such as Cloudflare R2,
MinIO, and other S3-compatible services. In this mode, uploaded source files
and generated C-scans are stored under `inspections/{result_id}/`, and API
file routes return temporary signed URLs.
