# TODO Implementasi — VERITAS AI

**Status:** sebagian diimplementasikan. Slice P0 jalan sebagai satu layanan Harness; kotak kosong tetap berarti belum selesai. Gunakan [PRD](01_PRD.md), [arsitektur](02_System_Architecture.md), [kontrak API](03_API_Contracts.md) dan [threat model](threat-model/README.md) sebagai acuan.

## Status implementasi (24 November 2026)

Slice P0 jalan sebagai **satu layanan Harness**, bukan lima. Kode: `veritas_harness.py`, `llm_planner.py`, `seed_demo.py`. Check: `tests/test_demo.py` (140), `tests/test_seed.py` (9) dan `tests/test_openapi.py` (9). UI demo menempel di Harness (`/ui`); Trust Explorer publik di `/trust`; anchor default mock lokal, dengan adapter JSON-RPC opsional ke satu node EVM dev. Belum ada jaringan Besu, kontrak, atau bukti konsensus.

| Area | Status |
| --- | --- |
| Task → proposal → policy → approval → tool simulasi → receipt | Selesai |
| Egress gate + mock receiver | Selesai |
| Receipt Ed25519 + hash-chain + verifikasi publik | Selesai (anchor mock) |
| Expiry approval + idempotensi | Selesai |
| Planner deterministik + adapter LLM opsional | Selesai (provider nyata belum diuji) |
| Frontend/Backend/Agent sebagai layanan terpisah | Belum |
| Besu nyata, mTLS, Postgres, multi-tenant, CI, deployment | Belum |

## Target dan aturan prioritas

**Target demo:** perusahaan dapat melihat bahwa agent tidak menjalankan tindakan berisiko atau mengirim data terlarang sebelum pemeriksaan Harness. Tunjukkan satu alur procurement dan satu alur data keluar menggunakan data sintetis.

- **P0:** diperlukan untuk demonstrasi kontrol, keamanan jalur yang didemokan dan submission.
- **P1:** penting untuk memenuhi target platform dan penerimaan MVP penuh; kerjakan setelah jalur P0 stabil. Khususnya, tanpa anchor Besu nyata yang terkonfirmasi, acceptance *confirmed anchor* pada PRD **belum lulus**.
- **P2:** pengembangan berikutnya jika waktu memungkinkan.
- Urutan dependensi: `00 → 01 → 02 → 03/04 → 05/06 → 07 → 08 → 09`. Besu (`10`) bergantung pada receipt (`07`); integrasi UI dan pengujian akhir bergantung pada alur terkait.
- Topologi lima layanan adalah target, bukan alasan untuk mengorbankan demo. Alternatif yang lebih kecil tetap harus menempatkan kontrol dan eksekusi tool di sisi server, dan memberi label mock dengan jujur.

## 00 — Keputusan dan persiapan [P0]

- [ ] **T00.1 — Konfirmasi aturan hackathon.** Periksa kategori Applied AI & Agentic Intelligence, eligibility internasional, ukuran tim, aturan kode sebelumnya, format submission, deadline beserta zona waktu, rubrik, dan kewajiban hadir di Indore. **Selesai:** tautan aturan dan keputusan tim tercatat; jangan mengasumsikan deadline dari jadwal lama masih berlaku. **Status 24 Nov 2026:** Aturan hackathon belum dikonfirmasi.
- [ ] **T00.2 — Bekukan scope demo.** Pilih bentuk deployment yang dapat diselesaikan oleh tim dan tetapkan pengguna, fixture sintetis, tujuan mock serta batas policy. **Selesai:** daftar P0 dan apa yang disimulasikan disetujui tanpa mengklaim kontrol di luar cakupan. **Status 24 Nov 2026:** Scope dibekukan di README (satu layanan, Nexora, mock receiver); persetujuan tim belum dicatat.
- [ ] **T00.3 — Putuskan kontrak yang belum final.** Tetapkan cara memilih proyek dalam organisasi, pemetaan `vendor` ke `vendor_id`, bentuk payload/tool outbound, status/casing API, serta akses dan redaksi verifikasi publik. Pertahankan `Idempotency-Key` header kecuali kontrak diperbarui. **Selesai:** [kontrak API](03_API_Contracts.md) dan OpenAPI konsisten; keputusan terbuka ditandai. **Status 24 Nov 2026:** Kontrak utama jalan di kode; keputusan terbuka (pemilihan proyek, pemetaan vendor, akses receipt publik) belum difinalkan.
- [x] **T00.4 — Tetapkan model provider demo.** Pilih provider atau fallback deterministik, cara menyuntikkan kunci dan apakah request provider dikontrol. **Selesai:** demonstrasi dapat diulang tanpa kunci eksternal; jalur provider yang belum terlindungi dinyatakan di UI/dokumen. **Status 24 Nov 2026:** Fallback deterministik default; adapter LLM opsional via env. Provider nyata belum diuji.

