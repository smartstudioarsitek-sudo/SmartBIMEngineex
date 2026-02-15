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
