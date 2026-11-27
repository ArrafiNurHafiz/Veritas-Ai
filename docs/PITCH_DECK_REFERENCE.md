# Dokumen Referensi Pitch Deck (Build 2036 Template) — VERITAS AI

> **Selaras Template Resmi:** `/home/arrafi/Unduhan/Build 2036 _ Prototype Submission Deck Template.pptx` (**15 Slide**, TiE Global Summit 2026 Indore × Hack2Skill).  
> **File Deck Terisi:** [docs/VERITAS_AI_Build2036_Deck.pptx](VERITAS_AI_Build2036_Deck.pptx)  
> **Basis Fakta:** Kode, UI live, PostgreSQL 16 integration test, dan 7-container Docker Compose verification per **26 November 2026**.

---

## Ringkasan Cepat Presentasi

- **Team / Product Name:** VERITAS AI
- **Team Leader:** Arrafi Nur Hafiz
- **One-Liner:** **Control Before Action** — Governance Harness deterministik yang memisahkan otak proposal AI dari otoritas eksekusi, menegakkan persetujuan manusia (*Separation of Duties*), dan menerbitkan bukti kriptografis Ed25519 + audit trail *append-only*.
- **GitHub URL:** `https://github.com/ArrafiNurHafiz/Veritas-Ai`
- **Yang Masih Harus Dilengkapi Sebelum Submit:**
  1. **Demo Video URL** pada **Slide 13** (saat ini bertanda `[TODO: Insert Demo Video URL]`).
  2. Konfirmasi **Official Track / Problem Statement ID** Build 2036 pada **Slide 1** (saat ini terisi pernyataan masalah resmi proyek).

---

## Pemetaan 15 Slide Sesuai Build 2036 Template

### Slide 1 — Identitas Tim & Problem Statement
- **Prompt Template:** `Team Name :` | `Team Leader Name :` | `Problem Statement :`
- **Isi Rekomendasi:**
  - **Team Name:** `VERITAS AI`
  - **Team Leader Name:** `Arrafi Nur Hafiz`
  - **Problem Statement:** `Autonomous Enterprise AI lacks deterministic execution control, human separation-of-duties, and tamper-evident audit proof before triggering irreversible ERP, HR, Finance, and Security actions.`
- **Speaker Notes:**
  > "Perusahaan ingin memakai AI Agent untuk operasional inti, tapi tidak berani memberi akses tulis langsung ke ERP atau Cloud IAM karena LLM bisa salah tafsir atau terkena prompt injection. Kami membangun VERITAS AI: Control Before Action."

---

### Slide 2 — Brief about the Prototype
- **Prompt Template:** `Brief about the Prototype:`
- **Isi Rekomendasi:**
  - **Ringkasan Eksekutif:** VERITAS AI adalah *Runtime Governance Harness* di antara agen LLM dan sistem nyata perusahaan. Agent hanya mengusulkan aksi dalam JSON terstruktur; Harness memvalidasi kebijakan deterministik sebelum tool dijalankan.
  - **3 Pilar Inti:**
    1. **Proposal-Only Isolation (`agent_service` :8001):** Berjalan di jaringan internal tertutup (`agent_net`), tanpa kredensial DB, tanpa kunci signing, dan tanpa akses langsung ke ERP/IAM.
    2. **Deterministic Policy & Human Gate (`enterprise` :8100):** Evaluasi skema, batas nominal, allowlist vendor, *Separation of Duties* (pengaju ≠ approver), serta revalidasi ulang saat approval diputuskan (`DENIED_ON_RESUME` / `APPROVAL_EXPIRED`).
    3. **Cryptographic Proof & Multi-Tenant Audit:** Receipt Ed25519 atas canonical JSON + audit log berantai hash yang diproteksi trigger database *append-only*.

---

### Slide 3 — Opportunity
- **Prompt Template:**
  - *How different is it from any of the other existing ideas?*
  - *How will it be able to solve the problem?*
  - *USP of the proposed solution*
