# ==============================================================================
# 📄 NAMA FILE: libs_mep.py
# 📍 LOKASI: modules/mep/libs_mep.py
# 🛠️ FUNGSI: Mechanical, Electrical & Plumbing (MEP) Engine - SNI Standard
# ==============================================================================

import math
import pandas as pd

class MEP_Engine:
    def __init__(self):
        self.engine_name = "SmartBIM MEP Engine (SNI Compliant)"
        
        # 1. Standar Pencahayaan SNI 03-6197-2011 (Lux)
        self.std_lux = {
            "Ruang Kelas": 250,
            "Kantor / Ruang Kerja": 350,
            "Ruang Rapat": 300,
            "Koridor / Lobi": 100,
            "Toilet": 100,
            "Gudang": 50,
            "Kamar Tidur (Residensial)": 150
        }

        # 2. Standar Kebutuhan Air Bersih SNI 03-7065-2005 (Liter/Orang/Hari)
        self.std_air = {
            "Sekolah": 50,
            "Kantor": 50,
            "Perumahan (Mewah)": 250,
            "Perumahan (Menengah)": 150,
            "Masjid / Tempat Ibadah": 15,
            "Rumah Sakit": 500
        }

    # ==========================================
    # 1. MECHANICAL (HVAC / BEBAN PENDINGIN)
    # ==========================================
    def hitung_kebutuhan_ac(self, panjang, lebar, tinggi, fungsi_ruang, jumlah_orang, terpapar_sinar_matahari=False):
        """
        Menghitung beban pendingin (Cooling Load) ruangan dalam BTU/hr 
        dan merekomendasikan kapasitas AC (PK).
        """
        luas_m2 = panjang * lebar
        volume_m3 = luas_m2 * tinggi
        
        # Faktor Beban Termal Iklim Tropis (BTU/hr per m3)
        faktor_ruang = 250 if fungsi_ruang in ["Gudang", "Koridor / Lobi", "Toilet"] else 350
        
        # Penambahan beban jika dinding terpapar sinar matahari langsung (Simplified OTTV)
        if terpapar_sinar_matahari:
            faktor_ruang += 50 
            
        beban_ruang_btu = volume_m3 * faktor_ruang
        
        # Beban kalor manusia (Estimasi 400 BTU/hr per orang aktif)
        beban_orang_btu = jumlah_orang * 400 
        
        total_btu = beban_ruang_btu + beban_orang_btu
        
        # Konversi BTU/hr ke Daya Kuda (PK / Paardekracht) -> 1 PK ~ 9000 BTU/hr
        estimasi_pk = total_btu / 9000.0
        
        # Pembulatan PK ke ukuran standar pabrikan
        standar_pk = [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
        pk_rekomendasi = min(standar_pk, key=lambda x: abs(x - estimasi_pk) if x >= estimasi_pk else float('inf'))

        return {
            "Luas_Ruangan_m2": round(luas_m2, 2),
            "Total_Beban_Pendingin_BTU": round(total_btu, 2),
            "Kapasitas_AC_Rekomendasi_PK": pk_rekomendasi,
            "Jumlah_Unit_Estimasi": math.ceil(estimasi_pk / pk_rekomendasi) if estimasi_pk > 5.0 else 1,
            "Status": "✅ Dihitung berdasarkan beban termal tropis dan kalor manusia."
        }

    # ==========================================
    # 2. ELECTRICAL (PENCAHAYAAN / LIGHTING)
    # ==========================================
    def hitung_titik_lampu(self, panjang, lebar, fungsi_ruang, lumen_per_watt=100, watt_lampu=15):
        """
        Menghitung kebutuhan titik lampu LED berdasarkan standar Lux SNI 03-6197-2011.
        Metode: Lumen Method (Simplified)
        """
        luas_m2 = panjang * lebar
        target_lux = self.std_lux.get(fungsi_ruang, 200) # Default 200 Lux jika tidak ada di daftar
        
        # Rumus Dasar: Total Lumen yang dibutuhkan ke bidang kerja
        # Total_Lumen = (Area * Target_Lux) / (CU * LLF)
        # Asumsi CU (Coefficient of Utilization) = 0.6, LLF (Light Loss Factor) = 0.8
        cu = 0.6
        llf = 0.8
        
        total_lumen_dibutuhkan = (luas_m2 * target_lux) / (cu * llf)
        
        # Kapasitas 1 unit lampu
        lumen_1_lampu = lumen_per_watt * watt_lampu
        
        # Jumlah lampu yang dibutuhkan
        jumlah_lampu = math.ceil(total_lumen_dibutuhkan / lumen_1_lampu)
        
        return {
            "Fungsi_Ruang": fungsi_ruang,
            "Target_Pencahayaan_Lux": target_lux,
            "Lampu_Rekomendasi": f"LED {watt_lampu} Watt",
            "Jumlah_Titik_Lampu": jumlah_lampu,
            "Status": "✅ Dihitung berdasarkan SNI 03-6197-2011."
        }

    # ==========================================
    # 3. PLUMBING (AIR BERSIH & DIAMETER PIPA)
    # ==========================================
    def hitung_pipa_air_bersih(self, fungsi_gedung, jumlah_penghuni, kecepatan_aliran_m_s=1.5):
        """
        Menghitung dimensi pipa utama (Main Pipe) berdasarkan kebutuhan air harian (SNI 03-7065-2005).
        """
        kebutuhan_per_orang = self.std_air.get(fungsi_gedung, 100)
        kebutuhan_harian_liter = kebutuhan_per_orang * jumlah_penghuni
        
        # Konversi ke Debit Puncak / Peak Flow (Q)
        # Asumsi pemakaian puncak terjadi selama 4 jam aktif (14400 detik)
        debit_puncak_liter_detik = kebutuhan_harian_liter / 14400.0
        debit_puncak_m3_detik = debit_puncak_liter_detik / 1000.0
        
        # Menghitung Luas Penampang Pipa (A) dengan rumus Kontinuitas: Q = A * v
        luas_penampang_A = debit_puncak_m3_detik / kecepatan_aliran_m_s
        
        # Menghitung Diameter (D) dalam meter, lalu konversi ke Inci
        # Rumus A = (pi/4) * D^2  -->  D = sqrt((4 * A) / pi)
        diameter_meter = math.sqrt((4 * luas_penampang_A) / math.pi)
        diameter_inci = diameter_meter * 39.3701
        
        # Normalisasi ke ukuran pipa PVC pasaran (Inci)
        ukuran_pasar_inci = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0]
        diameter_final = min([x for x in ukuran_pasar_inci if x >= diameter_inci], default=6.0)
        
        return {
            "Total_Kebutuhan_Harian_Liter": round(kebutuhan_harian_liter, 2),
            "Debit_Puncak_L_s": round(debit_puncak_liter_detik, 2),
            "Diameter_Pipa_Utama_Inci": diameter_final,
            "Status": "✅ Dihitung berdasarkan Kontinuitas Hidraulika & SNI 03-7065-2005."
        }