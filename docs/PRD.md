# Product Requirements Document — VERITAS AI Enterprise

> **Status:** Implemented & Verified (fondasi; IdP final dan target deploy masih terbuka)  
> **Versi:** 1  
> **Tanggal:** 24 November 2026  
> **Product Manager:** Arrafi Nur Hafiz  
> **Produk:** VERITAS AI — Control Before Action (versi produksi)

---

## Ringkasan Eksekutif

**Masalah:** Agen AI dapat menjalankan tool yang merusak, dan kontrol berbasis prompt tidak deterministik serta tidak dapat dibuktikan setelah kejadian. Demo saat ini membuktikan alur tersebut, tetapi masih satu proses, satu org, SQLite, dan data sintetis.

**Solusi:** Membangun ulang inti governance sebagai layanan produksi: kebijakan deterministik sebelum aksi, approval manusia dengan pemisahan tugas, resep kriptografis, audit tak dapat diubah, isolasi tenant, RBAC, SSO OIDC, dan planner LLM yang hanya menghasilkan proposal.

**Hasil yang diukur:**

- Seluruh eksekusi melewati policy gate sebelum tool dipanggil.
- Tidak ada tool call untuk proposal yang ditolak, kedaluwarsa, atau disetujui oleh role yang salah.
- Setiap resep terverifikasi oleh kunci Harness dan status anchor ditampilkan terpisah.
- Dua tenant tidak dapat membaca data tenant lain.
- Seluruh perubahan kebijakan dan keputusan approval tercatat di audit log append-only.

---

## Konteks dan Fakta yang Ditemukan

**Fakta teknis dari repository:**

- Backend aktif adalah `veritas_harness.py` (FastAPI) dengan SQLite dan `agent_service.py` opsional.
- Frontend Next.js mem-proxy `/api/v1/*` ke Harness.
- Endpoint inti sudah ada: tasks, executions, approvals, policies, receipts, verify, egress.
- Resep ditandatangani Ed25519 atas JSON kanonik; verifikasi tersedia.
- Anchor secara default adalah mock lokal, bukan Besu/konsensus.
- Demo berhasil dideploy dengan Docker Compose dan preflight 18/18 lulus.

**Keputusan pengguna:**

- Rilis pertama hanya inti: Policy → Approval → Receipt.
- Penyimpanan: Postgres dengan migrasi versi.
- LLM: provider yang sudah ada, yaitu 9router lokal `:20128`.
- Kredensial: environment/vault di server; tidak pernah diketik di chat.
- Otorisasi: boleh refactor besar, migrasi, dan tes keamanan.
- Data demo tidak dimigrasi; produksi mulai dari kosong.

**Asumsi yang belum dikonfirmasi:**

- Kepatuhan: baseline audit trail append-only dan retensi log; regulasi spesifik belum dipilih.
- SSO: OIDC generik yang kompatibel dengan Keycloak/Google/Entra; IdP final belum dipilih.
- Target deploy: cloud-agnostic Docker Compose; platform akhir belum diputuskan.
- Endpoint 9router di produksi harus dapat dijangkau dari cluster; nilai default lokal hanya untuk development.

---

## Tujuan dan Non-Tujuan

**Tujuan:**

1. Mengubah vertical slice demo menjadi fondasi produksi yang dapat dijalankan enterprise.
2. Menjamin isolasi tenant dan otorisasi server-side pada semua data dan aksi.
3. Menyediakan bukti kriptografis dan audit trail yang dapat diverifikasi independen.
4. Memisahkan keputusan LLM dari eksekusi tool melalui tool registry dan policy gate deterministik.

**Non-Tujuan:**

- Tidak membangun Besu/EVM anchor atau klaim konsensus.
- Tidak membuat DLP penuh; hanya egress yang melalui Harness.
- Tidak memigrasi data demo SQLite.
- Tidak membangun billing, marketing site baru, atau Kubernetes pada rilis pertama.
- Tidak menyimpan kredensial atau data sensitif di repository.

