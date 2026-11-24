# Diagram arsitektur dan alur

Semua diagram menggambarkan **rencana**, bukan sistem yang telah dibangun. Setiap direktori menyimpan sumber bertipe `candidate.json` dan tampilan Archify `index.html` yang dapat dibuka langsung tanpa server atau dependensi jaringan. Diagram disusun berdasarkan [arsitektur yang disepakati](../02_System_Architecture.md), [kontrak API](../03_API_Contracts.md) dan [threat model](../threat-model/README.md).

| Diagram | Cakupan |
| --- | --- |
| [Gambaran umum](overview/index.html) | Lima layanan, data dan batas kepercayaan. |
| [Frontend](frontend/index.html) | Landing, dashboard dan batas akses browser. |
| [Backend](backend/index.html) | Identitas, tenant dan facade API. |
| [Harness](harness/index.html) | Kebijakan, approval, tool gateway dan bukti. |
| [Alur AI](ai-flow/index.html) | Proposal tidak tepercaya sampai keputusan policy. |
| [Kontrol data keluar](data-egress/index.html) | Pemeriksaan tujuan dan payload sebelum pengiriman ke mock receiver. |
| [Alur approval](approval-flow/index.html) | Pengajuan, keputusan dan pemeriksaan ulang. |
| [Alur bukti dan anchor](anchoring-flow/index.html) | Receipt, tanda tangan, chain dan verifikasi. |
| [Siklus eksekusi](execution-lifecycle/index.html) | Status execution dan status anchor yang terpisah. |

Untuk memperbarui diagram, pasang [Archify](https://github.com/tt-a1i/archify) terlebih dahulu, periksa sumber terhadap dokumen terkait, lalu jalankan dari akar proyek:

```sh
node <path-ke-archify>/bin/archify.mjs finalize architecture docs/architecture/<nama>/candidate.json docs/architecture/<nama>/index.html --quality showcase --json
```

Ganti `<path-ke-archify>` dengan lokasi instalasi dan `<nama>` dengan direktori diagram. Hasil pemeriksaan otomatis disimpan di direktori diagram. Label diagram berbahasa Indonesia; sebagian kontrol viewer Archify menggunakan bahasa Inggris.
