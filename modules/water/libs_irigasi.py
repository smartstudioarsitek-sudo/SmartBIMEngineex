import numpy as np
import math
import matplotlib.pyplot as plt

class Irrigation_Engine:
    
    def __init__(self):
        pass

    # =========================================
    # 1. LOGIKA HITUNG DIMENSI
    # =========================================
    def hitung_dimensi_saluran(self, Q, b_ratio=1.5, m=1.0, S=0.0005, n=0.025):
        # Inisialisasi
        h = 0.1
        best_diff = float('inf')
        best_h = 0.1
        
        # Iterasi mencari tinggi air (h)
        while h < 20.0: # Batas iterasi dinaikkan
            b = h * b_ratio 
            A = (b + m * h) * h
            P = b + 2 * h * math.sqrt(1 + m**2)
            
            if P > 0:
                R = A / P
                Q_calc = (1/n) * A * (R**(2/3)) * (S**0.5)
                diff = abs(Q_calc - Q)
                
                if diff < best_diff:
                    best_diff = diff
                    best_h = h
                
                if Q_calc >= Q: 
                    break
            h += 0.05
            
        # Set hasil akhir
        h = best_h
        b = h * b_ratio
        
        # Parameter Final
        A = (b + m * h) * h
        V = Q / A if A > 0 else 0
        T = b + 2 * m * h 
        D = A / T if T > 0 else 0
        Fr = V / math.sqrt(9.81 * D) if D > 0 else 0
        
        # Freeboard
        if Q < 0.5: w = 0.20
        elif Q < 10.0: w = 0.30
        elif Q < 50.0: w = 0.60
        else: w = 0.75
        
        H_total = h + w
        
        status = "AMAN"
        warns = []
        if Fr >= 1.0: status = "BAHAYA"; warns.append("Superkritis")
        if V < 0.6: status = "PERHATIAN"; warns.append("Sedimentasi")
        
        return {
            "Dimensi": {"b": round(b, 2), "h_air": round(h, 2), "H_total": round(H_total, 2), "m": m, "w": w},
            "Hidrolis": {"V": round(V, 2), "Fr": round(Fr, 2), "Area": round(A, 2)},
            "Status": status
        }

    # =========================================
    # [FIX UTAMA] FUNGSI PLOTTING GRAFIK
    # =========================================
    def hitung_dan_gambar_saluran(self, Q, S, n, m):
        """
        Fungsi yang dicari oleh Orkestra AI.
        Mengembalikan Figure (Grafik) dan Info (Dict).
        """
        # 1. Hitung
        hasil = self.hitung_dimensi_saluran(Q, S=S, n=n, m=m)
        dim = hasil['Dimensi']
        b = dim['b']
        h = dim['h_air']
        H = dim['H_total']
        w = dim['w']
        
        # 2. Gambar
        fig, ax = plt.subplots(figsize=(8, 4))
        
        # Koordinat Tanah
        x_tanah = [-b/2 - m*H, -b/2, b/2, b/2 + m*H]
        y_tanah = [H, 0, 0, H]
        ax.plot(x_tanah, y_tanah, 'brown', lw=3, label='Saluran')
        ax.fill_between(x_tanah, y_tanah, -1.0, color='#8B4513', alpha=0.3)
        
        # Koordinat Air
        x_air = [-b/2 - m*h, -b/2, b/2, b/2 + m*h]
        y_air = [h, 0, 0, h]
        ax.plot(x_air, y_air, 'blue', lw=1, linestyle='--')
        ax.fill(x_air, y_air, 'cyan', alpha=0.5, label='Air')
        
        # Label
        ax.text(0, h/2, f"h={h}m", ha='center', color='blue', fontweight='bold')
        ax.text(0, -0.5, f"b={b}m", ha='center', color='brown', fontweight='bold')
        
        ax.set_title(f"Desain Saluran (Q={Q} m3/s)")
        ax.legend(loc='upper right')
        ax.set_aspect('equal')
        ax.grid(True, linestyle=':', alpha=0.5)
        
        return fig, {"b": b, "h": h, "H": H, "w": w}

    # =========================================
    # 3. ALIAS & DXF
    # =========================================
    def hitung_dimensi_ekonomis(self, Q, S, n, m):
        return self.hitung_dimensi_saluran(Q, S=S, n=n, m=m)

    def generate_dxf_script(self, desain_data_or_b, h_total=None, m=None, t=None, filename="out.dxf"):
        # Logic handling input dict/manual
        if isinstance(desain_data_or_b, dict):
            data = desain_data_or_b
            b = data['Dimensi']['b']
            H = data['Dimensi']['H_total']
            h_air = data['Dimensi']['h_air']
            m = data['Dimensi']['m']
        else:
            b = desain_data_or_b
            H = h_total
            h_air = H - 0.6 if H else 1.0
            m = m if m is not None else 1.0
            
        # Koordinat DXF
        x_bl = -b/2; y_b = 0; x_br = b/2
        x_tl = -b/2 - (m*H); y_t = H; x_tr = b/2 + (m*H)
        x_wl = -b/2 - (m*h_air); y_w = h_air; x_wr = b/2 + (m*h_air)
        
        dxf = "0\nSECTION\n2\nENTITIES\n"
        def dxf_line(x1, y1, x2, y2, layer):
            return f"0\nLINE\n8\n{layer}\n10\n{x1}\n20\n{y1}\n30\n0.0\n11\n{x2}\n21\n{y2}\n31\n0.0\n"
        def dxf_text(x, y, text, height, layer):
            return f"0\nTEXT\n8\n{layer}\n10\n{x}\n20\n{y}\n30\n0.0\n40\n{height}\n1\n{text}\n"

        dxf += dxf_line(x_tl, y_t, x_bl, y_b, "STRUKTUR")
        dxf += dxf_line(x_bl, y_b, x_br, y_b, "STRUKTUR")
        dxf += dxf_line(x_br, y_b, x_tr, y_t, "STRUKTUR")
        dxf += dxf_line(x_wl, y_w, x_wr, y_w, "AIR")
        dxf += dxf_text(0, -0.5, f"b = {b:.2f}m", 0.2, "TEXT")
        dxf += "0\nENDSEC\n0\nEOF"
        return dxf
    # =========================================
    # KEBUTUHAN AIR TANAMAN (KP-01)
    # =========================================
    def hitung_kebutuhan_air_irigasi(self, eto, kc, curah_hujan_efektif, perkolasi=2.0, wlr=0.0, efisiensi_irigasi=0.65):
        """
        Menghitung Kebutuhan Bersih Air di Sawah (NFR) dan Kebutuhan Pengambilan (IR).
        Semua satuan input dalam mm/hari.
        - eto: Evapotranspirasi referensi (dari Penman)
        - kc: Koefisien tanaman (Crop Coefficient)
        - perkolasi: Kehilangan air ke bawah tanah (mm/hari, standar 2-3 untuk lempung)
        - wlr: Water Layer Replacement (Penggantian lapisan air, untuk padi)
        - efisiensi_irigasi: 65% (0.65) standar untuk saluran terbuka tahanan tanah
        """
        # Evapotranspirasi Tanaman (ETc)
        etc = eto * kc
        
        # Kebutuhan Air di Sawah (Net Field Requirement - NFR)
        # NFR = ETc + Perkolasi + WLR - Hujan Efektif
        nfr = etc + perkolasi + wlr - curah_hujan_efektif
        
        # Jika hujan lebih besar dari kebutuhan, NFR = 0 (tidak perlu irigasi)
        nfr = max(0.0, nfr)
        
        # Kebutuhan Air Irigasi di Intake (Irrigation Requirement - IR)
        # IR = NFR / Efisiensi (mm/hari)
        ir_mm_hari = nfr / efisiensi_irigasi
        
        # Konversi ke Liter/detik/Hektar (L/s/ha)
        # 1 mm/hari = 10 m3/ha/hari = 10 / 86400 m3/s/ha = 0.1157 L/s/ha
        ir_lps_ha = ir_mm_hari * 0.1157
        
        return {
            "ETc_mm_hari": round(etc, 2),
            "NFR_mm_hari": round(nfr, 2),
            "IR_mm_hari": round(ir_mm_hari, 2),
            "Kebutuhan_Air_Lps_per_Ha": round(ir_lps_ha, 3)
        }
    # =========================================
    # 4. NOMENKLATUR & SKEMA JARINGAN (KP-01)
    # =========================================
    def generate_skema_jaringan_kp01(self, nama_daerah_irigasi, data_sekunder):
        """
        Membuat Nomenklatur dan Skema Jaringan Irigasi sesuai Standar KP-01.
        - nama_daerah_irigasi: String (misal: "Way Sekampung")
        - data_sekunder: List of Dict berisi detail saluran sekunder
        """
        import networkx as nx
        import plotly.graph_objects as go
        import pandas as pd
        
        G = nx.DiGraph()
        tabel_nomenklatur = []
        
        # 1. Bendung & Intake Primer
        # Singkatan KP-01: Ambil huruf depan (Way Sekampung -> WS)
        kode_bendung = "".join([kata[0].upper() for kata in nama_daerah_irigasi.split() if kata])
        node_bendung = f"Bendung {nama_daerah_irigasi}\n(B.{kode_bendung})"
        G.add_node(node_bendung, type='bendung', level=0)
        
        node_primer = f"Sal. Primer {nama_daerah_irigasi}"
        G.add_node(node_primer, type='primer', level=1)
        G.add_edge(node_bendung, node_primer)
        
        # 2. Bangunan Bagi & Saluran Sekunder
        for i, sekunder in enumerate(data_sekunder):
            # Bangunan Bagi di Saluran Primer
            kode_bagi = f"B.{kode_bendung}.{i+1}"
            G.add_node(kode_bagi, type='bangunan_bagi', level=2)
            G.add_edge(node_primer, kode_bagi)
            
            # Saluran Sekunder
            nama_sekunder = sekunder['nama']
            # Kode sekunder KP-01: Ambil 3 huruf pertama (Natar -> NAT)
            kode_sekunder = nama_sekunder[:3].upper() 
            node_sekunder = f"Sal. Sekunder {nama_sekunder}"
            G.add_node(node_sekunder, type='sekunder', level=3)
            G.add_edge(kode_bagi, node_sekunder)
            
            tabel_nomenklatur.append({
                "Tingkat": "Sekunder",
                "Bangunan / Saluran": f"Saluran {nama_sekunder}",
                "Kode Nomenklatur": kode_bagi,
                "Fungsi KP-01": "Bangunan Bagi Primer ke Sekunder"
            })
            
            # 3. Petak Tersier & Boks Sadap
            jml_tersier = sekunder['jumlah_tersier']
            for j in range(jml_tersier):
                # Bangunan Sadap (Tersier)
                kode_sadap = f"B.{kode_sekunder}.{j+1}"
                G.add_node(kode_sadap, type='bangunan_sadap', level=4)
                G.add_edge(node_sekunder, kode_sadap)
                
                # Nomenklatur Petak Tersier (Kiri/Kanan)
                posisi = "Ki" if j % 2 == 0 else "Ka"
                kode_petak = f"{kode_sekunder}.{j+1} {posisi}"
                node_petak = f"Petak Tersier\n({kode_petak})"
                G.add_node(node_petak, type='petak_tersier', level=5)
                G.add_edge(kode_sadap, node_petak)
                
                tabel_nomenklatur.append({
                    "Tingkat": "Tersier",
                    "Bangunan / Saluran": f"Petak {kode_petak}",
                    "Kode Nomenklatur": kode_sadap,
                    "Fungsi KP-01": f"Boks Sadap untuk Petak {posisi} (Areal Tersier)"
                })
                
        # ---------------------------------------------------------
        # VISUALISASI NETWORK TREE MENGGUNAKAN PLOTLY
        # ---------------------------------------------------------
        # Menentukan posisi X dan Y menggunakan layout multipartite hierarki
        for node, data in G.nodes(data=True):
            data['subset'] = data['level']
            
        pos = nx.multipartite_layout(G, subset_key="subset", align="horizontal")
        
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            # Tukar X dan Y agar grafiknya mengalir vertikal (dari atas ke bawah)
            edge_x.extend([y0, y1, None])
            edge_y.extend([x0, x1, None])

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y, 
            line=dict(width=2, color='#94a3b8'),
            hoverinfo='none', mode='lines'
        )

        node_x = []
        node_y = []
        node_text = []
        node_color = []
        
        color_map = {
            'bendung': '#ef4444',         # Merah
            'primer': '#3b82f6',          # Biru Tua
            'bangunan_bagi': '#f59e0b',   # Kuning/Orange
            'sekunder': '#0ea5e9',        # Biru Muda
            'bangunan_sadap': '#8b5cf6',  # Ungu
            'petak_tersier': '#22c55e'    # Hijau
        }

        for node in G.nodes():
            x, y = pos[node]
            node_x.append(y) # Tukar posisi
            node_y.append(x)
            node_text.append(node)
            node_color.append(color_map.get(G.nodes[node]['type'], '#000'))

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=node_text,
            textposition="bottom center",
            hoverinfo='text',
            marker=dict(showscale=False, color=node_color, size=25, line_width=2, line_color='white')
        )

        fig = go.Figure(data=[edge_trace, node_trace],
                     layout=go.Layout(
                        title='<b>Skema Jaringan Irigasi & Nomenklatur (Standar KP-01)</b>',
                        titlefont_size=18,
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=40,l=20,r=20,t=60),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        # Autorange reversed agar Bendung berada di atas
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, autorange="reversed"),
                        plot_bgcolor='white'
                    )
        )
        
        df_nomenklatur = pd.DataFrame(tabel_nomenklatur)
        return fig, df_nomenklatur
