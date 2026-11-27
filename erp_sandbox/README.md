# VERITAS ERP Sandbox (`erp_sandbox/`)

Service ERP terpisah di port `8003` untuk percobaan **sebelum** dihubungkan ke webhook ERP perusahaan yang asli.

## Menjalankan Secara Terpisah
```bash
.venv/bin/uvicorn erp_sandbox.main:app --host 127.0.0.1 --port 8003
```

Buka browser ke `http://127.0.0.1:8003` untuk melihat daftar transaksi General Ledger yang masuk.

## Mengganti ke Webhook ERP Asli Nanti
Saat sudah siap menggunakan ERP perusahaan (Odoo / SAP / Custom Webhook), cukup ubah di `.env`:
```env
VERITAS_ERP_ADAPTER=odoo   # atau sap / webhook
VERITAS_ERP_WEBHOOK_URL=https://erp.perusahaan.co.id/api/webhook
VERITAS_ERP_API_KEY=...
VERITAS_ERP_HMAC_SECRET=...
VERITAS_ALLOW_INSECURE_WEBHOOKS=0
```
