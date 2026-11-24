# STATUS.md — VERITAS AI

**Tanggal Pembaruan Terakhir:** 2026-11-24
**Fase Saat Ini:** Redesign Landing Page (Axiom.co Style & Scroll Motion) & Konfigurasi Interkoneksi Layanan Lokal
**Status Keseluruhan:** PASS (Test Suite 140+ checks passed, Next.js Production Build 0 errors, End-to-End Interconnection Verified)

---

## 1. Redesign Landing Page (Referensi Axiom.co)
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

## 2. Interkoneksi Layanan Lokal (Full Mesh Integration)
Semua service telah terhubung secara lokal:
1. **Frontend (:3000) &harr; Harness Gateway (:8002):**
   - Konfigurasi Next.js rewrites di `frontend/next.config.ts` untuk mem-proxy seluruh request `/api/v1/:path*` dan `/health/:path*` ke `http://127.0.0.1:8002`.
   - Mengeliminasi kendala CORS dan cookie跨域 di browser.
   - Live synchronization di `frontend/src/lib/store.tsx` yang secara otomatis memuat policy, agent, dan execution asli dari database SQLite Harness saat service berjalan.
2. **Harness Gateway (:8002) &harr; Agent Service (:8001):**
   - Terhubung via `VERITAS_AGENT_URL=http://127.0.0.1:8001` dan `VERITAS_AGENT_TOKEN=dev-agent-token`.
   - Proposal pembuatan task invoice di-generate oleh service agent, lalu dicegat dan dievaluasi secara deterministik oleh Harness sebelum merilis panggilan tool.
3. **Orkestrator & Konfigurasi:**
   - Disediakan file konfigurasi terpusat `.env` dan `.env.example`.
   - Disediakan script orkestrator satu perintah `./start_local.sh` yang menjalankan ketiga service secara bersamaan dengan penanganan graceful shutdown.
   - Konfigurasi `docker-compose.yml` terintegrasi mencakup `agent` (:8001) dan `harness` (:8002).

---

## 3. Bukti Verifikasi
- `.venv/bin/python tests/test_demo.py` &rarr; 140+ acceptance checks lulus (Exit code 0).
- `.venv/bin/python tests/test_agent_service.py` &rarr; Contract checks antara agent service dan harness lulus (Exit code 0).
- `.venv/bin/python tests/test_seed.py` &rarr; 9/9 seed checks lulus (Exit code 0).
- `cd frontend && pnpm build` &rarr; 13/13 static pages compiled successfully (Exit code 0).
- `cd frontend && pnpm eslint` pada landing page &rarr; 0 error, 0 warning (Exit code 0).
- Live curl end-to-end:
  - `GET http://127.0.0.1:8001/health/live` &rarr; `{"status":"ok"}`
  - `GET http://127.0.0.1:8002/health/ready` &rarr; `{"status":"ok","database":"ok"}`
  - `POST http://127.0.0.1:8002/api/v1/tasks` (Harness calls Agent on 8001) &rarr; `202 WAITING_APPROVAL`, proposal tool `approve_invoice` diterima dari `agent_service`.
  - `GET http://127.0.0.1:3000/api/v1/policies` (Proxy Next.js :3000 &rarr; :8002) &rarr; `200 OK`, live policy diterima.