- **Isi Rekomendasi:**
  1. **How different from existing ideas?**
     - *vs Direct LLM SDKs (LangChain/Function Calling):* Model tidak lagi memegang fungsi eksekutor langsung.
     - *vs LLM Prompt Guardrails (NeMo/LlamaGuard):* Bukan evaluasi model probabilistik yang lambat (+latensi & rawan jailbreak), melainkan engine aturan Python deterministik.
     - *vs API Gateways (Kong/Apigee):* Bukan sekadar HTTP rate-limiter; Harness memeriksa argumen semantik tool, state approval manusia multi-peran, dan mengikat receipt kriptografis per transaksi.
  2. **How will it solve the problem?**
     - Memaksa setiap permintaan AI melewati mesin status tervalidasi (`CREATED → PLANNING → POLICY_CHECK → WAITING_APPROVAL / ALLOWED / DENIED → EXECUTING → RECEIPT`), dengan integrasi SSRF-guarded & HMAC-signed ke sistem target.
  3. **USP (Unique Selling Proposition):**
     - **4 Agent Operasional + 8 Bounded Tools** lintas departemen dalam satu Harness, **anti-TOCTOU Resume Revalidation**, **DB-enforced append-only audit** (SQLite & PostgreSQL 16 trigger), dan **Public Trust Explorer** dengan uji tamper 1-byte secara real-time.

---

### Slide 4 — List of Features Offered by the Solution
- **Prompt Template:** `List of features offered by the solution` (+ visual representations)
- **Isi Rekomendasi (6 Kartu Fitur + Katalog 4 Agent):**
  1. **Multi-Agent Bounded Catalog:** `procurement-agent` (`approve_invoice`, `check_vendor_status`), `finance-risk-agent` (`audit_reconciliation`, `flag_discrepancy`), `hr-operations-agent` (`provision_workspace`, `log_badge_request`), `security-audit-agent` (`scan_iam_keys`, `revoke_stale_token`).
  2. **Deterministic Policy & FX Normalization:** Auto-allow ≤ Rp 5 jt (vendor terdaftar `V-ABC`/`V-XYZ`), approval gate Rp 5–25 jt, hard-cap deny > Rp 25 jt, plus normalisasi USD/SGD/EUR ke IDR.
  3. **Human Gate, SoD & Expiry Sweeper:** Pemisahan pengaju vs penyetuju (`403 SEPARATION_OF_DUTIES`), *optimistic locking* (`expected_version`), dan `ApprovalExpiryWorker` latar belakang.
  4. **Anti-TOCTOU Resume Revalidation:** Memeriksa ulang `policy_version`, `args_hash`, status aktif tool & agent (`AGENT_DISABLED`), dan status blokir vendor sebelum melepaskan tool.
  5. **Ed25519 Receipt & Append-Only Audit:** Tanda tangan digital per eksekusi + rantai hash SHA-256 + database trigger yang menolak `UPDATE`/`DELETE`.
  6. **SSRF-Guarded Connectors & Multi-Tenant Governance:** Format adapter Webhook HMAC / Odoo / SAP (`erp_sandbox`), notifikasi email **SMTP asli (`STARTTLS`)** dengan `mail_sandbox` (`:8025`) sebagai fallback lokal offline, onboarding tenant API (`POST /api/v1/tenants`), dan Prometheus `/metrics`.

---

### Slide 5 — Process Flow Diagram or Use-Case Diagram
- **Prompt Template:** `Process flow diagram or Use-case diagram`
- **Visual Tertanam:** Diagram resolusi tinggi [diag_flow.png](/tmp/veritas_shots/diag_flow.png) yang menampilkan alur 5 tahap: `1. Task Dispatch (Idempotency + FX)` → `2. Isolated Agent Proposal` → `3. Deterministic Gate` → cabang `ALLOW` / `DENY (0 calls)` / `APPROVAL_REQUIRED` → `4. Anti-TOCTOU Resume Revalidation` → `5. Ed25519 Receipt & Append-Only Audit`.

---

### Slide 6 — Wireframes / Mock Diagrams & Governance Surfaces
- **Prompt Template:** `Wireframes/Mock diagrams of the proposed solution (Optional)`
- **Visual Tertanam:** Wireframe permukaan konsol RBAC [diag_wireframe.png](/tmp/veritas_shots/diag_wireframe.png) yang memetakan 4 peran server (`Operator → /tasks`, `Approver → /approvals`, `Admin → /agents & /policies`, `Auditor/Public → /trust`), ditambah jalur `/` (Landing + Playground) serta companion consoles (:8003 ERP & :8025 Mail).

---

