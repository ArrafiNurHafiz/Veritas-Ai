# Catatan Kajian Web — Bahan Video Demo VERITAS AI

**Sumber:** `http://localhost:3000` (dibuka dan diuji di browser sungguhan, 24 November 2026)
**Tujuan:** bekal pembuatan video demo; bukan audit produksi.

---

## 1. Gambaran Umum

VERITAS AI adalah situs + konsol demo untuk narasi **"Control Before Action"**: agen hanya mengirim proposal, Harness yang memutuskan, manusia yang menandatangani bila perlu, lalu bukti tanda tangan disimpan.

Tumpukan yang terlihat:

| Lapisan | Alamat | Peran |
|---|---|---|
| Frontend Next.js App Router | `:3000` | Landing page + konsol operator |
| Harness Gateway FastAPI | `:8002` | Mesin kebijakan, antrean approval, resep Ed25519, SQLite |
| Agent Service (opsional) | `:8001` | Penyusun proposal saja |
| Anchor | lokal/mock | Secara default **bukan** Besu sungguhan |

Route utama: `/` (landing), `/login`, `/dashboard`, `/dashboard/agents`, `/dashboard/tasks`, `/dashboard/approvals`, `/dashboard/policies`, `/dashboard/executions`, `/dashboard/trust`, `/dashboard/settings`.

---

## 2. Identitas Visual

- Latar gelap `#08090A` / `#0C0D11`, border hairline `#1E2129`, grid teknis, radial glow hangat.
- Aksen oranye `#DA5C2B` / `#EB6733`, dipakai konsisten pada logo, eyebrow, CTA, tab aktif, status, dan grafik.
- Tipografi sans (Inter/system), label mono uppercase dengan tracking lebar, angka dan kode monospace.
- Tombol CTA oranye dengan efek panah ganda; kartu border tipis, radius sedang, shadow lembut.
- Gerak: header adaptif saat scroll, reveal bertahap, marquee logo, histogram live, spotlight pada kartu.
- Kesimpulan: video sebaiknya memakai palet gelap + oranye milik produk, bukan palet terang generik.

---

## 3. Alur Yang Sudah Diuji Langsung

### 3.1 Landing Page

| Interaksi | Hasil yang teramati |
|---|---|
| Simulator nominal & vendor | `V-ABC` + Rp 8.500.000 → `APPROVAL_REQUIRED`, reason `AMOUNT_ABOVE_AUTO_CEILING (>5M)` |
| Ubah vendor ke `V-MALICIOUS`, nominal Rp 14.500.000, klik Run | `DENIED`, reason `VENDOR_NOT_ALLOWLISTED`, aksi `Immediate 403 Forbidden rejection` |
| Preset `Unlisted Vendor Block` | DSL berubah ke `reject immediate(code="UNAUTHORIZED_VENDOR")`, hasil `DENIED`, latency 0.8 ms |
| `Deny Call` / `Sign & Release` | Keduanya tersedia pada kartu antrean sign-off |
| `Tamper with 1 Byte` | Hash berubah, `HASH MISMATCH`, `INVALID SIGNATURE`, `Reconciliation Failed`; tombol berubah jadi `Restore Original Byte` |
| `Run ▶` | Status `Running...` sesaat, lalu verdict + metrik + receipt diperbarui |

### 3.2 Dashboard

