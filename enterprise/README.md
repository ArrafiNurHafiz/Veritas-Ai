# VERITAS AI — enterprise data layer

SQLAlchemy 2.0 ORM/Core models, typed tenant-scoped repositories and Alembic
migrations. The legacy demo files are untouched; production starts from an
empty database.

## Install

```bash
pip install -r enterprise/requirements.txt
```

## Migrate

From the repository root (the URL is read from `DATABASE_URL`, default
`sqlite:///./enterprise.db`):

```bash
alembic -c enterprise/alembic.ini upgrade head
alembic -c enterprise/alembic.ini downgrade base   # rollback, dev only
```

Example Postgres URL:
`DATABASE_URL=postgresql+psycopg://user:password@host:5432/veritas`

`postgresql://` and `postgres://` URLs are automatically normalised to the
psycopg 3 driver. No credentials are stored in this repository.

## Modules

- `enterprise/config.py` — engine/session factory, `DATABASE_URL` handling.
- `enterprise/hashing.py` — `canonical_json`, `sha256`, `audit_hash`, UTC helpers.
- `enterprise/models.py` — 14 tables; `Base.metadata` is the Alembic target.
- `enterprise/repositories.py` — typed create/get/list with mandatory tenant
  filter. Audit events are append-only: no update/delete function exists.
- `enterprise/migrations/` — Alembic environment and initial schema.

## Tests

```bash
python -m pytest tests/test_enterprise_data.py -q
```

Tests create their own in-memory SQLite database; no external service is
required. Timestamps are stored as ISO-8601 UTC strings for deterministic
hashing across SQLite and Postgres.
