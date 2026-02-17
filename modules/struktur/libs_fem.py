import openseespy.opensees as ops
import numpy as np
import pandas as pd

class OpenSeesEngine:
    """
    ENGINEER LEVEL: HARDCORE FINITE ELEMENT METHOD
    Menggunakan OpenSeesPy untuk analisis struktur tahan gempa.
    Fokus: Modal Analysis (Eigenvalue) untuk SNI 1726:2019.
    """
    
    def __init__(self):
        # 1. Inisialisasi Model 3D, 6 DOF per node
        ops.wipe()
        ops.model('basic', '-ndm', 3, '-ndf', 6)
        self.node_map = {}
        self.elem_map = {}
        
    def create_material_beton(self, fc):
        """
        Mendefinisikan material beton elastis (Simplified untuk Modal Analysis).
        Untuk analisis nonlinear (Pushover), nanti kita upgrade ke Concrete02.
        """
        E_c = 4700 * np.sqrt(fc) # MPa (SNI 2847)
        # Konversi ke kPa jika input beban dalam kN dan m
        E_c_kpa = E_c * 1000 
        
        # Material ID 1: Elastic Isotropic
        # E, nu (Poisson ratio beton ~0.2)
        ops.nDMaterial('ElasticIsotropic', 1, E_c_kpa, 0.2)
        return E_c_kpa

    def build_simple_portal(self, bentang_x, bentang_y, tinggi_lantai, jumlah_lantai, fc=25):
        """
        GENERATOR MODEL PORTAL 3D OTOMATIS
        Membuat struktur 'Stick Model' sederhana untuk tes analisis gempa.
        """
        self.create_material_beton(fc)
        
        # Parameter Penampang (Asumsi Balok/Kolom 40x40 cm)
        A = 0.4 * 0.4
        Iz = (1/12) * 0.4 * (0.4**3)
        Iy = (1/12) * 0.4 * (0.4**3)
        J = (1/144) * 0.4 * (0.4**3) # Torsi aproksimasi
        
        # Transformasi Koordinat (Linear)
        ops.geomTransf('Linear', 1, 0, 0, 1) # Kolom
        ops.geomTransf('Linear', 2, 0, 1, 0) # Balok Arah X
        
        node_id = 1
        z_curr = 0.0
        
        # --- 1. BUAT NODES & MASSA ---
        # Pola: Grid sederhana 4 kolom (persegi) naik ke atas
        # Node Dasar (Jepit)
        base_nodes = []
        floor_nodes = {} # Key: Lantai, Val: List Node ID
        
        # Koordinat Dasar (0,0), (X,0), (X,Y), (0,Y)
        coords = [(0,0), (bentang_x,0), (bentang_x,bentang_y), (0,bentang_y)]
        
        for i, (x, y) in enumerate(coords):
            ops.node(node_id, x, y, 0.0)
            ops.fix(node_id, 1, 1, 1, 1, 1, 1) # Jepit Sempurna (6 DOF fix)
            base_nodes.append(node_id)
            node_id += 1
            
        # Node Lantai Atas
        for fl in range(1, jumlah_lantai + 1):
            z_curr += tinggi_lantai
            floor_nodes[fl] = []
            
            for i, (x, y) in enumerate(coords):
                ops.node(node_id, x, y, z_curr)
                
                # ASSIGN MASSA (PENTING UNTUK GEMPA!)
                # Asumsi Beban Mati DL = 5 kN/m2 (Pelat+Finishing)
                # Area Tributari per kolom approx = (bentang_x/2 * bentang_y/2)
                trib_area = (bentang_x/2) * (bentang_y/2) * 4 # Simplifikasi total lantai bagi 4
                mass_val = (5.0 * trib_area) / 9.81 # Massa = Berat / Gravitasi
                
                # Massa geser arah X, Y, dan Rotasi (abaikan vertikal untuk eigen simple)
                ops.mass(node_id, mass_val, mass_val, 0.0, 0.0, 0.0, 0.0)
                
                floor_nodes[fl].append(node_id)
                
                # Buat Elemen Kolom (Dari bawah ke atas)
                lower_node = base_nodes[i] if fl == 1 else floor_nodes[fl-1][i]
                
                # elasticBeamColumn(eleTag, iNode, jNode, A, E, G, J, Iy, Iz, transfTag)
                # G (Shear Modulus) approx E/2.4
                E_val = 4700 * np.sqrt(fc) * 1000
                G_val = E_val / 2.4
                
                ops.element('elasticBeamColumn', node_id*100+i, lower_node, node_id, A, E_val, G_val, J, Iy, Iz, 1)
                
                node_id += 1
                
            # Buat Elemen Balok (Keliling Lantai)
            # Simplifikasi: Menghubungkan 4 node keliling
            fns = floor_nodes[fl]
            # 0-1, 1-2, 2-3, 3-0
            beam_conns = [(0,1), (1,2), (2,3), (3,0)]
            for bi, (start, end) in enumerate(beam_conns):
                n1 = fns[start]
                n2 = fns[end]
                ops.element('elasticBeamColumn', node_id*200+bi, n1, n2, A, E_val, G_val, J, Iy, Iz, 2)

    def run_modal_analysis(self, num_modes=3):
        """
        EKSEKUSI EIGENVALUE ANALYSIS
        Menghitung Perioda (T) dan Frekuensi (f).
        Sesuai SNI 1726:2019.
        """
        # Hitung Eigenvalue (Omega Kuadrat)
        eigen_values = ops.eigen(num_modes)
        
        results = []
        for i, val in enumerate(eigen_values):
            if val < 0: val = 0
            omega = np.sqrt(val)
            T = (2 * np.pi) / omega # Perioda (Detik)
            f = 1 / T               # Frekuensi (Hz)
            
            results.append({
                "Mode": i + 1,
                "Period (T) [detik]": round(T, 4),
                "Frequency (f) [Hz]": round(f, 4),
                "Omega (rad/s)": round(omega, 4)
            })
            
        return pd.DataFrame(results)

    def get_mass_participation(self):
        """
        Menghitung Partisipasi Massa (Advanced).
        Memastikan ragam yang diambil cukup (>90%).
        Catatan: OpenSeesPy native tidak punya output tabel langsung, 
        perlu hitungan manual vektor eigen * massa.
        (Disederhanakan untuk tahap ini: return modal analysis dulu).
        """
        # Placeholder untuk pengembangan tahap selanjutnya
        return "Fitur Partisipasi Massa akan aktif di Fase 2."

# --- TESTING BLOCK (Agar bisa di-run terpisah untuk debug) ---
if __name__ == "__main__":
    fem = OpenSeesEngine()
    # Buat Gedung 5 Lantai, Bentang 6x6 meter
    fem.build_simple_portal(6, 6, 3.5, 5)
    df = fem.run_modal_analysis()
    print("--- HASIL ANALISIS OPEN SEES ---")
    print(df)
