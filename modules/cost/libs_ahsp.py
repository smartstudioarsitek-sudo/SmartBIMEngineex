import pandas as pd

class AHSP_Engine:
    def __init__(self):
        # ======================================================
        # DATABASE AHSP SE DIRJEN BINA KONSTRUKSI NO. 30/2025
        # DIPARTISI MENJADI 3 BIDANG UTAMA
        # ======================================================

        # 1. BIDANG CIPTA KARYA (GEDUNG & PERMUKIMAN)
        self.koefisien_ck = {
            "galian_tanah_manual": {
                "desc": "[CK-Gedung] 1 m3 Galian Tanah Biasa Kedalaman 1 m",
                "bahan": {}, 
                "upah": {"Pekerja": 0.750, "Mandor": 0.025}
            },
            "beton_k300": {
                "desc": "[CK-Gedung] 1 m3 Membuat Beton Mutu f’c = 26,4 MPa (K 300)",
                "bahan": {"Semen (kg)": 413, "Pasir (m3)": 0.48, "Split (m3)": 0.77},
                "upah": {"Pekerja": 1.65, "Tukang": 0.275, "Mandor": 0.083}
            }
            # ... (Silakan tambahkan data CK lainnya di sini) ...
        }

        # 2. BIDANG BINA MARGA (JALAN & JEMBATAN)
        self.koefisien_bm = {
            "galian_tanah_alat": {
                "desc": "[BM-Jalan] 1 m3 Galian Biasa (Alat Berat)",
                "bahan": {"Sewa Excavator (Jam)": 0.056, "Sewa Dump Truck (Jam)": 0.092},
                "upah": {"Pekerja": 0.014, "Mandor": 0.005}
            },
            "beton_k300": {
                "desc": "[BM-Jembatan] 1 m3 Beton Struktur fc' 25 MPa (K-300)",
                "bahan": {"Semen (kg)": 400, "Pasir (m3)": 0.45, "Split (m3)": 0.75},
                "upah": {"Pekerja": 1.20, "Tukang": 0.20, "Mandor": 0.05} # Upah BM biasanya lebih kecil karena dominan alat
            }
        }

        # 3. BIDANG SUMBER DAYA AIR (IRIGASI, BENDUNG, JIAT)
        self.koefisien_sda = {
            "galian_tanah_manual": {
                "desc": "[SDA-Irigasi] 1 m3 Galian Tanah Biasa (Saluran)",
                "bahan": {},
                "upah": {"Pekerja": 0.526, "Mandor": 0.052}
            },
            "beton_k225": {
                "desc": "[SDA-Bendung] 1 m3 Beton Mutu fc' = 19,3 MPa (K 225)",
                "bahan": {"Semen (kg)": 371, "Pasir (m3)": 0.498, "Split (m3)": 0.77},
                "upah": {"Pekerja": 1.50, "Tukang": 0.25, "Mandor": 0.075}
            }
        }

        # Satukan semua resep aktif untuk fallback parser (agar tidak error di file app_enginex.py tab RAB)
        self.koefisien = {**self.koefisien_ck, **self.koefisien_bm, **self.koefisien_sda}

    def hitung_hsp(self, kode_analisa, harga_bahan_dasar, harga_upah_dasar, bidang="Cipta Karya"):
        """
        Kecerdasan Pemilihan Koefisien berdasarkan Bidang Proyek
        """
        # Pilih partisi database sesuai input bidang dari sidebar Streamlit
        if bidang == "Bina Marga":
            db_aktif = self.koefisien_bm
        elif bidang == "Sumber Daya Air":
            db_aktif = self.koefisien_sda
        else:
            db_aktif = self.koefisien_ck

        # Fallback Logic: Cari kecocokan kata terdekat di DB aktif
        target_kode = kode_analisa
        if kode_analisa not in db_aktif: 
            for key in db_aktif.keys():
                if key.split('_')[0] in kode_analisa:
                    target_kode = key
                    break
            if target_kode not in db_aktif: return 0 # Nyerah jika tidak ada yang mirip
            
        data = db_aktif[target_kode]
        total_bahan = 0
        total_upah = 0
        
        for item, koef in data['bahan'].items():
            key_clean = item.split(" (")[0].lower()
            h_satuan = 0
            if "semen" in key_clean: h_satuan = harga_bahan_dasar.get('semen', 0)
            elif "pasir" in key_clean: h_satuan = harga_bahan_dasar.get('pasir', 0)
            elif "split" in key_clean: h_satuan = harga_bahan_dasar.get('split', 0)
            elif "excavator" in key_clean: h_satuan = harga_bahan_dasar.get('excavator', 500000)
            total_bahan += koef * h_satuan
            
        for item, koef in data['upah'].items():
            h_upah = harga_upah_dasar.get(item.lower(), 0)
            total_upah += koef * h_upah
            
        return total_bahan + total_upah
