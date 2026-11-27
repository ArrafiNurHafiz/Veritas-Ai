# VERITAS AI Enterprise — Runbook

Aplikasi produksi ada di modul `enterprise.main`. Demo lama (`veritas_harness.py`) sengaja dibiarkan utuh dan tidak dipakai oleh aplikasi ini.

## 1. Inisialisasi database

```bash
export DATABASE_URL='postgresql+psycopg://user:password@host:5432/veritas'
alembic -c enterprise/alembic.ini upgrade head
alembic -c enterprise/alembic.ini upgrade head   # kedua kali: no-op
```

Tanpa `DATABASE_URL`, aplikasi memakai `sqlite:///./enterprise.db` hanya untuk lokal/test. Produksi wajib Postgres.

## 2. Variabel lingkungan wajib produksi

| Variabel | Fungsi |
|---|---|
| `DATABASE_URL` | Koneksi Postgres via psycopg 3 |
| `VERITAS_SIGNING_SEED` | 64 hex karakter; kunci Ed25519 stabil antar restart |
| `OIDC_ISSUER` | URL issuer OIDC |
| `OIDC_CLIENT_ID` | Client ID |
| `OIDC_CLIENT_SECRET` | Client secret (environment/vault, jangan di repo) |
| `OIDC_REDIRECT_URI` | Callback HTTPS aplikasi |
| `VERITAS_COOKIE_SECURE=1` | Cookie hanya lewat HTTPS |
| `VERITAS_LLM_BASE_URL` | Endpoint OpenAI-compatible, mis. 9router `http://host:20128/v1` |
| `VERITAS_LLM_API_KEY` | Kredensial provider LLM (environment/vault) |
| `VERITAS_LLM_MODEL` | Nama model |
| `VERITAS_BOOTSTRAP_TENANT_ID` | Tenant awal saat database kosong |
| `VERITAS_BOOTSTRAP_TENANT_NAME` | Nama tenant awal |

Jika `VERITAS_SIGNING_SEED` tidak diisi, kunci dibuat sementara setiap proses; resep lama tidak dapat diverifikasi setelah restart. **Jangan pakai kondisi ini di produksi.**

## 3. Menjalankan stack Docker / VPS Demo

```bash
cp .env.vps.example .env
# Isi minimal VERITAS_SIGNING_SEED (contoh: openssl rand -hex 32) dan POSTGRES_PASSWORD untuk VPS
docker compose -f docker-compose.enterprise.yml up -d --build
# UI + API via Caddy: http://localhost:8090
# Enterprise API langsung: http://localhost:8100 (bound ke 127.0.0.1)
# ERP Sandbox: http://localhost:8003 (bound ke 127.0.0.1)
# Mail Sandbox Web Inbox: http://localhost:8025 (SMTP :1025 internal ke enterprise)
python3 scripts/enterprise_preflight.py

# Backup & restore volume PostgreSQL di VPS:
./scripts/backup_postgres.sh
./scripts/restore_postgres.sh backups/veritas_<db>_<timestamp>.sql.gz
```

Default `docker-compose.enterprise.yml` menyiapkan mode **demo perusahaan** dengan Postgres container, `erp_sandbox`, `mail_sandbox`, `VERITAS_SSO_BYPASS=1`, `VERITAS_KMS_BYPASS=1`, `VERITAS_AUTH_TEST_MODE=true`, dan `NEXT_PUBLIC_VERITAS_TEST_MODE=1`. Untuk hard-cutover produksi: matikan semua flag bypass (`0`/`false`), aktifkan `VERITAS_COOKIE_SECURE=1`, isi variabel OIDC, atur `VERITAS_SITE_ADDRESS` domain HTTPS Anda, dan ganti `VERITAS_SIGNING_SEED` / SMTP / ERP URL ke sistem nyata.

> **Catatan jaringan `agent`:** Service `agent` berada di jaringan Docker `agent_net` yang `internal: true`. Tanpa gateway LLM internal yang terjangkau dari `agent_net`, `agent_service.py` otomatis memakai planner deterministik per-agent sehingga demo tetap berjalan stabil dan aman.

## 4. Menjalankan API saja

```bash
uvicorn enterprise.main:app --host 0.0.0.0 --port 8100
```

Alur OIDC:

```text
GET  /api/v1/auth/start      -> redirect ke IdP
GET  /api/v1/auth/callback   -> verifikasi ID token + issue session
POST /api/v1/auth/logout     -> revoke session
```

## 5. Endpoint inti

| Method | Path | Role |
|---|---|---|
| POST | `/api/v1/tasks` | operator, admin |
| GET | `/api/v1/executions` | semua role |
| GET | `/api/v1/executions/{id}` | semua role |
| GET | `/api/v1/approvals` | approver, admin, auditor |
| POST | `/api/v1/approvals/{id}/decisions` | approver, admin |
| GET/PUT | `/api/v1/policies` | GET semua; PUT admin |
| GET | `/api/v1/receipts/{id}` | semua role |
| POST | `/api/v1/receipts/{id}/verify` | semua role |
| POST | `/api/v1/anchors/{id}/confirm` | admin (mock lokal) |
| GET | `/api/v1/audit-events?verify=true` | auditor, admin |

Semua mutation memerlukan CSRF double-submit: cookie `vt_csrf` dan header `X-CSRF-Token` harus sama.

## 6. Mode test tanpa IdP

Hanya untuk automated test:

```bash
export VERITAS_AUTH_TEST_MODE=true
export VERITAS_TEST_IDENTITY_JSON='{"user_id":"operator-1","tenant_id":"tenant-a","roles":["operator"]}'
export VERITAS_SESSION_STORE=memory
```

Mode ini tidak boleh aktif di produksi.

## 7. Verifikasi

```bash
bash scripts/run_all_tests.sh
python3 scripts/enterprise_preflight.py   # terhadap stack Docker di :8090
```

Yang diuji: migrasi dua kali, isolasi tenant, RBAC, separation of duties, resep Ed25519, audit hash-chain, tool registry, dan LLM fail-closed.

## 8. Batas klaim

- Anchor adalah mock lokal; tidak ada Besu/konsensus.
- Resep membuktikan integritas byte dan kunci Harness, bukan kebenaran invoice.
- SSO bergantung pada IdP yang dikonfigurasi; tanpa itu aplikasi menolak login.
- LLM hanya mengusulkan; policy gate tetap deterministik.