---

## Pengguna dan Use Case

### Persona Utama

| Persona | Kebutuhan |
|---|---|
| Operator | Mengirim proposal invoice/task tanpa hak mengeksekusi langsung |
| Approver | Meninjau dan menandatangani proposal di atas batas kebijakan |
| Admin Tenant | Mengelola policy, anggota, dan vendor dalam tenant sendiri |
| Auditor | Membaca audit trail dan memverifikasi resep tanpa hak mutasi |

### Use Case Inti

**UC-1 — Proposal melewati policy gate**

1. Operator mengirim task invoice.
2. Harness memvalidasi payload dan menghasilkan proposal dari planner.
3. Policy engine mengevaluasi aturan deterministik.
4. Jika di bawah batas dan vendor diizinkan, tool simulasi berjalan dan resep dibuat.
5. Jika di atas batas, eksekusi ditahan untuk approval.

**UC-2 — Approval dengan separation of duties**

1. Approver melihat antrean tenant sendiri.
2. Approver memberikan alasan dan keputusan.
3. Harness menolak keputusan jika approver adalah requester atau tenant berbeda.
4. Pada approve, tool berjalan sekali dan resep diterbitkan.

**UC-3 — Verifikasi independen**

1. Auditor membuka resep.
2. Sistem menghitung ulang hash kanonik dan memverifikasi Ed25519.
3. Status anchor tampil terpisah; anchor pending/failed tidak pernah disebut terverifikasi.

---

## Requirements Fungsional

### P0 — Wajib Rilis Pertama

| ID | Requirement | Kriteria Penerimaan |
|---|---|---|
| FR-01 | Multi-tenant | Semua tabel data bisnis memiliki `tenant_id`; query tanpa filter tenant ditolak oleh repository layer. Uji: tenant A tidak dapat GET/PUT resource tenant B. |
| FR-02 | RBAC | Role `operator`, `approver`, `admin`, `auditor` ditegaskan di server. Uji: operator call approve endpoint → 403; auditor submit task → 403. |
| FR-03 | SSO OIDC | Login melalui authorization code flow; session server-side; CSRF double-submit untuk cookie mutation. Uji: login dummy IdP berhasil, logout mencabut sesi. |
| FR-04 | Approval gate | Proposal > batas atau vendor tidak dikenal berhenti sebelum tool call. Uji: `tool_calls = 0` saat `WAITING_APPROVAL`/`DENIED`. |
| FR-05 | Separation of duties | Requester tidak dapat menyetujui proposal sendiri. Uji: decision oleh actor yang sama → 403 dan status tetap pending. |
| FR-06 | Resep Ed25519 | Setiap eksekusi sukses menghasilkan resep dengan digest kanonik. Uji: verifikasi valid; modifikasi 1 byte membuat verifikasi gagal. |
| FR-07 | Audit append-only | Setiap mutasi kebijakan/approval menghasilkan event audit dengan hash berantai. Uji: update/delete audit ditolak; rantai hash valid. |
| FR-08 | Policy deterministik | Aturan dievaluasi di Python, bukan LLM. Uji: payload yang sama menghasilkan verdict yang sama. |
| FR-09 | LLM adapter | 9router/OpenAI-compatible menghasilkan proposal saja; output tidak dipercaya dan divalidasi. Uji: tool tidak terdaftar atau JSON cacat → DENY. |
| FR-10 | Migrasi Postgres | Schema versi dengan Alembic; migrasi naik dari kosong dan idle. Uji: `alembic upgrade head` dua kali tidak mengubah hash schema. |
| FR-11 | Claim guardrails | UI/API tidak menyebut Besu, konsensus, DLP penuh, atau SSO produksi sebelum fitur ada. Uji: snapshot teks tidak mengandung frasa terlarang. |

### P1 — Setelah Rilis Pertama