### Slide 7 — Architecture Diagram of the Proposed Solution
- **Prompt Template:** `Architecture diagram of the proposed solution`
- **Visual Tertanam:** Diagram isolasi jaringan 7 container [diag_arch.png](/tmp/veritas_shots/diag_arch.png):
  - `edge_net`: Caddy (:8090/:443) → Next.js 16 (:3000) → VERITAS Enterprise Harness (:8100)
  - `agent_net (internal: true)`: Agent Service (:8001) ↔ LLM Gateway (`json_object` + circuit breaker) / Deterministic Planner
  - `db_net (internal: true)`: PostgreSQL 16 (`0001`–`0004` + append-only audit triggers + `backup_postgres.sh`)
  - Target terkelola: ERP Sandbox (:8003, HMAC + `VERITAS_WEBHOOK_ALLOW_HOSTS`), Mail Sandbox (:1025/:8025), dan EVM Anchor Outbox (Mock lokal / JSON-RPC opsional).

---

### Slide 8 — Technologies Used in the Solution
- **Prompt Template:** `Technologies to be used in the solution:`
- **Isi Rekomendasi (4 Kelompok Stack Aktual di Repo):**
  - **Frontend & Edge:** Next.js 16 (App Router, Turbopack), React 19, TypeScript, Tailwind CSS v4, Caddy 2 Reverse Proxy.
  - **Backend & Agent Core:** FastAPI, Python 3.12 / 3.14, Pydantic, `httpx`, OpenAI-compatible adapter (structured JSON fallback, exponential retry, `_CircuitBreaker`, `_TenantRateLimiter`).
  - **Persistence & Security:** PostgreSQL 16, SQLAlchemy 2.0, Alembic (`0001`–`0004`), `cryptography` (Ed25519), PKCE OIDC + Scrypt password hash + Double-Submit CSRF + SSRF IP/Host Guard.
  - **Ops, Sandbox & Verification:** Docker / Podman Compose, Pytest, `erp_sandbox`, `mail_sandbox`, `pg_dump` / `psql` scripts, Prometheus `/metrics`.

---

### Slide 9 — Estimated Implementation Cost (Optional)
- **Prompt Template:** `Estimated implementation cost (optional):`
- **Isi Rekomendasi (Jujur & Berbasis Baseline Open-Source + VPS):**
  - **Software & Runtime Licenses:** **$0** (Seluruh inti stack — FastAPI, Next.js, PostgreSQL 16, Caddy, Alembic, PyCA Cryptography — bersifat open-source tanpa biaya lisensi per-seat).
  - **Infrastruktur Demo/Pilot VPS (Estimasi Cloud Umum):** **~$12–$40 / bulan** `[Estimasi vendor cloud umum untuk 1 node VPS 2–4 vCPU, 4–8 GB RAM]` menjalankan seluruh 7 container Compose.
  - **LLM Inference Cost:** **$0 pada mode planner deterministik**; biaya token variabel sesuai provider OpenAI-compatible klien saat `VERITAS_LLM_BASE_URL` diaktifkan (terproteksi batas payload `64 KiB` dan `VERITAS_LLM_RPM_LIMIT` per tenant).
  - **Cutover Produksi (Klien-Dependen):** `[Sesuai infrastruktur klien: KMS/Vault existing, OIDC IdP existing, & optional EVM node]`.

---

### Slide 10 — Snapshots of the Prototype
- **Prompt Template:** `Snapshots of the prototype`
- **Visual Tertanam:** 4 tangkapan layar asli (*live capture*) dari aplikasi VERITAS AI yang dijalankan:
  1. Landing Page & Live Proposal Stream (`/`)
  2. Multi-Agent Task Center — 4 Agent Operasional (`/dashboard/tasks`)
  3. Human-in-the-Loop Approval Center (`/dashboard/approvals`)
  4. Public Trust Explorer & Ed25519 Verification (`/dashboard/trust`)

---