## 01 — Fondasi dan kontrak [P0]

- [x] **T01.1 — Siapkan struktur proyek dan kontrol versi.** Buat direktori layanan yang dipilih, manifest dependensi dan konfigurasi lingkungan berisi placeholder; jangan masukkan secret atau data nyata. **Selesai:** proyek dapat dijalankan dari checkout bersih dengan instruksi tertulis. **Status 24 Nov 2026:** Git `main` di https://github.com/ArrafiNurHafiz/Veritas-Ai; dependensi di `requirements.txt`, contoh env di README, `.gitignore` mengecualikan DB/venv/artifact. Fresh checkout: `python -m venv`, `pip install -r requirements.txt`, `uvicorn veritas_harness:app --port 8002`; Docker sebagai alternatif. Belum ada lockfile hash atau CI.
- [x] **T01.2 — Definisikan OpenAPI 3.1.** Mulai dari task, execution, approval, receipt dan verifikasi serta antarmuka internal yang dipakai demo. Tambahkan kontrak tool outbound setelah T00.3. **Selesai:** skema tervalidasi, contoh request/response dan error konsisten dengan implementasi. **Status 24 Nov 2026:**OpenAPI 3.1 otomatis; `docs/openapi.json` snapshot + `tests/test_openapi.py` gagal bila kontrak berubah tanpa refresh.
- [x] **T01.3 — Siapkan persistence, migrasi dan seed.** Simpan minimal organisasi, user/role, task, execution, approval, event dan receipt secara durable; gunakan fixture Nexora dan invoice sintetis. **Selesai:** restart tidak menghilangkan pending approval atau receipt; seed dapat diulang dengan aman. **Status 24 Nov 2026:** SQLite durable dengan runner migrasi berversi (`MIGRATIONS`, `schema_migrations`); versi 1 membuat/menambal kolom, versi 2 mem-backfill status delivery. `tests/test_demo.py` membuktikan migrasi berurutan, rerun no-op, dan DB lama mendapat kolom serta backfill; `tests/test_e2e.py` membuktikan restart mempertahankan receipt, anchor confirmed, dan pending approval. Seed idempoten. Belum ada migrasi down/rollback atau lock lintas proses.
- [x] **T01.4 — Tambahkan health dan observabilitas.** Implementasikan liveness/readiness pada layanan aktif, correlation ID dan log terstruktur yang diredaksi. **Selesai:** dependensi yang tidak siap terlihat tanpa membocorkan secret atau payload sensitif. **Status 24 Nov 2026:**live/ready, correlation ID, error envelope, akses log JSON opt-in (`VERITAS_LOG_JSON=1`), `/metrics` Prometheus di balik token internal.

## 02 — Identitas dan batas akses [P0]

