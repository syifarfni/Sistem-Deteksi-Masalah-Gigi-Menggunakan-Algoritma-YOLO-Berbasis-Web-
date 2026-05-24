# DentScan 

Aplikasi web berbasis Django untuk deteksi penyakit gigi (gingivitis, karang gigi, karies) dari gambar maupun kamera/webcam secara real-time menggunakan Ultralytics YOLO versi 11. Proyek ini juga menyediakan autentikasi pengguna dan penyimpanan riwayat deteksi per pengguna, lengkap dengan optimasi penyajian gambar hasil deteksi.

## Fitur Utama
- Upload gambar untuk deteksi objek penyakit gigi
- Deteksi real-time via kamera/webcam (stream MJPEG)
- Riwayat deteksi per pengguna (login diperlukan)
- Autentikasi: registrasi, login, logout, profil, ganti password
- Optimasi gambar media (thumbnail/resize) melalui middleware

## Struktur Proyek Singkat
```
./
├─ manage.py
├─ yolo/                 # Konfigurasi project Django (settings, urls, wsgi)
├─ home/                 # Fitur deteksi (model YOLO, views, middleware)
├─ accounts/             # Autentikasi pengguna & halaman profil
├─ weights/              # Model YOLO (best.pt)
├─ media/hasil_deteksi/  # Hasil deteksi yang tersimpan
├─ detection_results/    # Log hasil deteksi (debug/penyimpanan sementara)
└─ requirements.txt.txt  # Dependensi Python
```

## Prasyarat
- Python 3.11 atau 3.12 (disarankan 3.12)
e- Pip terbaru (pip >= 23)
- Database (pilih salah satu):
  - MySQL Server (konfigurasi default)
  - SQLite (lebih sederhana, tidak perlu instalasi terpisah)
- Build tools yang sesuai sistem operasi Anda (untuk OpenCV, Torch, dan mysqlclient jika menggunakan MySQL)
  - Windows: Visual C++ Build Tools
  - Linux: `build-essential`, `libmysqlclient-dev` (jika menggunakan MySQL), dsb

Catatan: Instalasi Torch/Ultralytics dapat memakan waktu, khususnya di Windows dan/atau tanpa GPU.

## Instalasi
1) Clone/kopi kode sumber (atau buka folder ini di IDE Anda)

2) Buat virtual environment
- Windows (PowerShell):
  - `python -m venv .venv`
  - `.venv\Scripts\Activate`
- Mac/Linux (bash/zsh):
  - `python3 -m venv .venv`
  - `source .venv/bin/activate`

3) Install dependensi
- `pip install --upgrade pip wheel setuptools`
- `pip install -r requirements.txt.txt`

4) Siapkan database

### Opsi A — MySQL (Default)
- Buat database bernama `projectdeteksi` (atau sesuaikan):
  ```sql
  CREATE DATABASE projectdeteksi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  -- Opsional: buat user khusus (jangan gunakan root di produksi)
  CREATE USER 'appuser'@'localhost' IDENTIFIED BY 'strong_password_here';
  GRANT ALL PRIVILEGES ON projectdeteksi.* TO 'appuser'@'localhost';
  FLUSH PRIVILEGES;
  ```
- Secara default, `yolo/settings.py` menggunakan konfigurasi berikut:
  - ENGINE: `django.db.backends.mysql`
  - NAME: `projectdeteksi`
  - USER: `root`
  - PASSWORD: `user123`
  - HOST: `localhost`
  - PORT: `3306`
  Ubah kredensial ini sebelum ke produksi. Untuk lingkungan lokal, pastikan kredensial cocok dengan server MySQL Anda.

### Opsi B — SQLite (Lebih Sederhana untuk Pengembangan)
- Edit `yolo/settings.py` dan ganti konfigurasi database dengan SQLite:
  ```python
  DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.sqlite3',
          'NAME': BASE_DIR / 'db.sqlite3',
      }
  }
  ```
- Keuntungan SQLite:
  - Tidak perlu menginstal server database terpisah
  - Tidak perlu membuat database atau user
  - Cocok untuk pengembangan dan pengujian lokal
  - File database (`db.sqlite3`) otomatis dibuat saat migrasi pertama kali
- Catatan: Untuk produksi dengan traffic tinggi, tetap disarankan menggunakan MySQL/PostgreSQL.

5) Migrasi database dan buat superuser
- `python manage.py migrate`
- `python manage.py createsuperuser`

6) Pastikan model YOLO tersedia
- File model default: `weights/best.pt` (sudah disertakan). Jika ingin mengganti, sesuaikan path di `home/views.py` pada variabel `model_path`.

## Menjalankan Aplikasi (Development)
- Jalankan server development:
  - `python manage.py runserver`
- Buka: `http://127.0.0.1:8000/`

Akun admin: akses `http://127.0.0.1:8000/admin/` menggunakan superuser yang Anda buat.

## Cara Pakai (UI)
1) Registrasi/masuk
- Daftar di `/register/` atau login di `/login/`
2) Unggah gambar untuk deteksi
- Dari beranda (`/`), unggah gambar gigi dan jalankan deteksi
3) Deteksi kamera (real-time)
- Buka `/camera/` untuk kamera default (ID 0)
- Buka `/camera/1/` atau lainnya untuk memilih kamera lain
- Untuk menghentikan stream, tutup tab/browser, atau kirim POST ke `/camera/` dengan `action=stop`
4) Riwayat deteksi
- Buka `/riwayat/` (login diperlukan). Endpoint mengembalikan JSON riwayat milik pengguna aktif.

