# Threat model — AI governance dan integritas bukti

**Status: kontrol yang direncanakan, belum diaudit atau diuji.** Sumber spesifikasi: [arsitektur](../02_System_Architecture.md), [model keamanan](../05_Security_Threat_Model.md) dan [AI](../ai.md).

## Pihak dan kepercayaan

| Pihak | Memegang / mengelola | Dipercaya untuk | Tidak membuktikan |
| --- | --- | --- | --- |
| Pengguna dan approver | Sesi dan keputusan manusia | Bertindak sesuai peran yang divalidasi | Identitas saja tidak mengizinkan akses semua tenant. |
| Backend | Sesi, organisasi dan tugas | Memvalidasi akses dan meneruskan identitas internal | Bahwa proposal model aman dieksekusi. |
| Agent | Konfigurasi model dan proposal | Menghasilkan usulan terstruktur | Otorisasi, eksekusi atau kebenaran faktual. |
| Harness | Policy, tool gateway, approval dan signing | Menegakkan policy dan membuat catatan | Kebenaran data sumber atau tindakan di luar gateway. |
| Adapter / Besu | Referensi anchor dan ledger privat | Menyimpan serta membaca kembali anchor | Kebenaran isi receipt atau konsensus terdesentralisasi pada satu node. |
| Pengelola kunci | Kunci signing dan metadata rotasi | Melindungi dan merotasi kunci | Integritas jika kunci telah disusupi. |

## Ancaman, kontrol dan bukti penerimaan

| Ancaman | Kontrol direncanakan | Bukti penerimaan yang dibutuhkan |
| --- | --- | --- |
| Akses lintas tenant / proyek | Backend dan Harness memverifikasi scope pada setiap objek. | Tes IDOR terhadap receipt, approval dan execution. |
| Eskalasi role atau approval palsu | Role-bound approval, identitas layanan, expiry dan audit. | User tanpa hak mendapat 403; execution tetap pending. |
| Replay atau balapan approval | Ikat ke execution, hash argumen dan policy; versi optimistis; cek ulang. | Tes replay, perubahan argumen, expiry dan keputusan bersamaan. |
| Prompt injection atau tool bypass | Output model tidak tepercaya, registry tetap dan gateway tunggal. | Tool tidak dikenal ditolak dan Agent tidak memiliki kredensial tool. |
| Duplikasi aksi | Idempotency key dan persistensi perubahan. | Retry tidak menghasilkan aksi terlindungi kedua. |
| Receipt diubah / signer palsu | Canonical JSON, SHA-256, Ed25519 dan kunci tepercaya. | Perubahan payload, kunci salah dan signature tidak valid gagal. |
| Chain offline atau anchor salah | Outbox, retry dan verifikasi hasil chain terpisah. | Receipt durable; pending/failed tidak pernah ditampilkan verified. |
| Kebocoran data | Redaksi log dan receipt publik; hanya digest di chain. | Uji tidak ada invoice, PII, prompt atau secret di chain. |
| Agent mengirim data sensitif ke luar | Harness memeriksa tujuan dan payload final pada tool yang dimediasi; default deny saat policy gagal atau klasifikasi tidak diketahui. Restriksi jaringan dan kredensial terpisah untuk mencegah bypass. | Mock receiver tidak dipanggil untuk fixture terlarang; uji juga tujuan tidak dikenal, payload berubah setelah cek dan jalur provider langsung. |
| Secret bocor / layanan disusupi | Secret manager, least privilege, rotasi dan jaringan internal. | Pemeriksaan secret serta uji pembatasan layanan. |

## Asumsi dan risiko tersisa

- Harness, sistem pengelolaan kunci dan policy store merupakan bagian dari batas kepercayaan. Penyusup yang mengendalikan komponen tersebut dapat merusak jaminan; anchor tidak menjamin kebenaran input.
- Satu node Besu tidak membuktikan keamanan validator terdistribusi.
- Masa retensi, backup/restore, prosedur rotasi/pencabutan kunci dan model akses verifikasi publik harus ditetapkan sebelum deployment.
- Tidak ada temuan yang dinyatakan sudah diperbaiki tanpa bukti implementasi dan pengujian.
- Blockchain tidak menjaga kerahasiaan. Hash dari nilai sensitif yang mudah ditebak dapat diserang dengan menebak input; gunakan desain komitmen yang ditinjau sebelum menerapkannya pada data tersebut.
- Pemeriksaan demo bersifat deterministik dan terbatas: tidak menjamin deteksi seluruh rahasia atau melindungi jalur yang tidak dimediasi, termasuk panggilan provider AI.