- [x] **T02.1 — Implementasikan identitas pengguna demo.** Sediakan sesi admin/operator/approver/auditor dengan kredensial demo yang diinjeksi, bukan hardcoded. Terapkan keamanan cookie dan CSRF bila menggunakan cookie. **Selesai:** permintaan tanpa autentikasi dan akses role yang salah ditolak. **Status 24 Nov 2026:** Sesi server-side di tabel `sessions` (token dan CSRF disimpan sebagai hash), TTL `VERITAS_SESSION_TTL_SECONDS`, logout/expiry/revocation menghentikan cookie; login email/password (`VERITAS_ACCOUNTS`, `VERITAS_DEMO_PASSWORD`) atau token demo; rate limit 5 kegagalan/menit per kredensial; cookie `HttpOnly` + `SameSite`/`Secure` lewat env; CSRF terikat sesi, bukan hanya cookie. Belum ada hash password (plaintext env), MFA, atau session store lintas proses.
- [x] **T02.2 — Tegakkan scope organisasi/proyek.** Backend mengambil organisasi dari identitas terverifikasi; Harness memeriksa identitas internal dan scope secara independen. **Selesai:** tes tenant/proyek lain tidak dapat membaca atau mengubah task, approval dan receipt. **Status 24 Nov 2026:** Organisasi/proyek diambil dari token; eksekusi, event, receipt dan anchor lintas org mengembalikan 404; daftar dan keputusan approval difilter per scope; check `cross-org *` di `tests/test_demo.py`. UI demo dan tabel egress masih satu org.
- [ ] **T02.3 — Isolasi jalur eksekusi.** Hanya Harness memegang akses untuk memanggil tool terlindungi; agent tidak memiliki kredensial tool. Batasi jaringan dan kredensial pada lingkungan deployment yang mengklaim pencegahan bypass. **Selesai:** tes bypass pada lingkungan tersebut gagal; jalur yang belum diuji, termasuk provider model, dilaporkan sebagai celah cakupan. **Status 24 Nov 2026:** Hanya Harness memanggil tool; layanan Agent terpisah dan isolasi jaringan belum ada.

## 03 — Agent dan proposal [P0]

- [ ] **T03.1 — Implementasikan satu Procurement Agent.** Terima tugas invoice dan kembalikan proposal terstruktur sesuai skema dengan nama tool dan argumen; sediakan fallback deterministik. **Selesai:** proposal valid dapat diulang dan tidak menjalankan tool. **Status:** `agent_service.py` menyediakan layanan proposal deterministik opsional dengan token lokal. Tes `tests/test_agent_service.py` memeriksa Harness memanggil proses Agent nyata, approval tetap pending tanpa tool call, dan Agent offline menyebabkan deny tanpa tool call. Compose dua layanan dijalankan lokal: invoice di atas batas tetap `WAITING_APPROVAL` dengan nol tool call, dan setelah Agent dihentikan invoice kecil `DENIED` dengan nol tool call. Browser E2E dan isolasi jaringan deployment belum dibuktikan.
- [x] **T03.2 — Validasi proposal di Harness.** Gunakan registry tool tetap dan skema server-side; abaikan klaim otorisasi model. **Selesai:** tool tidak dikenal, argumen salah tipe, nominal negatif/malformed dan output model tidak valid ditolak. **Status 24 Nov 2026:** Registry tool tetap + validasi skema server-side; output model tidak valid = DENY.
- [x] **T03.3 — Perlakukan konten invoice sebagai data tidak tepercaya.** **Selesai:** fixture prompt injection tidak mengubah policy atau menyebabkan pemanggilan tool terlarang. **Status 24 Nov 2026:** `tests/test_demo.py` menjalankan adapter planner nyata terhadap server OpenAI-compatible palsu: payload berisi instruksi injeksi tetap hanya data, output provider dengan tool tak terdaftar = DENY/UNKNOWN_TOOL tanpa tool call, output non-skema jatuh ke planner deterministik dan tetap lulus policy. Provider/model nyata belum diuji.

## 04 — Policy dan tool gateway [P0]

- [x] **T04.1 — Implementasikan state machine dan policy default deny.** Terapkan versi/digest policy, allowlist tool/vendor dan pemeriksaan scope. Batas otomatis demo adalah IDR 5.000.000 inklusif; di atasnya perlu approval. **Selesai:** tes `0`, `5.000.000`, `5.000.001`, tipe invalid dan vendor tidak dikenal menghasilkan keputusan yang benar sesuai aturan final. **Status 24 Nov 2026:** Batas 0 / 5.000.000 / 5.000.001 / hard cap / tipe invalid diuji.
- [x] **T04.2 — Buat tool `approve_invoice` simulasi.** Semua pemanggilan melewati Harness dan hanya mengubah state invoice sintetis, tanpa pembayaran atau vendor API. **Selesai:** pending dan denied mencatat nol pemanggilan tool; allowed mengubah state sekali. **Status 24 Nov 2026:** Tool `approve_invoice` simulasi; `tool_calls` dihitung, pending/denied nol panggilan.
- [x] **T04.3 — Tambahkan idempotensi dan persistensi transisi.** Ikat key ke request dan hasil; reuse dengan payload berbeda menghasilkan 409. **Selesai:** retry paralel atau setelah timeout tidak menyebabkan aksi duplikat. **Status 24 Nov 2026:** Idempotency-Key pada task dan egress; reuse payload berbeda = 409; tool call unik per eksekusi.

