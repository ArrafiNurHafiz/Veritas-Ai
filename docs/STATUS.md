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
