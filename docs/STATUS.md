# STATUS.md — VERITAS AI

**Tanggal Pembaruan Terakhir:** 2026-11-25
**Fase Saat Ini:** Dashboard Live Sync, RBAC Enforcement & Demo-Ready Acceptance
**Status Keseluruhan:** PASS (Test Suite 140+ checks passed, E2E HTTP 36/36 passed, Demo Preflight 100% passed, Next.js Production Build 0 errors)

---

## 1. Audit Dashboard & Penegakan RBAC Live
- **Integrasi Penuh:** Dashboard Next.js tidak lagi mock murni; terhubung langsung ke backend via proxy `/api/v1` di port 8002.
- **Pemisahan Wewenang (RBAC):**
  - **Operator (`Marcus Vance` / `tok-operator`):** Berwenang membuat dan mengirim tugas invoice (`POST /api/v1/tasks`). Ditolak tegas jika mencoba menyetujui transaksi (`403 Forbidden`).
  - **Approver (`Sarah Jenkins` / `tok-approver`):** Berwenang meninjau dan menandatangani persetujuan invoice di atas batas auto-approval (`POST /api/v1/approvals/{id}/decisions`). Tombol pembuatan invoice dikunci dengan penjelasan pemisahan tugas.
  - **Admin (`Alexa Chen` / `tok-admin`):** Otoritas penuh: dispatch task, approve invoice, modifikasi aturan kebijakan (`/dashboard/policies`), dan konfirmasi blockchain anchor.
  - **Auditor (`Dr. Rachel Kim` / `tok-auditor`):** Read-only audit trail dan verifikasi receipt kriptografis di Trust Explorer (`/dashboard/trust`).
- **Verifikasi Kriptografi Interaktif:**
  - Pengecekan real-time Ed25519 signature & RFC 8785 canonical hash.
  - Interactive tamper sandbox yang membuktikan kegagalan verifikasi seketika jika 1 byte bukti diubah.

---

## 2. Redesign Landing Page (Referensi Axiom.co)
- **Visual & Style:** Mengadopsi aesthetic pitch-dark (`#08090A` / `#0C0D11`), aksen oranye Axiom (`#DA5C2B` / `#EB6733`), hairline borders (`#1E2129`), technical grid background (`axiom-grid-bg`), dan radial warm glow.
- **Animasi & Efek Scroll:**
  - Header adaptif saat scroll (`window.scrollY > 20`) dengan glassmorphism shadow.
  - Dual-arrow slide animation khas tombol Axiom (`axiom-btn-arrow`).
  - Staggered in-view scroll reveal (`motion/react`) di seluruh card, heading, dan frame.
  - Mouse-tracking radial spotlight glow pada bento card problem.
  - Infinite continuous marquee scrolling pada partner logo strip.
  - Animated telemetry histogram bars di interactive playground.
- **Komponen Interaktif:**
  - Interactive Telemetry Illustration Frame di Hero (live proposals & skenario switcher).
  - Feature Deep Dives (simulator slider nominal & vendor allowlist, queue approval interaktif, dan 1-byte tamper-proof cryptographic test).
  - Interactive Policy DSL / APL Query Playground dengan metrik latency dan hasil scan live.

---

## 3. Interkoneksi Layanan Lokal (Full Mesh Integration)
Semua service telah terhubung secara lokal:
1. **Frontend (:3000) &harr; Harness Gateway (:8002):**
   - Konfigurasi Next.js rewrites di `frontend/next.config.ts` untuk mem-proxy seluruh request `/api/v1/:path*` dan `/health/:path*` ke `http://127.0.0.1:8002`.
   - Mengeliminasi kendala CORS dan cookie di browser.
   - Live synchronization di `frontend/src/lib/store.tsx` yang secara otomatis memuat policy, agent, dan execution asli dari database SQLite Harness saat service berjalan.
2. **Harness Gateway (:8002) &harr; Agent Service (:8001):**
   - Terhubung via `VERITAS_AGENT_URL=http://127.0.0.1:8001` dan `VERITAS_AGENT_TOKEN=dev-agent-token`.
   - Proposal pembuatan task invoice di-generate oleh service agent, lalu dicegat dan dievaluasi secara deterministik oleh Harness sebelum merilis panggilan tool.
