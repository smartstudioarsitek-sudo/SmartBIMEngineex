import math

class Bendung_Engine:
    """
    Engine Sederhana untuk Perhitungan Hidrolis Bendung Tetap.
    """
    
    def hitung_lebar_efektif(self, lebar_sungai, n_pilar, lebar_pilar=1.0):
        """
        Menghitung Lebar Efektif Bendung (Be).
        Be = B - 2(n.Kp + Ka)H -> Simplifikasi Be = B - 20%
        """
        # Simplifikasi KP-02: Be diambil 85-90% lebar sungai jika data pilar kurang
        Be = lebar_sungai - (n_pilar * lebar_pilar)
        return max(0, Be)

    def hitung_tinggi_muka_air_banjir(self, Q_banjir, Be, Cd=2.1):
        """
        Menghitung Tinggi Energi (Hd) di atas mercu.
        Rumus Debit Pelimpah: Q = Cd * Be * Hd^1.5
        Maka: Hd = (Q / (Cd * Be)) ^ (2/3)
        """
        if Be <= 0: return 0
        Hd = (Q_banjir / (Cd * Be)) ** (2/3)
        return round(Hd, 3)

    def cek_stabilitas_guling(self, Momen_Tahan, Momen_Guling):
        """
        Cek Safety Factor Guling (Overturning).
        """
        if Momen_Guling == 0: return 99.0
        SF = Momen_Tahan / Momen_Guling
        status = "AMAN" if SF >= 1.5 else "BAHAYA"
        return SF, status

    def penentuan_kolam_olak(self, Froude, Tinggi_Terjun):
        """
        Menentukan Tipe Kolam Olak USBR berdasarkan Bilangan Froude & Head.
        """
        if Froude < 1.7:
            tipe = "Tidak Perlu Kolam Olak (Aliran Subkritis)"
        elif 1.7 <= Froude <= 2.5:
            tipe = "USBR Tipe IV (Baffle Blocks)"
        elif 2.5 < Froude <= 4.5:
            tipe = "USBR Tipe IV (Gigi Ompong)"
        else:
            # Froude > 4.5
            if Tinggi_Terjun > 10:
                tipe = "USBR Tipe II (Bucket)"
            else:
                tipe = "USBR Tipe III (Gigi Ompong)"
        return tipe
    # =========================================
    # ANALISIS REMBESAN & KANTONG LUMPUR (KP-02)
    # =========================================
    def cek_rembesan_lane(self, delta_H, list_Lv, list_Lh, jenis_tanah):
        """
        Menghitung Angka Rembesan Lane (Weighted Creep Ratio) untuk mencegah Piping.
        - delta_H: Beda tinggi muka air hulu dan hilir (m)
        - list_Lv: List panjang rayapan vertikal (m) [cut-off wall, sheet pile]
        - list_Lh: List panjang rayapan horizontal (m) [lantai muka, kolam olak]
        """
        if delta_H <= 0: return {"Status": "Error: Delta H harus > 0"}

        # Total panjang rayapan Lane (Lv utuh, Lh sepertiga)
        Lw = sum(list_Lv) + (sum(list_Lh) / 3.0)
        
        # Angka Rembesan Lane aktual (Cw)
        Cw_aktual = Lw / delta_H
        
        # Referensi Angka Lane Minimum berdasarkan jenis tanah (KP-02)
        lane_min_db = {
            "pasir sangat halus": 8.5,
            "pasir halus": 7.0,
            "pasir sedang": 6.0,
            "pasir kasar": 5.0,
            "kerikil halus": 4.0,
            "kerikil kasar": 3.0,
            "lempung keras": 1.8
        }
        
        cw_izin = lane_min_db.get(jenis_tanah.lower(), 7.0) # Default konservatif ke pasir halus
        
        status = "✅ AMAN dari Piping" if Cw_aktual >= cw_izin else "❌ BAHAYA Piping (Perpanjang Lantai Muka / Tambah Sheetpile)"
        
        return {
            "Panjang_Rayapan_Lane_Lw_m": round(Lw, 2),
            "Angka_Rembesan_Aktual_Cw": round(Cw_aktual, 2),
            "Angka_Rembesan_Izin_Min": cw_izin,
            "Status": status
        }

    def dimensi_kantong_lumpur(self, Q_desain, kecepatan_endap_w=0.04, kecepatan_aliran_v=0.3):
        """
        Desain Kantong Lumpur (Sediment Trap) berdasarkan kecepatan jatuh partikel (w).
        - kecepatan_endap_w: m/s (0.04 m/s umum untuk pasir halus d=0.06mm)
        - kecepatan_aliran_v: m/s (Aliran tenang agar sedimen turun, max 0.4 m/s)
        """
        # Luas permukaan (L x B) yang dibutuhkan agar partikel mengendap
        # B * L = Q / w
        luas_permukaan_min = Q_desain / kecepatan_endap_w
        
        # Luas penampang melintang (A = Q / v)
        A_melintang = Q_desain / kecepatan_aliran_v
        
        # Asumsi kedalaman air (h) efektif di kantong lumpur (standar 1.5 - 2.5m)
        h_efektif = 2.0
        lebar_B = A_melintang / h_efektif
        
        # Panjang kantong lumpur L = Luas Permukaan / Lebar
        panjang_L = luas_permukaan_min / lebar_B
        
        # Tambahkan safety factor panjang 20% untuk turbulensi
        panjang_desain = panjang_L * 1.2
        
        return {
            "Lebar_B_m": round(lebar_B, 2),
            "Kedalaman_Air_h_m": round(h_efektif, 2),
            "Panjang_L_m": round(panjang_desain, 2),
            "Luas_Permukaan_m2": round(luas_permukaan_min, 2)
        }
