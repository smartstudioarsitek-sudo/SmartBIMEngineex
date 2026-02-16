import math

class SNI_Concrete_2019:
    def __init__(self, fc, fy):
        """
        Inisialisasi Engine Beton SNI 2847:2019.
        Input:
        - fc: Kuat tekan beton (MPa)
        - fy: Kuat leleh baja tulangan (MPa)
        """
        self.fc = float(fc)
        self.fy = float(fy)
        self.Es = 200000.0 # Modulus elastisitas baja (MPa)

    def hitung_phi_lentur(self, epsilon_t):
        """
        Menghitung Faktor Reduksi Kekuatan (Phi) sesuai SNI 2847:2019 Pasal 21.2.
        Menggunakan Interpolasi Linear untuk Zona Transisi.
        """
        epsilon_ty = self.fy / self.Es # Regangan leleh (biasanya 0.002)
        epsilon_limit = 0.005          # Batas terkontrol tarik
        
        trace_msg = ""
        phi = 0.65 # Default awal (Terkontrol Tekan)
        
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

    def hitung_geser_beton_vc(self, bw, d, Av_terpasang=0, Nu=0, Ag=0, As_longitudinal=0):
        """
        Menghitung Kuat Geser Beton (Vc) - SNI 2847:2019 / ACI 318-19.
        FITUR AUDIT: Menggunakan Rho_w untuk akurasi Size Effect.
        
        Input:
        - bw: Lebar badan (mm)
        - d: Tinggi efektif (mm)
        - Av_terpasang: Luas tulangan geser yang ada (jika 0 berarti tanpa sengkang)
        - Nu: Gaya aksial (N). Positif = Tekan, Negatif = Tarik.
        - Ag: Luas bruto penampang (mm2)
        - As_longitudinal: Luas tulangan tarik memanjang (mm2) -> PENTING untuk Size Effect
        """
        trace = []
        lambda_conc = 1.0 # Faktor beton ringan (1.0 untuk beton normal)
        
        # 1. Hitung Term Aksial (Nu/6Ag)
        # Batasan SNI: Term ini tidak boleh lebih dari 0.05 * fc
        axial_term = 0
        if Ag > 0:
            axial_val = Nu / (6 * Ag)
            max_axial = 0.05 * self.fc
            
            # Jika Nu tekan (positif), batasi maks. Jika tarik, biarkan negatif (mengurangi Vc).
            if axial_val > 0:
                axial_term = min(axial_val, max_axial)
            else:
                axial_term = axial_val 
            
            if Nu != 0:
                trace.append(f"Efek Aksial (Nu={Nu/1000:.1f}kN): {axial_term:.2f} MPa")

        # 2. Logic Size Effect & Rho_w (Sesuai Audit Deep Research)
        # Jika ada sengkang min (Av > 0), Size Effect = 1.0 (Diabaikan karena sengkang menahan retak)
        has_stirrups = Av_terpasang > 0 
        
        if has_stirrups:
            lambda_s = 1.0
            # Rumus (a) Tabel 22.5.5.1 SNI 2847:2019
            # Vc = (0.17 * lambda * sqrt(fc) + Nu/6Ag) * bw * d
            vc_val = (0.17 * lambda_conc * math.sqrt(self.fc) + axial_term) * bw * d
            trace.append("Metode: Tabel 22.5.5.1 (a) - Dengan Sengkang (Size Effect Diabaikan)")
            
        else:
            # KASUS TANPA SENGKANG (CRITICAL FOR THICK SLAB/FOOTING)
            # Wajib menghitung Size Effect Lambda_s
            # Rumus: sqrt(2 / (1 + d_mm/254))
            val_d = 2.0 / (1.0 + (d / 254.0))
            lambda_s = math.sqrt(val_d)
            
            # Lambda_s tidak boleh > 1.0
            if lambda_s > 1.0: lambda_s = 1.0
            
            # Hitung Rho_w (Rasio Tulangan Memanjang)
            rho_w = 0
            if bw * d > 0:
                rho_w = As_longitudinal / (bw * d)
            
            # Gunakan Rumus (c) Tabel 22.5.5.1 (Lebih Akurat & Strict SNI)
            # Vc = (0.66 * lambda_s * (rho_w)^(1/3) * sqrt(fc) + Nu/6Ag) * bw * d
            
            # Jika user tidak input As (As=0), kita fallback ke rumus estimasi tapi kasih warning
            if rho_w <= 0:
                # Fallback aman (menggunakan koefisien 0.17 dasar)
                vc_val = (0.17 * lambda_s * lambda_conc * math.sqrt(self.fc) + axial_term) * bw * d
                trace.append(f"⚠️ WARNING: As_longitudinal = 0. Menggunakan rumus estimasi (0.17). Lambda_s={lambda_s:.3f}")
            else:
                term_rho = math.pow(rho_w, 1/3) # Pangkat sepertiga
                vc_val = (0.66 * lambda_s * term_rho * lambda_conc * math.sqrt(self.fc) + axial_term) * bw * d
                trace.append(f"Metode: Tabel 22.5.5.1 (c) - Strict SNI (Size Effect + Rho). Lambda_s={lambda_s:.3f}, Rho={rho_w:.4f}")

        # Safety Check Final: Vc tidak boleh negatif
        if vc_val < 0: vc_val = 0
        
        return vc_val, lambda_s, " | ".join(trace)

    def hitung_tulangan_perlu(self, Mu, d, b):
        """
        Helper untuk mengestimasi Luas Tulangan (As) berdasarkan Momen (Mu).
        Berguna untuk Preliminary Design.
        """
        Mu_nmm = Mu * 1e6 # Konversi kNm ke Nmm
        phi = 0.9 # Asumsi awal terkontrol tarik
        a_guess = 0.2 * d # Asumsi awal tinggi blok tekan beton
        
        try:
            # Rumus Dasar: Mn = As * fy * (d - a/2)
            # Maka As = Mu / (phi * fy * (d - a/2))
            As = Mu_nmm / (phi * self.fy * (d - a_guess/2))
        except ZeroDivisionError:
            As = 0
            
        return As
