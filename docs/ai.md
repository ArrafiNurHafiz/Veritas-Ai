# AI dan batas kepercayaan

**Status: rencana MVP.** Agent menghasilkan proposal; Harness adalah penegak kebijakan dan satu-satunya pemanggil tool terlindungi.

## Alur

1. Backend mengautentikasi pengguna dan mengirim permintaan dengan konteks organisasi terverifikasi ke Harness.
2. Harness meminta Agent membuat rencana dengan skema tool yang diizinkan.
3. Agent mengembalikan nama tool, argumen dan alasan terstruktur. Respons model, dokumen invoice dan input pengguna dianggap tidak tepercaya.
4. Harness memvalidasi skema, registry, ruang lingkup, argumen dan kebijakan sebelum memutuskan deny, approval atau execution.
5. Jika disetujui, Harness memeriksa kembali persetujuan dan kebijakan sebelum memanggil tool simulasi.

Untuk skenario outbound-data, Harness memeriksa tujuan dan payload final sebelum tool pengiriman memanggil mock receiver lokal. Aturan demo memblokir field sensitif sintetis dan tujuan yang tidak ada dalam allowlist; payload yang memenuhi aturan setelah redaksi dapat diizinkan. Policy gagal atau klasifikasi tidak diketahui berarti deny. Ikat payload dan tujuan final pada keputusan agar tidak berubah setelah pemeriksaan.

Kontrol ini tidak otomatis memeriksa prompt yang dikirim ke provider model atau lalu lintas langsung agent. Batasi jalur tersebut secara terpisah dan nyatakan cakupan yang belum terlindungi. Deteksi demo berbasis aturan tidak membuktikan semua rahasia dapat ditemukan.

Lihat [diagram alur AI](architecture/ai-flow/index.html), [arsitektur](02_System_Architecture.md) dan [threat model](threat-model/README.md).

## Pagar pengaman yang diwajibkan

| Risiko | Kontrol yang direncanakan | Verifikasi |
| --- | --- | --- |
| Prompt injection dalam invoice | Perlakukan dokumen sebagai data; keputusan otorisasi berada di luar model. | Uji instruksi berbahaya dalam teks invoice tidak melewati gateway. |
| Model mengaku berwenang | Abaikan klaim model; policy engine deterministik memutuskan. | Proposal yang melampaui batas tetap memerlukan approval. |
| Tool atau argumen tidak valid | Registry tetap dan validasi skema server-side. | Tool tak dikenal dan nominal tidak valid ditolak. |
| Agent dikompromikan | Tanpa kredensial tool, akses tulis data terlindungi atau akses blockchain langsung; batasi jaringan. | Uji Agent tidak dapat memanggil tool secara langsung. |
| Keluaran tidak deterministik | Respons terstruktur dan fallback demo deterministik. | Skenario demo tetap dapat diulang tanpa provider model. |

Provider, model, skema proposal final, kebijakan retensi prompt dan detail fallback belum dipilih. Jangan mengklaim sandbox universal atau keakuratan faktual model.
