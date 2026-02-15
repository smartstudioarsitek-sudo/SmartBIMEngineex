class Green_Audit:
    def hitung_panen_hujan(self, luas_atap, curah_hujan_mm_thn):
        """
        Menghitung potensi Rainwater Harvesting.
        Rumus: Luas Atap x Curah Hujan x 0.8 (Koefisien Aliran)
        """
        # Konversi mm ke meter = /1000
        volume_m3 = luas_atap * (curah_hujan_mm_thn / 1000) * 0.8
        liter_thn = volume_m3 * 1000
        
        hemat_air = liter_thn / 365 # liter per hari
        
        return {
            "Potensi Air Hujan": f"{volume_m3:.1f} m3/tahun",
            "Penghematan Harian": f"{hemat_air:.0f} liter/hari",
            "Rekomendasi": "Cukup untuk siram taman & flushing toilet" if hemat_air > 100 else "Hanya cukup untuk siram taman kecil"
        }

    def cek_orientasi_bangunan(self, arah_hadap):
        """
        Analisis termal sederhana berdasarkan hadap rumah.
        """
        arah = arah_hadap.lower()
        if "utara" in arah or "selatan" in arah:
            return "✅ ORIENTASI BAIK: Panas matahari minim, cahaya maksimal. Beban AC rendah."
        elif "timur" in arah:
            return "⚠️ PERHATIAN: Terpapar matahari pagi. Bagus untuk kesehatan, tapi perlu shading di jam 10-12."
        elif "barat" in arah:
            return "❌ ORIENTASI PANAS: Terpapar matahari sore yang menyengat. WAJIB sun-shading/secondary skin tebal."
        else:
            return "ℹ️ Analisis orientasi membutuhkan arah mata angin spesifik."