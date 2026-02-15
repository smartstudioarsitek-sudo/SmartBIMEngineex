import math

class SNI_Concrete_2019:
    def __init__(self, fc, fy):
        self.fc = float(fc)
        self.fy = float(fy)
        self.Es = 200000 # Modulus elastisitas baja (MPa)

    def hitung_phi_lentur(self, epsilon_t):
        """
        Menghitung Faktor Reduksi Kekuatan (Phi) sesuai SNI 2847:2019 Pasal 21.2.
        Reviewer Note: Menggantikan logika 'Toggle' kaku dengan Interpolasi Linear.
        """
        epsilon_ty = self.fy / self.Es # Regangan leleh (biasanya 0.002)
        epsilon_limit = 0.005          # Batas terkontrol tarik
        
        trace_msg = ""
        
        # KASUS 1: Terkontrol Tekan (Kolom)
        if epsilon_t <= epsilon_ty:
            phi = 0.65 # Asumsi sengkang ikat (bukan spiral)
            trace_msg = f"Terkontrol Tekan (eps_t {epsilon_t:.4f} <= {epsilon_ty:.4f}) -> Phi = 0.65"
            
        # KASUS 2: Terkontrol Tarik (Balok)
        elif epsilon_t >= epsilon_limit:
            phi = 0.90
            trace_msg = f"Terkontrol Tarik (eps_t {epsilon_t:.4f} >= 0.005) -> Phi = 0.90"
            
        # KASUS 3: Zona Transisi (Interpolasi Linear)
        else:
            # Rumus Interpolasi: 0.65 + (eps - eps_ty) * (0.25 / (0.005 - eps_ty))
            phi = 0.65 + (epsilon_t - epsilon_ty) * (0.25 / (epsilon_limit - epsilon_ty))
            trace_msg = f"Zona Transisi (Interpolasi) -> Phi = {phi:.3f}"
            
        return phi, trace_msg

    def hitung_geser_beton_vc(self, bw, d, Av_terpasang=0, Nu=0, Ag=0):
        """
        Menghitung Kuat Geser Beton (Vc) sesuai SNI 2847:2019 Pasal 22.5.5.
        Reviewer Note: WAJIB memperhitungkan Size Effect Factor (lambda_s).
        """
        # 1. Tentukan Lambda_s (Size Effect Factor)
        # Jika ada tulangan geser (Av > Av_min), size effect tidak berlaku (lambda_s = 1.0)
        # Tapi untuk Pondasi/Plat tanpa sengkang, lambda_s HARUS dihitung.
        
        trace = []
        
        if Av_terpasang > 0:
            lambda_s = 1.0
            trace.append("Ada tulangan geser -> Lambda_s = 1.0")
        else:
            # Rumus Size Effect: sqrt(2 / (1 + 0.004*d))
            # d dalam mm
            val = 2.0 / (1.0 + 0.004 * d)
            lambda_s = math.sqrt(val)
            
            # Lambda_s maksimal 1.0
            if lambda_s > 1.0: lambda_s = 1.0
            
            trace.append(f"Tanpa tulangan geser (Size Effect) -> Lambda_s = sqrt(2/(1+0.004*{d})) = {lambda_s:.3f}")

        # 2. Rumus Vc (Simplified SNI 2847:2019 Tabel 22.5.5.1)
        # Vc = 0.17 * lambda_s * sqrt(fc) * bw * d
        # (Dalam N)
        
        vc_nominal = 0.17 * lambda_s * math.sqrt(self.fc) * bw * d
        trace.append(f"Vc Dasar = 0.17 * {lambda_s:.2f} * sqrt({self.fc}) * {bw} * {d} = {vc_nominal/1000:.2f} kN")
        
        # 3. Koreksi Gaya Aksial (Nu) jika ada (Misal Kolom Tekan)
        if Nu > 0 and Ag > 0:
            # Nu dalam Newton
            faktor_nu = Nu / (6 * Ag)
            penambahan = faktor_nu * bw * d
            vc_nominal += penambahan
            trace.append(f"Koreksi Aksial Nu -> Tambah {penambahan/1000:.2f} kN")
            
        return vc_nominal, lambda_s, " | ".join(trace)

    def hitung_tulangan_perlu(self, Mu, d, b):
        """
        Helper sederhana untuk hitung AS perlu (Lentur)
        """
        # Konversi satuan ke N.mm
        Mu_nmm = Mu * 1e6
        
        # Asumsi phi awal 0.9 (nanti dikoreksi iterasi di level app)
        phi = 0.9 
        
        # a asumsi awal 20% d
        a = 0.2 * d
        
        # As = Mu / (phi * fy * (d - a/2))
        As = Mu_nmm / (phi * self.fy * (d - a/2))
        
        return As
