# Hosting Demo — VERITAS AI

## Lokal dengan Docker

```sh
docker compose up -d --build
```

Akses: `http://localhost:8080`

Layanan:

| Service | Peran | Akses |
|---|---|---|
| `agent` | Proposal-only agent, `:8001` | internal |
| `harness` | Policy runtime + SQLite, `:8002` | internal |
| `frontend` | Next.js standalone, `:3000` | internal |
| `caddy` | Reverse proxy, `:80` di container | `localhost:8080` |

Data Nexora di-seed otomatis oleh `entrypoint.sh` sebelum Harness start. Seed bersifat idempoten. Volume `veritas-data` menyimpan SQLite.

Verifikasi:

```sh
curl -fsS http://localhost:8080/ -o /dev/null -w '%{http_code}\n'
VERITAS_BASE=http://localhost:8080 VERITAS_FRONTEND=http://localhost:8080 \
  .venv/bin/python scripts/demo_preflight.py
```

## Subdomain sendiri

Atur di `.env`:

```sh
VERITAS_SITE_ADDRESS=demo.example.com
```

Lalu ganti pemetaan port Caddy dari `8080:80` ke `80:80` dan `443:443`. Caddy akan menerbitkan sertifikat otomatis ketika DNS subdomain sudah mengarah ke server.

## Deploy ke server SSH

Hosting lokal sudah terverifikasi. Deploy eksternal memerlukan kunci publik di-`authorized_keys` di server tujuan; autentikasi tanpa kunci yang diklaim pada panel Orca tidak diterima oleh `ssh.instabox.sh:2222`.

Kunci publik mesin ini:

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKiqfK/a1IH7FH2EdmDr/x7rKnibo8oIpwbWuB1XKiKL github
```

Setelah kunci tersebut diizinkan, deploy dengan:

```sh
ssh -p 2222 <user>@ssh.instabox.sh 'mkdir -p ~/veritas && cd ~/veritas && git clone <repo-url> .'
# salin source proyek, lalu:
ssh -p 2222 <user>@ssh.instabox.sh 'cd ~/veritas && docker compose up -d --build'
```

Jangan membagikan kata sandi atau kunci privat melalui chat.

## Catatan deploy aktif

Demo sudah di-deploy ke server SSH yang diberikan, direktori `~/veritas`, dengan `docker compose up -d --build`. Seluruh kontainer sehat. Akses internal server `http://localhost:8080` → 200. Akses publik langsung ke `http://35.89.33.197:8080` masih diblokir firewall/hosting; akses akhir akan memakai subdomain pengguna. Sementara itu verifikasi dilakukan lewat SSH tunnel:

```sh
ssh -p 2222 -L 18080:localhost:8080 <user>@ssh.instabox.sh
# lalu buka http://localhost:18080
```

Fallback publik aktif (karena port inbound origin diblokir dan DNSCloud tidak bisa menjangkau origin):

```text
https://8080-agra2y7deopcerrqsal7j7p52e.instabox.tech
```

Ini diterbitkan dari server dengan:

```sh
instabox-port publish 8080 --name veritas --public
```

Tidak ada halaman peringatan, URL stabil selama sandbox hidup, dan bisa dicabut dengan `instabox-port unpublish 8080`. Tunnel Serveo sementara sudah dimatikan. Untuk memakai `veritas.rapydev.my.id`, pengaturan Origin/Proxy di portal DNSCloud atau firewall inbound tetap harus diperbaiki; `instabox-port` tidak menerima domain kustom.