3. **Orkestrator & Konfigurasi:**
   - Disediakan file konfigurasi terpusat `.env` dan `.env.example`.
   - Disediakan script orkestrator satu perintah `./start_local.sh` yang menjalankan ketiga service secara bersamaan dengan penanganan graceful shutdown.
   - Script preflight otomatis `scripts/demo_preflight.py` untuk validasi kesehatan stack sebelum demo.
   - Konfigurasi `docker-compose.yml` terintegrasi mencakup `agent` (:8001) dan `harness` (:8002).

---

## 4. Bukti Verifikasi Lengkap
- `scripts/demo_preflight.py` &rarr; 100% checks passed (Exit code 0).
- `tests/test_demo.py` &rarr; 140+ acceptance checks passed (Exit code 0).
- `tests/test_e2e.py` &rarr; 36 HTTP E2E checks passed (Exit code 0).
- `tests/test_agent_service.py` &rarr; Contract checks antara agent service dan harness passed (Exit code 0).
- `tests/test_seed.py` &rarr; 9/9 seed checks passed (Exit code 0).
- `tests/test_openapi.py` &rarr; 9/9 OpenAPI contract checks passed (Exit code 0).
- `cd frontend && pnpm build` &rarr; 13/13 static pages compiled successfully (Exit code 0).
- `cd frontend && pnpm eslint src/` &rarr; 0 error, 0 warning (Exit code 0).

---

## 5. Multi-Agent Workforce (2026-11-26)
- **4 Agent Operasional (`enterprise/agents.py`, `agent_service.py`):**
  1. `procurement-agent` — Procurement Agent (`approve_invoice`, `check_vendor_status`)
  2. `finance-risk-agent` — Finance Risk Agent (`audit_reconciliation`, `flag_discrepancy`)
  3. `hr-operations-agent` — HR Operations Agent (`provision_workspace`, `log_badge_request`)
  4. `security-audit-agent` — Security Audit Agent (`scan_iam_keys`, `revoke_stale_token`)
- **Tool Catalog Isolation & Deterministic Policy:** Setiap agent dibatasi pada katalog tool miliknya (`TOOL_NOT_ALLOWED_FOR_AGENT`), divalidasi oleh `ToolRegistry`, dievaluasi deterministik (`ALLOW` / `APPROVAL_REQUIRED` / `DENY`), dan `agent_id` diikat ke Ed25519 receipt.
- **Dashboard Sync:** Memperbaiki `frontend/src/lib/store.tsx` agar memanggil `GET /api/v1/agents` di mode Enterprise, menambahkan pemilih agent & task flow dinamis di `/dashboard/tasks`, badge dinamis di sidebar, serta tamper simulation lintas agent di `ReceiptViewer`.

---

## 6. Sinkronisasi Lintas-Layanan Penuh (2026-11-26)
- **Enterprise (:8002/:8100) ↔ Agent Service (:8001) ↔ LLM (`9router`/OpenRouter):** `enterprise/llm.py` memanggil `POST /internal/v1/agents/{agent_id}/proposals` saat `VERITAS_AGENT_URL` diset (fail-closed `AGENT_UNAVAILABLE` jika offline/tanpa token), sementara `agent_service.py` menjalankan LLM-or-deterministic untuk keempat agent; `Dockerfile` dan `start_local.sh` menyinkronkan modul `enterprise` serta env LLM ke container/proses agent.
- **Enterprise (:8002) ↔ ERP Sandbox (:8003):** Penolakan manusia (`REJECTED`) pada tool ERP kini disinkronkan balik ke webhook ERP Sandbox (`sync_erp_execution_status`), dan `start_local.sh` menyinkronkan `VERITAS_HARNESS_URL`, `ERP_SANDBOX_API_KEY`, dan `ERP_SANDBOX_HMAC_SECRET`.
- **Frontend (:3000) ↔ Backend:** `store.tsx`, `settings/page.tsx`, `tasks/page.tsx`, `policies/page.tsx`, dan `DashboardHeader.tsx` menyinkronkan toggle tool, publish policy, keputusan approval, serta identitas tenant secara langsung.

---