## 05 — Approval manusia [P0]

- [x] **T05.1 — Buat approval durable.** Ikat permintaan ke execution, nama tool, hash argumen final, digest policy, requester dan expiry. **Selesai:** approval tetap pending setelah restart dan dapat ditelusuri. **Status 24 Nov 2026:** Approval durable di SQLite, terikat args_hash + versi policy + expiry.
- [x] **T05.2 — Implementasikan keputusan dengan role dan optimistic concurrency.** Catat approver, alasan dan waktu; tegakkan pemisahan tugas jika dikonfigurasi. **Selesai:** pengguna tanpa hak mendapat 403; keputusan bersaing atau berulang ditangani tanpa dua eksekusi. **Status 24 Nov 2026:**Role + optimistic version; uji dua thread: satu menang, satu 409, tepat satu tool call dan satu receipt.
- [x] **T05.3 — Revalidasi sebelum resume.** Periksa role, expiry, argumen, policy terkini dan status execution; reject tidak memanggil tool. **Selesai:** tes approval kedaluwarsa, replay, perubahan argumen/policy dan penolakan membuktikan nol eksekusi tidak sah. **Status 24 Nov 2026:**Revalidasi expiry, args hash, vendor, nominal, dan policy_version; gagal berarti DENIED/REJECTED tanpa tool call (`POLICY_CHANGED`).

## 06 — Perlindungan data keluar [P0]

- [x] **T06.1 — Definisikan fixture dan aturan egress.** Pilih field sensitif sintetis, format payload yang didukung dan tujuan mock allowlisted; tentukan perilaku untuk klasifikasi tidak diketahui. **Selesai:** aturan deterministik dan keterbatasannya dapat diuji dan didokumentasikan. **Status 24 Nov 2026:** Field sensitif `customer_secret`/`api_key`/`card_number`; tujuan `mock://crm` dan `mock://ledger`; klasifikasi tak dikenal = deny.
- [x] **T06.2 — Buat gateway pengiriman dan mock receiver lokal.** Periksa tujuan dan payload final, ikat keduanya pada keputusan/approval, dan cegah perubahan antara pemeriksaan dan pengiriman. **Selesai:** hanya payload yang lolos dapat mencapai mock; tidak ada layanan eksternal nyata dalam demo. **Status 24 Nov 2026:** Gateway memeriksa tujuan + payload final; mock receiver lokal mencatat panggilan.
- [x] **T06.3 — Blokir sebelum mengirim.** Sensitif, tujuan tidak diizinkan, klasifikasi tidak diketahui atau policy tidak tersedia menghasilkan deny. **Selesai:** setiap kasus membuktikan mock receiver menerima **nol** panggilan. **Status 24 Nov 2026:** Sensitif, tujuan di luar allowlist = DENY, nol panggilan; hanya nama field yang disimpan, bukan nilainya.
- [x] **T06.4 — Uji jalur allowed.** Kirim payload yang sudah disamarkan sesuai aturan ke tujuan mock yang diizinkan. **Selesai:** mock menerima tepat satu payload yang diizinkan meskipun ada retry. **Status 24 Nov 2026:** Payload teredaksi terkirim tepat sekali; retry dengan key sama tidak menduplikasi.
- [x] **T06.5 — Periksa kebocoran dan cakupan.** **Selesai:** payload rahasia mentah tidak muncul pada log, error, receipt atau blockchain; UI menyatakan kontrol hanya berlaku untuk jalur yang dimediasi dan tidak mengklaim DLP menyeluruh. **Status 24 Nov 2026:** Nilai sensitif tidak masuk DB/log/receipt; UI menyatakan kontrol hanya jalur mediated.

## 07 — Receipt dan verifikasi lokal [P0]

