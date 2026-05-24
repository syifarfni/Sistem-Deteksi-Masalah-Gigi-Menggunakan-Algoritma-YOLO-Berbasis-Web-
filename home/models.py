# your_app/models.py
from django.db import models
from django.contrib.auth.models import User

class RiwayatDeteksi(models.Model):
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='riwayat_deteksi')
    tanggal        = models.DateField(auto_now_add=True)
    hasil_diagnosa = models.TextField()
    foto_hasil     = models.ImageField(upload_to='hasil_deteksi/')

    def __str__(self):
        return f"{self.user.username} @ {self.tanggal}"