- Kartu metrik: 4 tugas agen, 1 auto-approved, 1 menunggu sign-off, 2 blokir/penolakan.
- Policy dispatcher: pilih vendor + nominal lalu `Submit to Harness`; aktif policy v3, ceiling Rp 5.000.000, default DENY.
- Tabel 4 eksekusi: `WAITING_APPROVAL`, `SUCCEEDED` (anchored #10482), `REJECTED`, `DENIED`.

### 3.3 Task Center

- Tiga skenario cepat: `Auto-Approval Flow` (Rp 3,2 juta), `Approval Gate Flow` (Rp 8,5 juta), `High-Value Unverified Vendor` (Rp 14,5 juta).
- **Kondisi teknis saat pengujian:** hanya `:3000` (Next.js dev) yang aktif; `:8001` dan `:8002` menolak koneksi. Jadi alur submit di bawah adalah **simulasi frontend**, bukan eksekusi Harness sungguhan.
- Submit skenario auto → timeline `CREATED → PLANNING → POLICY_CHECK → EXECUTING → SUCCEEDED`, decision `ALLOWED`, resep Ed25519, anchor lokal #10485, verifikasi `Matched / Verified / Block #10485`.
- Submit skenario gate → berhenti di `WAITING_APPROVAL` dengan decision `APPROVAL_REQUIRED` dan alasan `AMOUNT_LIMIT`.

### 3.4 Approval Center

- Kartu pending berisi invoice, vendor, nominal, alasan gate, tombol `Review & Decide →`.
- Modal berisi proposal `approve_invoice(invoice_id: ...)`, kolom `Signer Reason / Audit Note`, tombol `Reject Invoice` dan `Authorize & Sign`.
- Setelah `Authorize & Sign`: status `APPROVED`, resep terbentuk, pending menjadi 0, riwayat bertambah.
- **Catatan penting:** perubahan state tampak lokal per halaman. Setelah berpindah ke `/dashboard/executions`, tabel kembali menampilkan data seed awal. Tombol `Reset Demo State` mengembalikan kondisi awal (sudah diklik setelah pengujian).

### 3.5 Trust Explorer

- Satu resep anchored `rcpt_7f3b8901e4d2a1c8` (Block #10482) dengan payload canonical RFC 8785.
- Sandbox verifikasi: toggle tampering mengubah `CANONICAL MATCH` menjadi `Mismatch`, `CRYPTOGRAPHICALLY VALID` menjadi `Invalid`, dan anchor menjadi `Reconciliation Failed`.
- Teks di halaman sudah benar: `VALID` hanya membuktikan integritas byte, bukan kebenaran invoice atau penalaran LLM.

### 3.6 Login

Empat persona demo: Admin (Alexa Chen), Approver (Sarah Jenkins), Operator (Marcus Vance), Auditor (Dr. Rachel Kim). Sandbox menerima password apa pun; sign-in hanya redirects lokal dan tidak membuat sesi Harness.

---

## 4. Rekomendasi Video

Format: 16:9, 60 detik, 4 chapter fitur @~10 detik.

| Detik | Adegan | UI yang direbuild |
|---|---|---|
| 0–5 | Intro: "Introducing VERITAS AI" + tagline "Control Before Action." | Logo/teks, kanvas gelap + grid |
| 5–15 | Agen mengirim proposal invoice | Kartu proposal `approve_invoice`, Rp 8.500.000, vendor tervalidasi |
| 15–27 | Gerbang deterministik menilai | Baris policy `where amount > 5M → human_approval`, verdict `APPROVAL_REQUIRED` |
| 27–39 | Manusia menahan dan menandatangani | Modal approval, audit note, klik `Authorize & Sign`, status berubah |
| 39–51 | Resep terekam, lalu dibuktikan | `SHA-256 → Ed25519 → anchor`, toggle tamper, verifikasi gagal |
| 51–60 | Closer: "Verify every receipt." + nama produk | End card oranye-gelap |

Saran teknis sesuai skill `explainer-default`: seluruh UI digambar ulang sebagai vektor bersih (bukan screenshot), satu teks + satu elemen UI per frame, kamera bergerak halus, suara latar ringan, `seek(t)` murni, font disematkan.

---

## 5. Guardrail Klaim — WAJIB DIPATUHI

Bersumber `README.md` dan `docs/submission.md`. Situs landing memuat beberapa klaim promosi yang **tidak boleh dipakai** dalam video:

| Boleh dikatakan | Jangan dikatakan |
|---|---|
| "Harness memeriksa kebijakan sebelum tool simulasi berjalan." | "Agen diisolasi pada level jaringan." |
| "Resep ditandatangani; anchor default adalah mock lokal." | "Tersimpan di Besu / konsensus terdesentralisasi." |
| "Egress melalui Harness diperiksa aturan tetap." | "DLP penuh / semua trafik agen terkontrol." |
| "Anchor pending/failed ditampilkan sebagai tidak terverifikasi." | "Blockchain membuktikan data itu benar." |
| "Akun demo bersifat sintetis." | "SSO / identitas produksi." |
| "SQLite, satu proses, satu org demo." | "Deployment enterprise multi-tenant." |

Unsur yang **tidak boleh dipakai** tanpa bukti: testimoni "Marcus Vance", angka "94%", "100% Policy Gated" sebagai metrik produk, dan frasa "Confirmed on Chain". Itu konten promosi landing, bukan fakta yang terverifikasi.

---

## 6. Bukti Pemeriksaan

- Halaman dibuka dengan browser nyata pada viewport 1440×900; seluruh rute di atas berhasil dirender.
- Interaksi diuji: simulator policy, preset, sign/release, tamper, submit task, approval, reset demo state.
- Tidak ada error JavaScript (`window.onerror`/`unhandledrejection` kosong) dan tidak ada resource gagal (`responseStatus >= 400` kosong).
- State demo dikembalikan ke kondisi awal setelah pengujian.
- File ini hanya catatan; tidak mengubah kode aplikasi.