- UI admin tenant untuk manajemen anggota.
- Retention policy otomatis untuk audit log.
- Observability metrik dan alerting.
- Tool registry dengan izin per tenant.

---

## Requirements Non-Fungsional

| Area | Target yang diusulkan | Catatan |
|---|---|---|
| Latensi policy | p95 < 300 ms pada lingkungan lokal | Perlu disetujui sebagai SLO |
| Ketersediaan | Satu instance dulu; tanpa HA | HA masuk P1 |
| Enkripsi | TLS di edge; secret hanya di environment/vault | Tidak ada secret di repo |
| Audit | Append-only, hash berantai, tidak bisa diubah lewat API | Regulasi spesifik belum dipilih |
| Aksesibilitas | WCAG 2.1 AA untuk alur approval | Perlu diuji manual |
| Browser | Chromium/Firefox desktop terbaru | Mobile bukan fokus P0 |

---

## Arsitektur Target

```text
Browser
  -> Edge/Caddy (TLS)
      -> Frontend Next.js
          -> Harness FastAPI (/api/v1)
              -> Postgres (tenant-scoped)
              -> LLM Adapter (9router, proposal only)
              -> Audit Store (append-only)
```

Komponen:

| Komponen | Perubahan |
|---|---|
| Harness | Refactor repository layer ke Postgres + SQLAlchemy/Alembic |
| Auth | OIDC generic + session + CSRF + RBAC middleware |
| Policy | Tetap deterministik, dipindah ke modul domain terpisah |
| LLM | Adapter OpenAI-compatible dengan timeout, validasi, deny-by-default |
| Audit | Tabel append-only dengan hash rantai |
| Frontend | Hapus mock fallback untuk produksi; tampilkan error bila backend mati |

---

## API Inti

| Endpoint | Perubahan |
|---|---|
| `POST /api/v1/tasks` | Wajib `tenant_id` dari identity, bukan body |
| `GET /api/v1/executions` | Filter tenant wajib di server |
| `POST /api/v1/approvals/{id}/decisions` | Cek role + separation of duties |
| `GET /api/v1/policies` | Scope tenant |
| `PUT /api/v1/policies` | Admin tenant only; audit event wajib |
| `POST /api/v1/receipts/{id}/verify` | Verifikasi dengan kunci Harness |
| `GET /api/v1/audit-events` | Auditor only, append-only read |

---

## Risiko dan Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| LLM output disuntik prompt | Proposal berbahaya | Output tidak dipercaya; tool registry + policy gate tetap deterministik |
| Cross-tenant leakage | Pelanggaran data | `tenant_id` dari token, repository filter wajib, tes negatif |
| Migrasi wrong schema | Data hilang | Mulai dari DB kosong; Alembic; backup sebelum migrasi nyata |
| IdP belum dipilih | SSO tidak final | Adapter OIDC generik; konfigurasi lewat env |
| Regulasi belum spesifik | Retention/audit salah | Implementasikan baseline append-only; tandai sebagai asumsi |

---

## Open Questions

- [ ] Regulasi/kepatuhan final: GDPR/UU PDP, ISO 27001, SOC 2, atau hanya audit trail?
- [ ] IdP final: Google Workspace, Entra ID, Keycloak, atau OIDC generik?
- [ ] Target hosting produksi: VPS/cloud/managed Kubernetes?
- [ ] Endpoint 9router produksi dan kebijaksanaan timeout/retry?

---

## Definition of Done

- Semua FR P0 memiliki tes otomatis atau bukti manual yang dapat diulang.
- `pnpm lint`, `pnpm build`, dan seluruh test suite lulus.
- Migrasi dari database kosong berhasil dua kali berturut-turut.
- Regresi: demo flow Policy → Approval → Receipt tetap lulus.
- Audit trail dan isolasi tenant diverifikasi dengan tes negatif.
- Tidak ada secret, data produksi, atau klaim berlebih di dokumentasi.