- [x] **T07.1 — Tetapkan format bukti dan canonicalization.** Dokumentasikan RFC 8785 JCS atau ekuivalen yang presisi, field receipt, pengurutan event dan batas data yang tidak boleh dicatat. **Selesai:** fixture yang sama menghasilkan byte dan digest yang konsisten. **Status 24 Nov 2026:** Canonical JSON sorted-keys UTF-8 tanpa whitespace, didokumentasikan; SHA-256; event hash-chain.
- [x] **T07.2 — Tanda tangani dan simpan receipt.** Gunakan Ed25519, SHA-256, key ID dan kunci privat yang diinjeksi; simpan receipt secara durable. **Selesai:** tidak ada kunci dalam source/log dan receipt tersedia setelah restart. **Status 24 Nov 2026:**Ed25519 + SHA-256 + key_id; seed dapat diinjeksi via `VERITAS_SIGNING_SEED` (64 hex) atau disimpan di SQLite. Belum secret manager.
- [x] **T07.3 — Verifikasi secara independen.** Periksa key tepercaya, signature dan canonical hash secara terpisah, termasuk receipt yang diberikan pengguna. **Selesai:** perubahan payload, key yang tidak tepercaya dan signature salah gagal; hasil signature/hash/anchor ditampilkan terpisah. **Status 24 Nov 2026:** Verifikasi terpisah: signature, key tepercaya, hash, anchor; endpoint publik `/trust`.
- [x] **T07.4 — Cegah klaim keamanan hash berlebihan.** **Selesai:** data mentah tidak dicatat; hash nilai sensitif yang mudah ditebak tidak diperlakukan sebagai enkripsi. Desain commitment yang diperlukan untuk nilai demikian ditinjau sebelum digunakan. **Status 24 Nov 2026:**Payload mentah tidak disimpan; receipt memuat nonce acak 128-bit sehingga hash tidak mudah di-brute-force untuk nilai rendah-entropi.

## 08 — Dashboard dan alur demo [P0]

- [x] **T08.1 — Bangun permukaan minimum.** Tampilkan sign-in, task procurement, proposal tool/argumen, alasan policy, approval, timeline dan verifikasi receipt. **Selesai:** operator, approver dan auditor dapat menjalankan cerita tanpa akses langsung ke layanan internal. **Status 25 Nov 2026:** Selesai. Frontend Next.js modern terhubung ke Harness Gateway (:8002) via API proxy, dengan RBAC ketat (Operator create task, Approver sign-off, Auditor read-only/verify, Admin full control).
- [x] **T08.2 — Tampilkan status dengan jujur.** Tampilkan pending/denied/allowed dan anchor terpisah; sediakan loading, empty dan error state. **Selesai:** anchor pending/failed tidak pernah ditampilkan verified; tiga agent non-procurement diberi label planned. **Status 25 Nov 2026:** Selesai. Status anchor terpisah secara kriptografis, verifikasi live ke endpoint `/api/v1/verify` + simulasi tamper interaktif di Trust Explorer, agent non-procurement dilabeli PLANNED di `/dashboard/agents`.
- [x] **T08.3 — Tampilkan demo data keluar.** **Selesai:** UI menjelaskan aturan, keputusan blokir, nol pengiriman dan kasus payload disamarkan yang diizinkan, tanpa menampilkan rahasia dalam log/bukti. **Status 24 Nov 2026:** Form egress di dashboard menampilkan keputusan dan jumlah panggilan mock.

## 09 — Verifikasi dan submission [P0]

