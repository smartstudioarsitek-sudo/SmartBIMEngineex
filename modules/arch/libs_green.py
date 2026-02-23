# ==============================================================================
# 📄 NAMA FILE: libs_green.py
# 📍 LOKASI: modules/arch/libs_green.py (atau modules/green/)
# 🛠️ FUNGSI: Analisis Arsitektur, RTH, Sertifikasi Hijau & Audit Ekologi
# ==============================================================================

import pandas as pd

class Green_Building_Engine:
    def __init__(self):
        self.engine_name = "SmartBIM Green & Ecological Audit Engine"
        
        # Standar Luas Minimum per Orang/Fungsi (berdasarkan Neufert/SNI)
        self.std_ruang = {
            "kamar_tidur_utama": {"min": 12, "ideal": 16, "unit": "m2"},
            "kamar_tidur_anak": {"min": 9, "ideal": 12, "unit": "m2"},
            "kamar_mandi": {"min": 2.5, "ideal": 4, "unit": "m2"},
            "ruang_tamu": {"min": 9, "ideal": 15, "unit": "m2"},
            "ruang_keluarga": {"min": 12, "ideal": 20, "unit": "m2"},
            "dapur": {"min": 6, "ideal": 9, "unit": "m2"},
            "garasi_mobil": {"min": 15, "ideal": 18, "unit": "m2/mobil"},
        }
        
        # Faktor Emisi Karbon Material (kg CO2 equivalent)
        self.co2_factor = {
            "beton": 410,  # kg CO2 per m3 beton
            "baja": 2000,  # kg CO2 per ton baja
        }

    # ==========================================
    # 1. RAINWATER HARVESTING & ORIENTASI (Kode Asli Anda)
    # ==========================================
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

    # ==========================================
    # 2. PROGRAM RUANG & KDB/RTH
    # ==========================================
    def generate_program_ruang(self, penghuni, jumlah_mobil, luas_lahan):
        """
        Menghitung Kebutuhan Luas Bangunan, KDB, dan RTH (Ruang Terbuka Hijau).
        """
        kebutuhan = []
        
        kt_anak = max(0, penghuni - 2)
        kebutuhan.append({"Ruang": "KT Utama", "Jml": 1, "Luas": self.std_ruang['kamar_tidur_utama']['ideal']})
        if kt_anak > 0:
            kebutuhan.append({"Ruang": "KT Anak", "Jml": kt_anak, "Luas": kt_anak * self.std_ruang['kamar_tidur_anak']['ideal']})
            
        kebutuhan.append({"Ruang": "R. Keluarga", "Jml": 1, "Luas": self.std_ruang['ruang_keluarga']['ideal']})
        kebutuhan.append({"Ruang": "Dapur & Makan", "Jml": 1, "Luas": self.std_ruang['dapur']['ideal'] * 1.5})
        
        km_count = int(penghuni / 3) + 1
        kebutuhan.append({"Ruang": "KM/WC", "Jml": km_count, "Luas": km_count * self.std_ruang['kamar_mandi']['ideal']})
        
        if jumlah_mobil > 0:
            kebutuhan.append({"Ruang": "Garasi/Carport", "Jml": jumlah_mobil, "Luas": jumlah_mobil * self.std_ruang['garasi_mobil']['min']})

        df = pd.DataFrame(kebutuhan)
        total_fungsi = df['Luas'].sum()
        sirkulasi = total_fungsi * 0.20
        grand_total = total_fungsi + sirkulasi
        
        kdb_max = luas_lahan * 0.6
        status_kdb = "✅ AMAN (Sesuai Regulasi)" if grand_total <= kdb_max else "⚠️ OVER KDB (Perlu Naik Lantai)"
        
        luas_sisa = luas_lahan - grand_total
        rth_persen = (luas_sisa / luas_lahan) * 100 if luas_lahan > 0 else 0
        status_rth = "🌿 MEMENUHI SYARAT GREEN (>30%)" if rth_persen >= 30 else "❌ RTH KURANG"

        return {
            "Detail_Ruang": df,
            "Total_Luas_Bangunan_m2": round(grand_total, 2),
            "Status_KDB": status_kdb,
            "RTH_Aktual_%": round(rth_persen, 2),
            "Status_RTH": status_rth
        }

    # ==========================================
    # 3. JEJAK KARBON & OTTV FASAD
    # ==========================================
    def hitung_jejak_karbon_struktur(self, vol_beton_m3, berat_baja_kg):
        """Menghitung Embodied Carbon dan kompensasi penanaman pohon."""
        berat_baja_ton = berat_baja_kg / 1000
        emisi_beton = vol_beton_m3 * self.co2_factor["beton"]
        emisi_baja = berat_baja_ton * self.co2_factor["baja"]
        total_emisi = emisi_beton + emisi_baja
        kompensasi_pohon = total_emisi / 22 # 22 kg CO2 diserap 1 pohon/tahun
        
        return {
            "Total_Emisi_kgCO2": round(total_emisi, 2),
            "Kompensasi_Pohon_Dibutuhkan": round(kompensasi_pohon),
            "Status": "✅ Audit Carbon Footprint Selesai"
        }

    def hitung_ottv_sederhana(self, luas_dinding_luar, persentase_kaca_wwr):
        """Estimasi OTTV Fasad (Batas SNI: 35 Watt/m2)."""
        u_value_dinding = 2.5 
        sc_kaca = 0.8
        wwr = persentase_kaca_wwr / 100 
        ottv = (u_value_dinding * (1 - wwr) * 5) + (130 * wwr * sc_kaca)
        
        return {
            "Nilai_OTTV_W_m2": round(ottv, 2),
            "Status_SNI": "✅ LULUS (<35 W/m2)" if ottv <= 35 else "❌ GAGAL (Boros Energi AC)"
        }
