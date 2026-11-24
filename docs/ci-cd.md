# CI/CD dan operasi

**Status: direncanakan.** Tidak ada workflow, perintah, server, URL atau durasi deploy yang telah diverifikasi untuk proyek ini.

## Gerbang CI yang ditargetkan

| Gerbang | Pemeriksaan | Hasil selesai |
| --- | --- | --- |
| Kualitas | Lint dan pemeriksaan tipe sesuai stack setiap layanan. | Semua pemeriksaan yang dikonfigurasi lulus. |
| Kontrak | Validasi OpenAPI dan kompatibilitas antarlayanan. | Skema valid dan kontrak integrasi cocok. |
| Unit dan integrasi | Policy, approval, idempotensi, kriptografi dan komunikasi layanan. | Kasus dalam [rencana pengujian](04_Implementation_Plan.md) lulus. |
| Build | Build artefak dan container layanan. | Semua image dapat dibangun. |
| E2E | Demo allowed, approval, rejection, tamper dan gangguan chain. | Tidak ada eksekusi terlindungi tanpa otorisasi; status anchor jujur. |
| Keamanan | Pemeriksaan kebocoran secret dan akses tenant. | Tidak ada secret tertanam; kontrol akses teruji. |

## Rencana deployment

1. Siapkan secret manager dan konfigurasi lingkungan tanpa memasukkan secret ke repository.
2. Jalankan lima layanan, PostgreSQL dan Besu; batasi Agent, Harness, Blockchain dan RPC ke jaringan internal.
3. Publikasikan frontend dan backend melalui HTTPS; cek `/health/live` dan `/health/ready` setiap layanan.
4. Jalankan seed data sintetis dan smoke test alur procurement serta verifikasi receipt.
5. Periksa antrean approval, retry anchor, log terstruktur dan correlation ID.

Penyedia hosting, otomatisasi deployment, rollback, aturan retensi, pemulihan backup dan metrik operasional rinci belum diputuskan. Jangan menyajikan prosedur ini sebagai deploy yang telah tersedia.
