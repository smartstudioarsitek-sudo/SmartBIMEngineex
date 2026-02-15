class Zoning_Analyzer:
    def __init__(self):
        pass

    def cek_intensitas_bangunan(self, luas_lahan, luas_lantai_total, luas_dasar, zona="R-1"):
        """
        Cek apakah desain melanggar aturan kota (KDB/KLB).
        R-1: Rumah Kepadatan Rendah (KDB 60%, KLB 1.2)
        """
        rules = {
            "R-1": {"KDB": 60, "KLB": 1.2, "RTH": 30},
            "R-2": {"KDB": 70, "KLB": 2.0, "RTH": 20},
            "K-1": {"KDB": 80, "KLB": 4.0, "RTH": 10} # Komersial
        }
        
        rule = rules.get(zona, rules["R-1"])
        
        # Hitung Realisasi
        kdb_real = (luas_dasar / luas_lahan) * 100
        klb_real = (luas_lantai_total / luas_lahan)
        rth_real = 100 - kdb_real # Sisa lahan untuk hijau & perkerasan
        
        hasil = []
        hasil.append(f"Zonasi: {zona}")
        hasil.append(f"1. KDB (Maks {rule['KDB']}%): Realisasi {kdb_real:.1f}% -> {'✅ LULUS' if kdb_real <= rule['KDB'] else '❌ MELANGGAR'}")
        hasil.append(f"2. KLB (Maks {rule['KLB']}): Realisasi {klb_real:.1f} -> {'✅ LULUS' if klb_real <= rule['KLB'] else '❌ MELANGGAR'}")
        hasil.append(f"3. RTH (Min {rule['RTH']}%): Potensi {rth_real:.1f}% -> {'✅ LULUS' if rth_real >= rule['RTH'] else '⚠️ KRITIS'}")
        
        return "\n".join(hasil)

    def hitung_potensi_harga_lahan(self, luas_lahan, njop_meter, harga_pasar_meter):
        """
        Analisis Investasi Properti sederhana
        """
        nilai_njop = luas_lahan * njop_meter
        nilai_pasar = luas_lahan * harga_pasar_meter
        return {
            "Nilai Aset (NJOP)": f"Rp {nilai_njop:,.0f}",
            "Nilai Pasar Estimasi": f"Rp {nilai_pasar:,.0f}",
            "Gap Profit": f"{(nilai_pasar - nilai_njop)/nilai_njop * 100:.1f}%"
        }