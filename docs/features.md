# VERITAS AI — katalog fitur

**Status: direncanakan.** Katalog ini diturunkan dari [PRD](01_PRD.md) dan bukan daftar fitur yang sudah tersedia. Tidak ada URL demo atau akun aktif yang telah diverifikasi.

## Fokus produk

**Control Before Action:** perusahaan menetapkan batas tindakan dan pengiriman data oleh agent; Harness memeriksa keduanya sebelum tool dijalankan dan meminta persetujuan manusia bila kebijakan mensyaratkannya. Receipt dan anchor mendukung audit setelah tindakan, bukan menggantikan kontrol sebelum tindakan atau enkripsi data. Pembeli awal dan kebutuhan pasar masih merupakan hipotesis.

Prioritas hackathon adalah satu alur procurement end-to-end yang dapat dibuktikan; permukaan dan kemampuan enterprise di bawah ini adalah target, bukan seluruhnya prasyarat demo. Lihat [PRD](01_PRD.md) untuk batas P0.

### Presentasi frontend saat ini

Landing page yang ada menggunakan tipografi editorial, latar warna lembut dan elemen demonstrasi bergerak yang terinspirasi oleh [Steep](https://steep.app/). Pada desktop yang mendukung CSS view timeline, hero menempel saat scroll, teks mengecil dan memudar, sementara fragmen bergerak menuju ilustrasi workspace yang menyatu; browser lain dan preferensi reduced motion menggunakan alur normal. Scroll reveal CSS juga digunakan pada bagian berikutnya. Sidebar dashboard menyesuaikan lebar layar. Elemen visual pada landing adalah ilustrasi demo, bukan bukti status layanan sebenarnya.

## Peran

| Peran | Tanggung jawab yang direncanakan |
| --- | --- |
| Admin | Mengelola organisasi, anggota, registrasi agent dan kebijakan sesuai kewenangan. |
| Operator | Mengajukan tugas dan melihat status eksekusi yang berwenang diakses. |
| Approver | Meninjau dan memutuskan permintaan yang menunggu, dengan alasan. |
| Auditor | Membaca bukti dan hasil verifikasi sesuai hak akses. |
| Developer | Mengintegrasikan agent dan memeriksa kontrak, proposal serta receipt. |

Pemetaan hak akses per endpoint masih harus difinalkan di OpenAPI; nama peran saja tidak membuktikan otorisasi suatu objek.

## Antarmuka publik dan dashboard

| Area | Rute yang direncanakan | Fungsi | Status |
| --- | --- | --- | --- |
| Landing | `/`, `/features`, `/how-it-works`, `/docs` | Menjelaskan produk dan batasannya. | Direncanakan |
| Sign-in | `/login` | Memulai sesi. | Direncanakan |
| Overview | `/dashboard` | Ringkasan organisasi dan aktivitas. | Direncanakan |
| AI Workforce | `/agents` | Melihat dan mengelola agent; hanya Procurement yang operasional dalam target MVP. | Direncanakan |
| Task Center | `/tasks` | Mengajukan tugas dan memeriksa status. | Direncanakan |
| Playground | `/playground` | Menguji proposal dan kebijakan. | Direncanakan |
| Policy Manager | `/policies` | Melihat dan memperbarui kebijakan berversi sesuai hak akses. | Direncanakan |
| Approval Center | `/approvals` | Meninjau, menyetujui atau menolak permintaan. | Direncanakan |
| Execution Monitor | `/executions` | Menampilkan status dan urutan peristiwa. | Direncanakan |
| Trust Explorer | `/trust` | Menampilkan receipt dan hasil setiap pemeriksaan bukti. | Direncanakan |
| Organization Settings | `/settings` | Pengaturan organisasi dan akses. | Direncanakan |

Finance, HR dan Security adalah **agent yang direncanakan**, bukan fungsi operasional. Antarmuka harus responsif dan memiliki keadaan loading, kosong dan error serta label status yang dapat diakses.

## Alur procurement

| Langkah | Pelaku / komponen | Perilaku yang diharapkan |
| --- | --- | --- |
| Ajukan invoice | Operator → Backend | Terima tugas dengan idempotency key dan konteks organisasi yang diperoleh dari sesi. |
| Rencanakan | Harness → Agent | Kembalikan proposal tool terstruktur, bukan eksekusi. |
| Evaluasi | Harness | Validasi skema, registry, tenant, vendor dan kebijakan deterministik; default deny. |
| Persetujuan | Approver → Harness | Jumlah di atas IDR 5.000.000 menunggu keputusan manusia; cek ulang sebelum melanjutkan. |
| Eksekusi | Harness → tool simulasi | Hanya tool allowlisted mengubah state invoice simulasi; tidak ada transfer dana. |
| Bukti | Harness → Blockchain | Tanda tangani receipt dan anchor hash; tampilkan status anchor terpisah. |
| Verifikasi | Auditor / Trust Explorer | Periksa tanda tangan, hash dan anchor secara terpisah. |

Kebijakan demo mengizinkan otomatis jumlah hingga dan termasuk IDR 5.000.000 hanya jika semua syarat lain, termasuk allowlist vendor, terpenuhi. Contoh IDR 8.500.000 menunggu persetujuan. Lihat [istilah](istilah.md), [API](03_API_Contracts.md) dan [threat model](threat-model/README.md).

## Perlindungan data keluar — demo direncanakan

| Kondisi | Keputusan sebelum tool | Bukti |
| --- | --- | --- |
| Field sensitif sintetis atau tujuan tidak ada dalam allowlist | Blokir | Mock receiver mencatat nol panggilan; log dan receipt tidak memuat payload sensitif. |
| Payload telah disamarkan sesuai aturan dan tujuan diizinkan | Izinkan | Mock receiver lokal menerima payload sekali; retry tidak menduplikasi. |
| Policy gagal atau payload tidak dapat diklasifikasi | Blokir | Tidak ada panggilan tool pengiriman. |

Pemeriksaan ini hanya mencakup jalur yang melewati Harness. Akses langsung agent/provider ke jaringan harus dibatasi secara terpisah atau dicatat sebagai celah cakupan. Aturan demo deterministik bukan DLP menyeluruh. Blockchain tidak menjamin kerahasiaan.

## Batas fitur

Tidak ada pembayaran nyata, integrasi vendor nyata, token, coin, wallet pengguna atau klaim sertifikasi kepatuhan. Anchor membuktikan integritas catatan yang ditambatkan, bukan kebenaran keputusan AI atau data sumber. SDK, CLI, SSE dan validator tambahan adalah P1.
