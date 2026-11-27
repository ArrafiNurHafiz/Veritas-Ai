# Panduan Deploy Gratis 24/7 (Vercel + Neon + Hugging Face Spaces + Odoo 17)

Arsitektur gratis **tanpa kartu kredit**, **tetap pakai Odoo 17 CE + PostgreSQL 16 + Gmail SMTP**, dan **anti-sleep**:

1. **Neon.tech (Gratis)** → 2 database PostgreSQL 16 (`veritas` & `veritas_odoo`)
2. **Hugging Face Space 1 — Odoo 17 CE (`veritas-odoo`)** → Docker (`deploy/huggingface/odoo/Dockerfile`)
3. **Hugging Face Space 2 — VERITAS Backend (`veritas-backend`)** → Docker (`deploy/huggingface/backend/Dockerfile`)
4. **Vercel (Gratis)** → Frontend Next.js 16 (`frontend/`, proxy `/api/v1/*` ke Space 2)
5. **GitHub Actions Keep-Alive** → `.github/workflows/keep-alive.yml` (ping tiap 6 jam agar tidak pernah sleep 48 jam)

---

## Langkah 1 — Buat Database Gratis di Neon.tech
1. Daftar gratis di **https://neon.tech** (login via GitHub).
2. Buat Project 1: `veritas-db` → salin connection string (`postgresql://USER:PASS@HOST/neondb?sslmode=require`).
3. Buat Project 2 (atau database kedua): `veritas-odoo` → catat `PGHOST`, `PGUSER`, `PGPASSWORD`, dan nama DB (`neondb` atau `veritas_odoo`).

---

## Langkah 2 — Deploy Odoo 17 CE di Hugging Face Space 1
1. Buka **https://huggingface.co/new-space** → pilih **Docker (Blank)** → nama mis. `veritas-odoo` → **Public**.
2. Upload/push file dari `deploy/huggingface/odoo/Dockerfile` (dan ubah path `COPY` di Dockerfile jika ditaruh di root Space, atau push seluruh repo dan set `app_file` / copy `Dockerfile` ke root Space).
3. Di **Space Settings → Variables & Secrets**, tambahkan **Secrets**:
   - `ODOO_DB_HOST` = `<host-neon-odoo>`
   - `ODOO_DB_PORT` = `5432`
   - `ODOO_DB_USER` = `<user-neon-odoo>`
   - `ODOO_DB_PASSWORD` = `<password-neon-odoo>`
4. Setelah Space `Running`, buka `https://<username>-veritas-odoo.hf.space`, buat database Odoo (atau jalankan `scripts/setup_odoo.py` dengan `ODOO_URL=https://<username>-veritas-odoo.hf.space` untuk install modul `account`, `purchase`, `mrp` dan seed vendor `V-ABC` / `V-XYZ`).

---

## Langkah 3 — Deploy VERITAS Backend di Hugging Face Space 2
1. Buat Space Docker baru: `veritas-backend` (**Public**).
2. Di **Space Settings → Variables & Secrets**, tambahkan:
   - `DATABASE_URL` = `<connection-string-neon-veritas>`
   - `VERITAS_ERP_ADAPTER` = `odoo`
   - `VERITAS_ERP_WEBHOOK_URL` = `https://<username>-veritas-odoo.hf.space`
   - `VERITAS_WEBHOOK_ALLOW_HOSTS` = `<username>-veritas-odoo.hf.space`
   - `VERITAS_ODOO_DB` = `<nama-db-odoo>`
   - `VERITAS_ODOO_USERNAME` = `admin`
   - `VERITAS_ODOO_PASSWORD` = `<password-admin-odoo>`
   - `SMTP_HOST` = `smtp.gmail.com`
   - `SMTP_PORT` = `587`
   - `SMTP_USE_TLS` = `1`
   - `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` / `VERITAS_APPROVAL_NOTIFY_EMAILS`
   - `VERITAS_PUBLIC_URL` = `https://<project-vercel-anda>.vercel.app`
   - `VERITAS_CORS_ORIGINS` = `https://<project-vercel-anda>.vercel.app`
   - `VERITAS_ED25519_PRIVATE_KEY_B64` = `<generate-sekali-agar-receipt-konsisten>`

---

## Langkah 4 — Deploy Frontend di Vercel
1. Buka **https://vercel.com/new** → import repo GitHub `ArrafiNurHafiz/Veritas-Ai`.
2. Set **Root Directory** = `frontend`.
3. Tambahkan **Environment Variables**:
   - `HARNESS_URL` = `https://<username>-veritas-backend.hf.space`
   - `NEXT_PUBLIC_VERITAS_MODE` = `enterprise`
   - `NEXT_PUBLIC_VERITAS_TEST_MODE` = `1`
4. Klik **Deploy**. Karena `frontend/next.config.ts` mem-proxy `/api/v1/*` ke `HARNESS_URL`, cookie session & CSRF berjalan *single-origin* di HTTPS.

---

## Langkah 5 — Aktifkan Keep-Alive Anti-Sleep
1. Di repo GitHub Anda → **Settings → Secrets and variables → Actions → Variables**.
2. Tambahkan 2 Variables:
   - `VERITAS_BACKEND_URL` = `https://<username>-veritas-backend.hf.space`
   - `VERITAS_ODOO_URL` = `https://<username>-veritas-odoo.hf.space`
3. Workflow `.github/workflows/keep-alive.yml` akan otomatis melakukan ping setiap 6 jam agar kedua Hugging Face Space tetap aktif 24/7 selama penjurian.