### Slide 11 — Prototype Performance Report / Benchmarking
- **Prompt Template:** `Prototype Performance report/Benchmarking`
- **Isi Rekomendasi (HANYA Angka Verifikasi Nyata per 26 Nov 2026):**
  - **Pytest Full Enterprise & PostgreSQL 16 Suite:** **49 / 49 Passed (`0 skipped`) dalam 8.44s** (mencakup SSRF, RBAC, SoD, multi-agent isolation, approval expiry & resume revalidation, LLM circuit breaker + red-team prompt injection, ERP/Mail Sandbox, serta DB trigger append-only di PostgreSQL 16).
  - **Acceptance & Contract Suites:** `test_demo.py` (**140+ cek lulus**), `test_e2e.py` (**36 cek HTTP & restart-durability lulus**), `test_seed.py` (**9/9**), `test_openapi.py` (**9/9**), `test_agent_service.py` (**lulus**).
  - **Live 7-Container Compose Preflight (`scripts/enterprise_preflight.py`):** Lulus end-to-end melalui Caddy `:8090` dengan PostgreSQL 16, eksekusi 4 agent, 6 transaksi ERP Sandbox, tangkapan email SMTP di Mail Sandbox, serta `pg_dump` -> `psql` restore round-trip.
  - **Frontend Production Build:** `pnpm eslint src/` (**0 error, 0 warning**) & `next build` (**13/13 halaman statis** terkompilasi).
  - *Catatan:* Belum dilakukan benchmark beban konkuren produksi skala besar; keputusan aturan Python berjalan secara lokal tanpa tambahan panggilan model LLM eksternal.

---

### Slide 12 — Additional Details / Future Development
- **Prompt Template:** `Additional Details/Future Development (if any)`
- **Isi Rekomendasi:**
  - **Fase Pasca-Hackathon / Go-Live Perusahaan (`production_plan_and_todo.md`):**
    1. **Security Cutover:** Aktifkan PKCE OIDC (Entra ID / Google / Keycloak), matikan demo bypass, dan sambungkan Ed25519 signing ke Vault / KMS dengan key rotation.
    2. **Real Enterprise Connectors:** Sambungkan `VERITAS_ERP_WEBHOOK_URL` ke staging/produksi Odoo atau SAP klien, tambah adapter HRIS (Google Workspace/MS Graph/Jira) & Cloud IAM, serta SMTP relay perusahaan.
    3. **On-Chain & Observability:** Deploy kontrak `VeritasAnchorRegistry` ke Hyperledger Besu / EVM L2 via `VERITAS_ANCHOR_RPC_URL` dan sambungkan `/metrics` ke Prometheus/Grafana.

---

### Slide 13 — GitHub & Demo Video URL
- **Prompt Template:** `GitHub & Demo video URL`
- **Isi Rekomendasi:**
  - **GitHub Repository:** `https://github.com/ArrafiNurHafiz/Veritas-Ai`
  - **Demo Video URL:** `[TODO: Tempel URL Video Demo YouTube/Loom/Drive Sebelum Submit]`
  - **Cara Menjalankan Ulang Stack Enterprise (1 Perintah):**
    - `cp .env.vps.example .env && docker compose -f docker-compose.enterprise.yml up -d --build`
    - `python3 scripts/enterprise_preflight.py`

---

### Slide 14 — Hackathon Requirements & Judge Verification Guide
- **Prompt Template:** `Add as per the requirements for the hackathon:`
- **Isi Rekomendasi:**
  - **Panduan Uji 3 Menit untuk Juri:** (1) Login multi-peran → (2) Auto-allow `Rp 3,2 jt` + receipt → (3) Hold `Rp 8,5 jt` dengan 0 tool call + notifikasi email **SMTP asli (`STARTTLS`)** (atau `:8025` saat offline) → (4) Uji blokir `403` SoD & sign-off Approver → (5) Uji 1-Byte Tamper Test di Trust Explorer.
  - **Claim Guardrails (Transparansi Teknis):** Menyatakan jujur bahwa anchor default adalah mock lokal (kecuali EVM RPC diisi), konektor target ERP memakai `erp_sandbox` (`:8003`), sedangkan email sudah mendukung SMTP asli (`STARTTLS`) dengan `:8025` sebagai fallback lokal, bypass demo aktif untuk kemudahan evaluasi, dan pemeriksaan outbound hanya mencakup jalur yang dimediasi Harness.

---

### Slide 15 — Closing (`Thank You` — Template Build 2036)
- Mempertahankan slide penutup resmi Build 2036 dengan footer identitas proyek ringkas: `VERITAS AI — Control Before Action | https://github.com/ArrafiNurHafiz/Veritas-Ai`.