- [x] **T09.1 — Jalankan tes unit dan integrasi.** Cakup policy, validasi, RBAC, scope, approval race/replay, idempotensi, redaksi dan receipt. **Selesai:** hasil perintah dan kegagalan dicatat; tidak ada klaim lulus untuk tes yang tidak dijalankan. **Status 24 Nov 2026:**140 check `tests/test_demo.py` + 9 `tests/test_seed.py` + 9 `tests/test_openapi.py` lulus.
- [x] **T09.2 — Jalankan E2E dan fault injection.** Uji invoice kecil, invoice di atas batas, approve/reject, user tidak berhak, unknown tool, outbound blocked/allowed, receipt diubah dan chain offline. **Selesai:** semua perilaku kritis dibuktikan, termasuk nol panggilan tool saat pending/denied. **Status 25 Nov 2026:** Selesai. `tests/test_e2e.py` (36 HTTP checks), `scripts/demo_preflight.py` (all checks pass), dan E2E live gateway integrasi terverifikasi.
- [ ] **T09.3 — Siapkan deployment dan rehearsal.** Batasi layanan internal; siapkan HTTPS untuk endpoint publik, konfigurasi secret, health check dan seed sintetis. **Selesai:** demo dapat diulang dari lingkungan bersih; keterbatasan keamanan dan layanan mock terdokumentasi. **Status 24 Nov 2026:**Dockerfile + docker-compose.yml (user non-root, volume SQLite, healthcheck) terbukti jalan lewat build dan smoke container; HTTPS, pembatasan jaringan, dan rehearsal lintas layanan belum.
- [ ] **T09.4 — Siapkan submission.** Sediakan repo, arsitektur, demo URL, instruksi, video/screenshot dan impact case sesuai aturan yang dikonfirmasi. **Selesai:** jalankan walkthrough end-to-end dan periksa setiap tautan tanpa mengklaim fitur yang belum ada. **Status 24 Nov 2026:** draft ada di `docs/submission.md`: checklist deliverable, walkthrough 3 menit, peta bukti (140/36/9/9), impact case terbatas dan daftar klaim yang dilarang. Demo URL, video/screenshot dan field formulir tetap kosong sampai aturan hackathon dikonfirmasi.

## 10 — Anchor blockchain nyata [P1 untuk demo sempit; wajib untuk acceptance MVP penuh]

**Status 24 Nov 2026:** belum ada jaringan Besu maupun kontrak; T10.1 belum dikerjakan. Default anchor adalah baris SQLite `pending` yang dikonfirmasi manual lewat `/internal/v1/anchors/{id}/confirm`. Adapter JSON-RPC opsional (`VERITAS_ANCHOR_RPC_URL`) menulis digest ke calldata satu node dev dan melakukan read-back; logika submit/retry/read-back diuji dengan node palsu, bukan Besu. Verifikasi publik tidak menganggap pending/submitted sebagai verified. Transaksi calldata bukan panggilan kontrak, jadi T10.3 belum memenuhi acceptance PRD.

- [ ] **T10.1 — Siapkan private Besu dan kontrak minimal.** Batasi RPC dan identitas penulis; anchor hanya digest receipt. **Selesai:** kontrak deployed di jaringan privat dan akses tidak sah/duplikasi ditangani.
- [ ] **T10.2 — Buat adapter, outbox dan retry idempoten.** **Selesai:** saat chain offline, receipt tetap durable dan anchor pending; recovery tidak menghasilkan anchor duplikat. **Status 24 Nov 2026:** Satu percobaan saat issuance, retry lewat `/internal/v1/anchors/sweep`, `attempts`/`last_error` tersimpan; tidak ada worker outbox terjadwal, jadi retry bergantung pemanggilan sweep.
- [ ] **T10.3 — Verifikasi read-back dan konfirmasi.** **Selesai:** signature, hash dan nilai on-chain cocok; mismatch gagal; pending/failed bukan verified. Tunjukkan satu anchor yang benar-benar confirmed untuk memenuhi acceptance PRD. **Status 24 Nov 2026:** Logika cocok/mismatch lulus terhadap node JSON-RPC palsu; belum ada anchor confirmed di Besu.
- [x] **T10.4 — Dokumentasikan batas jaringan.** **Selesai:** satu node disebut sebagai demo anchoring, bukan bukti konsensus terdesentralisasi; blockchain tidak diklaim sebagai enkripsi. **Status 24 Nov 2026:** README dan `docs/02_System_Architecture.md` menyebut satu node/dev EVM sebagai demo, bukan konsensus.

## 11 — Setelah demo [P2]

- [ ] Full organization onboarding, policy builder, pengelolaan kunci dan recovery yang matang.
- [ ] SDK/CLI, streaming SSE dengan polling fallback, dan integrasi agent tambahan.
- [ ] Agent Finance/HR/Security operasional hanya setelah scope, kontrol, dan pengujian masing-masing disetujui.
- [ ] Validator tambahan dan kebijakan operasional produksi bila benar-benar dibutuhkan.
- [ ] Riset kompetitor dan validasi kebutuhan bersama calon pembeli; jangan menyatakan diferensiasi atau permintaan pasar sudah terbukti.
