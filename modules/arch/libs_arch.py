import pandas as pd

class Architect_Engine:
    def __init__(self):
        # Standar Luas Minimum per Orang/Fungsi (berdasarkan Neufert/SNI)
        self.std_ruang = {
            "kamar_tidur_utama": {"min": 12, "ideal": 16, "unit": "m2"},
            "kamar_tidur_anak": {"min": 9, "ideal": 12, "unit": "m2"},
            "kamar_mandi": {"min": 2.5, "ideal": 4, "unit": "m2"},
            "ruang_tamu": {"min": 9, "ideal": 15, "unit": "m2"},
            "ruang_keluarga": {"min": 12, "ideal": 20, "unit": "m2"},
            "dapur": {"min": 6, "ideal": 9, "unit": "m2"},
            "garasi_mobil": {"min": 15, "ideal": 18, "unit": "m2/mobil"},
            "taman": {"min": 0.1, "ideal": 0.3, "unit": "% luas lahan"} # 10-30% RTH
        }

    def generate_program_ruang(self, penghuni, jumlah_mobil, luas_lahan):
        """
        Menghitung Kebutuhan Luas Bangunan berdasarkan jumlah penghuni.
        """
        kebutuhan = []
        total_luas = 0
        
        # 1. Analisa Kamar Tidur
        kt_anak = max(0, penghuni - 2) # Asumsi 2 orang di KT Utama
        kebutuhan.append({"Ruang": "KT Utama", "Jml": 1, "Luas": self.std_ruang['kamar_tidur_utama']['ideal']})
        if kt_anak > 0:
            kebutuhan.append({"Ruang": "KT Anak", "Jml": kt_anak, "Luas": kt_anak * self.std_ruang['kamar_tidur_anak']['ideal']})
            
        # 2. Fasilitas Bersama
        kebutuhan.append({"Ruang": "R. Keluarga", "Jml": 1, "Luas": self.std_ruang['ruang_keluarga']['ideal']})
        kebutuhan.append({"Ruang": "Dapur & Makan", "Jml": 1, "Luas": self.std_ruang['dapur']['ideal'] * 1.5})
        
        # 3. Servis
        km_count = int(penghuni / 3) + 1
        kebutuhan.append({"Ruang": "KM/WC", "Jml": km_count, "Luas": km_count * self.std_ruang['kamar_mandi']['ideal']})
        
        if jumlah_mobil > 0:
            kebutuhan.append({"Ruang": "Garasi/Carport", "Jml": jumlah_mobil, "Luas": jumlah_mobil * self.std_ruang['garasi_mobil']['min']})

        # Hitung Total & Sirkulasi (20%)
        df = pd.DataFrame(kebutuhan)
        total_fungsi = df['Luas'].sum()
        sirkulasi = total_fungsi * 0.20
        grand_total = total_fungsi + sirkulasi
        
        # Cek KDB (Koefisien Dasar Bangunan) - Misal max 60%
        kdb_max = luas_lahan * 0.6
        status_kdb = "AMAN (Sesuai Regulasi)" if grand_total <= kdb_max else "OVER (Melanggar KDB, Perlu Tingkat)"
        
        return {
            "Detail_Ruang": df,
            "Luas_Fungsional": total_fungsi,
            "Sirkulasi_20%": sirkulasi,
            "Total_Luas_Bangunan": grand_total,
            "Status_KDB_60%": f"{grand_total:.1f} m2 vs Max {kdb_max:.1f} m2 -> {status_kdb}"
        }