## API Utama (Ringkas)
- POST `/detect/`
  - Form-Data: `image` (file gambar)
  - Response: JSON dengan properti:
    - `image`: hasil deteksi (base64-encoded JPEG)
    - `detections`: array setiap deteksi `{ class, class_id, confidence, box }`
    - `messages`: ringkasan hasil deteksi
    - `processing_time`: waktu proses (ms)
    - `saved_path`: path file hasil pada server
- GET `/camera/` atau `/camera/<int:camera_id>/`
  - Response: stream MJPEG (Content-Type `multipart/x-mixed-replace; boundary=frame`)
- POST `/camera/`
  - Form-Data: `action=stop` untuk menghentikan deteksi live
- GET `/riwayat/?optimize=true`
  - Response: JSON berisi riwayat. Jika `optimize=true`, URL foto dikembalikan dengan parameter ukuran (thumbnail) agar dioptimasi oleh middleware.

Contoh cURL untuk deteksi gambar:
```
curl -X POST http://127.0.0.1:8000/detect/ \
  -H "X-CSRFToken: <token>" \
  -F "image=@contoh.jpg"
```
Catatan: Endpoint memerlukan CSRF token jika dipanggil dari browser. Dari aplikasi pihak ketiga/alat uji, Anda bisa menonaktifkan CSRF (tidak disarankan) atau gunakan cookie/CSRF sesuai standar Django.

## Optimasi Gambar Media
Terdapat middleware `ImageOptimizationMiddleware` yang mengoptimasi gambar di bawah `/media/hasil_deteksi/` ketika parameter query `size` diberikan.
- `/media/hasil_deteksi/<file>?size=thumbnail` -> thumbnail max 300px
- `/media/hasil_deteksi/<file>?size=400x300` -> resize khusus (WxH)

## Catatan Penting Keamanan & Konfigurasi
- SECRET_KEY saat ini terset di `settings.py`. Jangan gunakan nilai ini di produksi. Ganti dengan nilai aman dan simpan sebagai variabel lingkungan.
- DEBUG=True hanya untuk pengembangan. Set `DEBUG=False` di produksi dan atur `ALLOWED_HOSTS` sesuai domain/server Anda.
- Kredensial database disimpan langsung di `settings.py` untuk contoh lokal. Pindahkan ke variabel lingkungan sebelum deploy.

## Troubleshooting
- Instalasi Torch/Ultralytics lambat atau gagal: pastikan pip, wheel, setuptools terbaru. Gunakan Python 3.12 jika memungkinkan. Di Windows, pastikan Visual C++ Build Tools terpasang.
- Kamera tidak terbuka: periksa indeks kamera (0, 1, dst) atau izin akses OS. Di server tanpa kamera, endpoint `/camera/` akan mengembalikan frame error.
- MySQL tidak bisa konek: pastikan service berjalan, kredensial benar, dan database `projectdeteksi` sudah dibuat.
- Beralih antara MySQL dan SQLite: jika Anda beralih dari satu database ke database lain, jalankan `python manage.py migrate` setelah mengubah konfigurasi di `settings.py` untuk membuat skema database baru.
- File requirements bernama `requirements.txt.txt`: ini memang nama file di repo ini; gunakan nama ini saat `pip install -r requirements.txt.txt`. Jika menggunakan SQLite, Anda tidak perlu menginstal `mysqlclient` yang tercantum di requirements.

## Deploy ke Produksi
Berikut beberapa opsi yang umum digunakan. Catatan: Untuk produksi dengan traffic tinggi, disarankan menggunakan MySQL atau PostgreSQL, bukan SQLite.

### Opsi A — Linux (Gunicorn + Nginx)
1) Konfigurasi produksi di `yolo/settings.py`:
   - `DEBUG=False`
   - `ALLOWED_HOSTS=["your_domain", "server_ip"]`
   - Tambahkan `STATIC_ROOT` (misal `BASE_DIR / "staticfiles"`) dan jalankan `python manage.py collectstatic`
   - Konfigurasi database produksi (MySQL) yang aman
2) Install server WSGI
   - `pip install gunicorn`
   - Jalankan: `gunicorn yolo.wsgi:application --bind 0.0.0.0:8000 --workers 3`
3) Nginx sebagai reverse proxy
   - Proxy ke `127.0.0.1:8000`
   - Untuk endpoint stream `/camera/`, nonaktifkan buffering agar stream MJPEG tidak macet:
     ```
     location /camera/ {
       proxy_pass http://127.0.0.1:8000;
       proxy_buffering off;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header Host $host;
     }
     ```
   - Layani static dan media dari disk (pastikan `STATIC_ROOT` dan `MEDIA_ROOT` diset)

### Opsi B — Docker 
1) Buat Dockerfile yang:
   - Menggunakan python:3.12-slim
   - Menginstal dependensi sistem untuk mysqlclient/opencv
   - Menyalin kode dan menginstal `requirements.txt.txt`
   - Menjalankan `python manage.py collectstatic --noinput` (jika sudah set `STATIC_ROOT`)
   - Menjalankan `gunicorn yolo.wsgi:application -b 0.0.0.0:8000`
2) Build dan jalankan:
   - `docker build -t dentscan .`
   - `docker run -p 8000:8000 --env-file .env dentscan`
3) Jika menggunakan webcam host, diperlukan pengaturan device mapping khusus (tergantung platform) — biasanya fitur ini hanya relevan pada host yang sama dan bukan di cloud.





## Lisensi
Gunakan sesuai kebutuhan internal/proyek Anda. Periksa lisensi model/Ultralytics dan pustaka pihak ketiga terkait sebelum distribusi.