## 7. Hardening Demo VPS & Lifecycle Approval
- **Approval Expiry & Resume Revalidation (`enterprise/repositories.py`, `enterprise/main.py`):**
  - Pending approval yang melewati `expires_at` otomatis ditransisikan ke `EXPIRED` (`APPROVAL_EXPIRED` + audit event `approval.expired`, `tool_calls = 0`) sebelum keputusan diproses (`409 APPROVAL_EXPIRED`).
  - Persetujuan (`POST /api/v1/approvals/{id}/decisions`) melakukan revalidasi penuh terhadap state execution, `args_hash`, `policy_version`, izin tool agent & tenant, status vendor, serta aturan policy aktif (`DENIED` / `DENIED_ON_RESUME` jika ada perubahan setelah approval dibuat).
- **Kesiapan Deploy VPS (`docker-compose.enterprise.yml`, `Dockerfile`, `.env.vps.example`, `scripts/backup_postgres.sh`, `scripts/restore_postgres.sh`, `.github/workflows/ci.yml`):**
  - Menambahkan service `erp_sandbox` dan `mail_sandbox` ke stack Compose lengkap dengan forwarding variabel `VERITAS_SSO_BYPASS`, `VERITAS_KMS_BYPASS`, `VERITAS_CORS_ORIGINS`, `VERITAS_EXPIRY_SWEEP_SECONDS`, `VERITAS_WEBHOOK_ALLOW_HOSTS`, `VERITAS_ERP_*`, `SMTP_*`, `VERITAS_APPROVAL_NOTIFY_EMAILS`, `VERITAS_PUBLIC_URL`, dan `VERITAS_ANCHOR_*`.
  - Memperbaiki SSRF allowlist terarah (`VERITAS_WEBHOOK_ALLOW_HOSTS=erp_sandbox`) dan filter gauge `veritas_approvals_pending` (`status == "pending"`).
  - Menjaga bypass demo login tetap aktif secara default sesuai konfigurasi demo perusahaan sampai cutover OIDC & KMS produksi dilakukan.

---

## 8. Governance Multi-Tenant, Background Expiry Worker & LLM Hardening (2026-11-26)
- **Background Expiry Worker & Multi-Tenant Governance (`0004_agent_configs.py`, `enterprise/main.py`, `frontend/src/app/dashboard/agents/page.tsx`):**
  - Menambahkan `ApprovalExpiryWorker` pada `lifespan` untuk sweep berkala di seluruh tenant, `PATCH /api/v1/agents/{agent_id}` + kontrol UI admin untuk enable/disable agent (`AGENT_DISABLED` fail-closed pada task baru & resume approval), serta onboarding tenant baru via `POST /api/v1/tenants`.
- **LLM Hardening & CI PostgreSQL 16 (`enterprise/llm.py`, `agent_service.py`, `.github/workflows/ci.yml`):**
  - Menambahkan `response_format={"type":"json_object"}` dengan fallback `400/422`, retry/backoff transien, `_CircuitBreaker`, `_TenantRateLimiter`, proteksi ukuran payload `413`, test red-team prompt injection 4 agent, skrip backup/restore PostgreSQL, dan job CI `postgres-integration` + verifikasi runtime 7-container Compose penuh.

---

## 9. Pitch Deck Submission Build 2036 (2026-11-26)
- **File Deck:** `docs/VERITAS_AI_Build2036_Deck.pptx` (15 slide selaras template resmi `/home/arrafi/Unduhan/Build 2036 _ Prototype Submission Deck Template.pptx` dan `docs/PITCH_DECK_REFERENCE.md`).
- **Visual & Verifikasi:** Menyematkan 3 diagram arsitektur/alur/wireframe (`diag_flow.png`, `diag_wireframe.png`, `diag_arch.png`) dan 4 tangkapan layar aplikasi live (`shot_hero.png`, `shot_tasks.png`, `shot_approvals.png`, `shot_trust.png`), serta diverifikasi dengan render PDF/PNG 15 slide via LibreOffice + `pdftoppm` tanpa overlap/clipping.
- **Sisa Aksi Sebelum Submit:** Tempel URL video demo pada Slide 13 (`[TODO: Insert Demo Video URL]`) dan konfirmasi Official Track / Problem Statement ID pada Slide 1.
