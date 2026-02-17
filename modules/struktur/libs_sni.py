import math

class SNI_Concrete_2019:
    """
    Engine Perhitungan Struktur Beton Bertulang.
    Referensi: SNI 2847:2019 (ACI 318-19).
    Fokus Audit: Penerapan Size Effect Factor (Lambda_s) yang presisi.
    """
    
    def __init__(self, fc, fy):
        """
        Inisialisasi Material.
        Args:
            fc (float): Kuat tekan beton (MPa)
            fy (float): Kuat leleh baja tulangan (MPa)
        """
        # Validasi input material tidak boleh negatif/nol
        self.fc = float(fc) if float(fc) > 0 else 25.0
        self.fy = float(fy) if float(fy) > 0 else 400.0
        self.Es = 200000.0 # Modulus elastisitas baja (MPa)

    def hitung_phi_lentur(self, epsilon_t):
        """
        Menghitung Faktor Reduksi Kekuatan (Phi) - Pasal 21.2.
        Logika Interpolasi Linear untuk Zona Transisi.
        """
        epsilon_ty = self.fy / self.Es # Regangan leleh (biasanya 0.002)
        epsilon_limit = 0.005          # Batas terkontrol tarik
        
        trace_msg = ""
        phi = 0.65 # Default awal (Terkontrol Tekan)
        
        # KASUS 1: Terkontrol Tekan (Kolom/Pondasi beban sentris)
        if epsilon_t <= epsilon_ty:
            phi = 0.65 
            trace_msg = f"Terkontrol Tekan (eps_t {epsilon_t:.5f} <= {epsilon_ty:.5f}) -> Phi = 0.65"
            
        # KASUS 2: Terkontrol Tarik (Balok Lentur Murni)
        elif epsilon_t >= epsilon_limit:
            phi = 0.90
            trace_msg = f"Terkontrol Tarik (eps_t {epsilon_t:.5f} >= 0.005) -> Phi = 0.90"
            
        # KASUS 3: Zona Transisi (Interpolasi Linear)
        else:
            # Rumus Interpolasi SNI Tabel 21.2.2
            phi = 0.65 + (epsilon_t - epsilon_ty) * (0.25 / (epsilon_limit - epsilon_ty))
            trace_msg = f"Zona Transisi (Interpolasi) -> Phi = {phi:.3f}"
            
        return phi, trace_msg

    def hitung_geser_beton_vc(self, bw, d, Av_terpasang=0, Nu=0, Ag=0, As_longitudinal=0):
        """
        Menghitung Kuat Geser Beton (Vc) - SNI 2847:2019 Pasal 22.5.5.
        
        PERUBAHAN AUDIT (CRITICAL):
        1. Implementasi Size Effect (Lambda_s) dengan penyebut 254 mm (Eksak 10 inci).
        2. Penggunaan Rho_w (Rasio Tulangan Memanjang) untuk rumus detail.
        
        Args:
            bw (float): Lebar badan (mm)
            d (float): Tinggi efektif (mm)
            Av_terpasang (float): Luas tulangan geser per jarak s (mm2). Jika 0 = Tanpa Sengkang.
            Nu (float): Gaya aksial (N). (+) Tekan, (-) Tarik.
            Ag (float): Luas bruto penampang (mm2).
            As_longitudinal (float): Luas tulangan tarik lentur (mm2).
        """
        trace = []
        lambda_conc = 1.0 # Faktor beton ringan (1.0 untuk beton normal)
        
        # Validasi Dimensi Geometri
        if bw <= 0 or d <= 0:
            return 0.0, 1.0, "Error: Dimensi bw atau d tidak valid (<=0)"

        # ---------------------------------------------------------
        # LANGKAH 1: KOREKSI GAYA AKSIAL (Nu)
        # ---------------------------------------------------------
        # Nu Positif = Tekan (Menambah Vc), Nu Negatif = Tarik (Mengurangi Vc)
        axial_term = 0.0
        
        if Ag > 0:
            val_nu_6ag = Nu / (6 * Ag)
            
            if Nu > 0: # Tekan
                # SNI membatasi kontribusi tekan maks 0.05*fc
                limit_axial = 0.05 * self.fc
                axial_term = min(val_nu_6ag, limit_axial)
                trace.append(f"Aksial Tekan (Nu={Nu/1000:.1f} kN): Menambah Vc sebesar {axial_term:.2f} MPa")
            elif Nu < 0: # Tarik
                # Tidak ada limit bawah untuk tarik, bisa mengurangi Vc sampai 0
                axial_term = val_nu_6ag
                trace.append(f"Aksial Tarik (Nu={Nu/1000:.1f} kN): Mengurangi Vc sebesar {axial_term:.2f} MPa")

        # ---------------------------------------------------------
        # LANGKAH 2: HITUNG SIZE EFFECT (Lambda_s)
        # ---------------------------------------------------------
        # Rumus SNI/ACI: sqrt(2 / (1 + d_inch/10))
        # KONVERSI PRESISI: 10 inci = 254 mm (BUKAN 250 mm)
        
        const_denominator = 254.0 
        val_under_sqrt = 2.0 / (1.0 + (d / const_denominator))
        lambda_s = math.sqrt(val_under_sqrt)
        
        # Lambda_s tidak boleh lebih dari 1.0
        if lambda_s > 1.0: lambda_s = 1.0
        
        # ---------------------------------------------------------
        # LANGKAH 3: LOGIKA PEMILIHAN RUMUS (TABEL 22.5.5.1)
        # ---------------------------------------------------------
        has_stirrups = Av_terpasang > 0 # Apakah ada sengkang?
        
        vc_val = 0.0
        
        # KASUS A: ADA SENGKANG MINIMUM (Size Effect Diabaikan)
        if has_stirrups:
            # Lambda_s dipaksa jadi 1.0 karena sengkang menahan retak
            effective_lambda_s = 1.0 
            
            # Rumus (a): 0.17 * lambda * sqrt(fc)
            base_vc = 0.17 * lambda_conc * math.sqrt(self.fc)
            vc_val = (base_vc + axial_term) * bw * d
            
            trace.append("Metode: Tabel 22.5.5.1 (a) - Dengan Sengkang (Size Effect Diabaikan)")
            
        # KASUS B: TANPA SENGKANG (Size Effect Berlaku Penuh)
        else:
            effective_lambda_s = lambda_s
            
            # Hitung Rho_w (Rasio Tulangan)
            rho_w = As_longitudinal / (bw * d)
            
            # Validasi Rho_w (Tidak boleh 0 untuk rumus c)
            if rho_w > 0:
                # Rumus (c) - Rumus Detail SNI 2019
                # Vc = (0.66 * lambda_s * (rho_w)^(1/3) * sqrt(fc) + Nu/6Ag) * bw * d
                
                term_rho = math.pow(rho_w, 1/3) # Pangkat sepertiga
                base_vc = 0.66 * effective_lambda_s * term_rho * lambda_conc * math.sqrt(self.fc)
                vc_val = (base_vc + axial_term) * bw * d
                
                trace.append(f"Metode: Tabel 22.5.5.1 (c) - Strict SNI (Size Effect Aktif).")
                trace.append(f"Detail: d={d:.0f}mm -> Lambda_s={effective_lambda_s:.3f}, Rho_w={rho_w:.4f}")
                
            else:
                # Fallback jika user lupa input As (Rho=0)
                # Menggunakan rumus estimasi (0.17) TAPI dikalikan Lambda_s
                # Vc = (0.17 * lambda_s * sqrt(fc))
                base_vc = 0.17 * effective_lambda_s * lambda_conc * math.sqrt(self.fc)
                vc_val = (base_vc + axial_term) * bw * d
                
                trace.append(f"⚠️ WARNING: As_longitudinal = 0. Menggunakan rumus (a) termodifikasi Lambda_s.")
                trace.append(f"Detail: Lambda_s={effective_lambda_s:.3f}")

        # Safety Check Akhir: Vc tidak boleh negatif
        if vc_val < 0: 
            vc_val = 0
            trace.append("Result: Vc negatif akibat gaya tarik besar -> Diambil 0")

        return vc_val, lambda_s, " | ".join(trace)

    def hitung_tulangan_perlu(self, Mu, d, b):
        """
        Helper Estimasi Tulangan Lentur (Preliminary Design).
        Output: As perlu (mm2).
        """
        if d <= 0: return 0
        
        Mu_nmm = Mu * 1e6 # Konversi kNm ke Nmm
        phi = 0.9 # Asumsi awal terkontrol tarik
        
        # Pendekatan Iteratif Sederhana (Blok Tekan Whitney)
        # Asumsi awal a = 0.2 * d
        a = 0.2 * d
        
        # Rumus: As = Mu / (phi * fy * (d - a/2))
        try:
            As = Mu_nmm / (phi * self.fy * (d - a/2))
            
            # Koreksi nilai 'a' berdasarkan As yang didapat
            # a = (As * fy) / (0.85 * fc * b)
            a_recalc = (As * self.fy) / (0.85 * self.fc * b)
            
            # Hitung ulang As dengan 'a' yang lebih presisi
            As_final = Mu_nmm / (phi * self.fy * (d - a_recalc/2))
            
            return As_final
        except ZeroDivisionError:
            return 0.0
            
# [PATCH UPGRADE] libs_sni.py
class SNILoadCombos:
    """
    Generator Kombinasi Pembebanan Berdasarkan SNI 1727:2020
    """
    @staticmethod
    def get_ultimate_combos(DL, LL, E=0, W=0):
        """
        Mengembalikan Dictionary semua kombinasi beban terfaktor (Pu)
        DL: Dead Load, LL: Live Load, E: Earthquake, W: Wind
        """
        combos = {
            "Comb 1 (1.4D)": 1.4 * DL,
            "Comb 2 (1.2D + 1.6L)": (1.2 * DL) + (1.6 * LL),
            "Comb 3 (1.2D + 1.0L + 1.0E)": (1.2 * DL) + (1.0 * LL) + (1.0 * E),
            "Comb 4 (0.9D + 1.0E)": (0.9 * DL) + (1.0 * E), # Cek Guling/Uplift
        }
        return combos

    @staticmethod
    def get_service_combos(DL, LL):
        """Untuk Cek Lendutan (Serviceability)"""
        return {"Service (D + L)": DL + LL}
