# Istilah dan status

**Status: spesifikasi yang direncanakan.** Halaman ini adalah acuan bahasa tampilan; nilai API final akan ditetapkan di OpenAPI.

## Status eksekusi

| Nilai yang direncanakan | Label | Makna |
| --- | --- | --- |
| `CREATED` | Dibuat | Eksekusi telah dibuat. |
| `PLANNING` | Menyusun rencana | Agent diminta mengusulkan tindakan. |
| `POLICY_CHECK` | Memeriksa kebijakan | Harness mengevaluasi permintaan. |
| `ALLOWED` | Diizinkan | Kebijakan mengizinkan kelanjutan; bukan bukti tool sudah berjalan. |
| `APPROVAL_REQUIRED` | Perlu persetujuan | Kebijakan memerlukan keputusan manusia. |
| `WAITING_APPROVAL` | Menunggu persetujuan | Permintaan menunggu keputusan yang sah. |
| `DENIED` | Ditolak kebijakan | Tool tidak boleh dijalankan. |
| `EXECUTING` | Sedang dijalankan | Harness menjalankan tool yang diizinkan. |
| `SUCCEEDED` / `FAILED` | Berhasil / Gagal | Hasil eksekusi tool, terpisah dari status anchor. |

Nama status terminal untuk pembatalan dan kedaluwarsa belum ditetapkan. API task contoh menggunakan `queued`; pemetaan ke status eksekusi harus didefinisikan sebelum OpenAPI difinalkan.

## Bukti dan anchor

| Nilai | Label | Makna |
| --- | --- | --- |
| `NOT_REQUESTED` | Belum diminta | Permintaan anchor belum dilakukan. |
| `PENDING` | Menunggu anchor | Receipt tersedia tetapi anchor belum dikonfirmasi. |
| `CONFIRMED` | Anchor dikonfirmasi | Adapter telah mengonfirmasi pencatatan hash. |
| `FAILED` | Anchor gagal | Proses anchor gagal; bukan bukti otomatis bahwa eksekusi tool gagal. |
| `verified: true` | Terverifikasi | Tanda tangan dari kunci tepercaya, hash dan anchor terkonfirmasi semuanya cocok. |
| `verified: false` | Belum terverifikasi | Setidaknya satu pemeriksaan belum terpenuhi; tampilkan alasan dan status masing-masing. |

API contoh memakai `confirmed`, `pending`, dan `failed` dalam huruf kecil; penyamaan casing lintas layanan masih perlu difinalkan. Jangan gunakan “terverifikasi” untuk anchor pending, kegagalan pemeriksaan, atau chain yang tidak tersedia. Jangan menyamakan bukti integritas dengan kebenaran keputusan AI.
