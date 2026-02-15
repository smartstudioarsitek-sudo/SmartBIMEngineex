import math

class SNI_Concrete_2019:
    def __init__(self, fc, fy):
        self.fc = float(fc)
        self.fy = float(fy)
        self.Es = 200000.0 # Modulus elastisitas baja (MPa)

    def hitung_phi_lentur(self, epsilon_t):
        """
        Menghitung Faktor Reduksi Kekuatan (Phi) sesuai SNI 2847:2019 Pasal 21.2.
        Menggunakan Interpolasi Linear (bukan Step Function) untuk Zona Transisi.
        """
        epsilon_ty = self.fy / self.Es # Regangan leleh (biasanya 0.002)
        epsilon_limit = 0.005          # Batas terkontrol tarik
        
        trace_msg = ""
        phi = 0.65 # Default awal
        
        # KASUS 1: Terkontrol Tekan (Kolom dengan sengkang ikat)
        if epsilon_t <= epsilon_ty:
            phi = 0.65 
            trace_msg = f"Terkontrol Tekan (eps_t {epsilon_t:.4f} <= {epsilon_ty:.4f}) -> Phi = 0.65"
            
        # KASUS 2: Terkontrol Tarik (Balok murni)
        elif epsilon_t >= epsilon_limit:
            phi = 0.90
            trace_msg = f"Terkontrol Tarik (eps_t {epsilon_t:.4f} >= 0.005) -> Phi = 0.90"
            
        # KASUS 3: Zona Transisi (Interpolasi Linear)
        else:
            # Rumus Interpolasi SNI: 0.65 + (eps - eps_ty) * (0.25 / (0.005 - eps_ty))
            phi = 0.65 + (epsilon_t - epsilon_ty) * (0.25 / (epsilon_limit - epsilon_ty))
            trace_msg = f"Zona Transisi (Interpolasi) -> Phi = {phi:.3f}"
            
        return phi, trace_msg

    def hitung_geser_beton_vc(self, bw, d, Av_terpasang=0, Nu=0, Ag=0):
        """
        Menghitung Kuat Geser Beton (Vc) sesuai SNI 2847:2019 Pasal 22.5.5.
        FITUR WAJIB: Size Effect Factor (Lambda_s) dengan konversi unit yang benar.
        """
        trace = []
        
        # 1. Tentukan Lambda_s (Size Effect Factor)
        # Jika ada tulangan geser (Av > Av_min), size effect tidak berlaku (lambda_s = 1.0)
        if Av_terpasang > 0:
            lambda_s = 1.0
            trace.append("Tulangan Geser Terpasang -> Size Effect Diabaikan (Lambda_s = 1.0)")
        else:
            # --- PERBAIKAN KRUSIAL (AUDIT COMPLIANCE) ---
            # Rumus SNI/ACI aslinya dalam satuan INCI: sqrt(2 / (1 + d_inch/10))
            # Kita bekerja dalam MM. Maka penyebut '10' harus dikonversi ke mm.
            # 10 inci = 254 mm.
            
            pembagi_inci = 254.0 
            
            # Rumus Metrik: sqrt( 2 / (1 + d_mm / 254) )
            val = 2.0 / (1.0 + (d / pembagi_inci))
            lambda_s = math.sqrt(val)
            
            # Clamping: Lambda_s tidak boleh lebih dari 1.0
            if lambda_s > 1.0: lambda_s = 1.0
            
            trace.append(f"Tanpa Sengkang (Size Effect Aktif) -> d={d:.0f}mm")
            trace.append(f"Lambda_s = sqrt(2 / (1 + {d}/254)) = {lambda_s:.3f}")

        # 2. Rumus Vc Dasar (Simplified SNI 2847:2019 Tabel 22.5.5.1)
        # Vc = 0.17 * lambda_s * sqrt(fc) * bw * d
        # (Hasil dalam Newton)
        
        vc_nominal = 0.17 * lambda_s * math.sqrt(self.fc) * bw * d
        trace.append(f"Vc Dasar = 0.17 * {lambda_s:.3f} * sqrt({self.fc}) * {bw} * {d} = {vc_nominal/1000:.2f} kN")
        
        # 3. Koreksi Gaya Aksial (Nu) jika ada (Misal Kolom Tekan)
        if Nu > 0 and Ag > 0:
            # Nu dalam Newton. Rumus: Vc = Vc_dasar * (1 + Nu/(6Ag)) - pendekatan alternatif
            # Atau penambahan kapasitas: 
            penambahan = (Nu / (6 * Ag)) * bw * d
            vc_nominal += penambahan
            trace.append(f"Koreksi Aksial Nu ({Nu/1000:.1f} kN) -> Tambah {penambahan/1000:.2f} kN")
            
        return vc_nominal, lambda_s, " | ".join(trace)

    def hitung_tulangan_perlu(self, Mu, d, b):
        """Helper estimasi AS perlu (Lentur)"""
        Mu_nmm = Mu * 1e6
        phi = 0.9 # Asumsi awal
        a_guess = 0.2 * d # Asumsi blok tekan
        
        # As = Mu / (phi * fy * (d - a/2))
        try:
            As = Mu_nmm / (phi * self.fy * (d - a_guess/2))
        except ZeroDivisionError:
            As = 0
            
        return As
