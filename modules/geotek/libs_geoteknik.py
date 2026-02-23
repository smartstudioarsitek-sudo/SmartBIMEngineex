import numpy as np
import matplotlib.pyplot as plt

class Geotech_Engine:
    # [FIX] INIT FLEXIBLE
    # Menerima 'gamma' ATAU 'gamma_tanah' agar AI tidak error
    def __init__(self, gamma=18, gamma_tanah=None, phi=30, c=10):
        # Logika prioritas: Jika 'gamma' diisi pakai itu, jika tidak pakai 'gamma_tanah', default 18
        if gamma is not None:
            self.gamma = gamma
        elif gamma_tanah is not None:
            self.gamma = gamma_tanah
        else:
            self.gamma = 18.0
            
        self.phi = phi           
        self.c = c               
        
    def hitung_talud_batu_kali(self, H, b_atas, b_bawah, beban_atas_q=0):
        # 1. Tekanan Tanah Aktif (Rankine)
        # Konversi phi ke radian
        phi_rad = np.radians(self.phi)
        Ka = np.tan(np.radians(45) - phi_rad/2)**2
        
        Pa = 0.5 * self.gamma * (H**2) * Ka
        Pq = beban_atas_q * H * Ka
        
        Total_Dorong_H = Pa + Pq
        Momen_Guling = (Pa * H/3) + (Pq * H/2)
        
        # 2. Berat Sendiri
        gamma_batu = 22.0
        W1 = b_atas * H * gamma_batu
        W2 = 0.5 * (b_bawah - b_atas) * H * gamma_batu
        
        # Momen Tahan 
        L1 = b_bawah - (b_atas / 2) 
        L2 = (b_bawah - b_atas) * (2/3) 
        Momen_Tahan = (W1 * L1) + (W2 * L2)
        
        # 3. SF
        SF_Guling = Momen_Tahan / Momen_Guling if Momen_Guling > 0 else 99.0
        
        return {
            "SF_Guling": round(SF_Guling, 2),
            "Status": "AMAN" if SF_Guling >= 1.5 else "BAHAYA"
        }

    # ===============================================
    # [FIX] FUNGSI BORE PILE (MULTI-ALIAS)
    # ===============================================
    def daya_dukung_bore_pile(self, d, l, n_ujung, n_selimut):
        """
        Fungsi Utama Hitung Bore Pile (4 Return Values)
        """
        # Luas
        Ap = 0.25 * np.pi * (d**2)
        As = np.pi * d * l
        
        # 1. Ujung (End Bearing)
        # qp max 4000 kPa (400 ton/m2)
        qp_val = min(40 * n_ujung, 400) * 10 # kN/m2
        Qp = qp_val * Ap
        
        # 2. Selimut (Friction)
        # fs = 2N (kN/m2) estimasi kasar
        fs_val = 2.0 * n_selimut * 10 
        Qs = fs_val * As
        
        # 3. Rekap
        Q_ult = Qp + Qs
        Q_allow = Q_ult / 2.5
        
        return Qp, Qs, Q_ult, Q_allow

    # ALIAS 1: Jika AI memanggil 'hitung_bore_pile'
    def hitung_bore_pile(self, diameter_cm=None, kedalaman_m=None, N_spt_rata=None, d=None, l=None, n_ujung=None, n_selimut=None):
        # Normalisasi input
        D = d if d else (diameter_cm/100 if diameter_cm else 0.6)
        L = l if l else (kedalaman_m if kedalaman_m else 10)
        Nu = n_ujung if n_ujung else (N_spt_rata if N_spt_rata else 10)
        Ns = n_selimut if n_selimut else (N_spt_rata if N_spt_rata else 10)
        
        Qp, Qs, Q_ult, Q_allow = self.daya_dukung_bore_pile(D, L, Nu, Ns)
        
        # Return dictionary jika dipanggil lewat fungsi lama
        return {
            "Q_allow_kN": round(Q_allow, 2),
            "Q_ultimate_kN": round(Q_ult, 2)
        }
    # ==============================================================================
    # ANALISIS STABILITAS LERENG BENDUNGAN TANAH (BISHOP SIMPLIFIED)
    # ==============================================================================
    def analisis_stabilitas_bishop(self, tinggi_lereng, kemiringan_derajat, c, phi, gamma, n_slices=20):
        """
        Menghitung Faktor Keamanan (FS) lereng bendungan tanah urugan 
        menggunakan Metode Bishop Sederhana (Simplified Bishop Method).
        Terintegrasi dengan rendering visualisasi bidang gelincir kritis.
        """
        import numpy as np
        import plotly.graph_objects as go
        
        beta = np.radians(kemiringan_derajat)
        phi_rad = np.radians(phi)
        
        # 1. Definisikan Geometri Lereng (Asumsi keruntuhan pada Toe / Kaki Lereng)
        L_crest = tinggi_lereng / np.tan(beta)
        
        # Asumsi Titik Pusat Lingkaran Kelongsoran (Trial Center)
        Xc = L_crest * 0.3
        Yc = tinggi_lereng * 1.6
        
        # Radius lingkaran (harus melewati toe di koordinat 0,0)
        R = np.sqrt(Xc**2 + Yc**2)
        
        # Titik perpotongan lingkaran dengan permukaan atas (Crest)
        X_exit = Xc + np.sqrt(R**2 - (Yc - tinggi_lereng)**2)
        
        # 2. Pembuatan Irisan (Slices)
        x_edges = np.linspace(0, X_exit, n_slices + 1)
        x_centers = (x_edges[:-1] + x_edges[1:]) / 2
        b_width = x_edges[1:] - x_edges[:-1]
        
        W_list = []
        alpha_list = []
        
        for i, x in enumerate(x_centers):
            # Elevasi Permukaan Tanah (Y_surf)
            if x <= L_crest:
                Y_surf = x * np.tan(beta)
            else:
                Y_surf = tinggi_lereng
                
            # Elevasi Bidang Gelincir (Y_slip)
            Y_slip = Yc - np.sqrt(R**2 - (x - Xc)**2)
            
            # Tinggi irisan rata-rata
            h_slice = max(0, Y_surf - Y_slip)
            
            # Berat irisan (W) = h * b * gamma
            W = h_slice * b_width[i] * gamma
            W_list.append(W)
            
            # Sudut bidang gelincir pada irisan tersebut (alpha)
            sin_alpha = (x - Xc) / R
            alpha_list.append(np.arcsin(sin_alpha))
            
        W_arr = np.array(W_list)
        alpha_arr = np.array(alpha_list)
        b_arr = np.array(b_width)
        
        # 3. Iterasi Perhitungan Nilai FS (Bishop Equation)
        # Karena FS ada di kedua sisi persamaan, kita butuh iterasi konvergen
        FS = 1.5 # Tebakan awal
        tolerance = 0.001
        
        for _ in range(50):
            # Hitung m_alpha = cos(alpha) + (sin(alpha)*tan(phi)) / FS
            m_alpha = np.cos(alpha_arr) + (np.sin(alpha_arr) * np.tan(phi_rad)) / FS
            
            # Pembilang: Sum [ (c*b + W*tan(phi)) / m_alpha ]
            pembilang = np.sum((c * b_arr + W_arr * np.tan(phi_rad)) / m_alpha)
            
            # Penyebut: Sum [ W * sin(alpha) ]
            penyebut = np.sum(W_arr * np.sin(alpha_arr))
            
            FS_new = pembilang / penyebut if penyebut > 0 else 99.0
            
            if abs(FS_new - FS) < tolerance:
                FS = FS_new
                break
            FS = FS_new

        status_lereng = "✅ AMAN" if FS >= 1.5 else "❌ BAHAYA (Butuh Perkuatan/Berm)"

        # 4. Visualisasi Geometri & Irisan menggunakan Plotly
        fig = go.Figure()

        # Gambar Permukaan Lereng
        fig.add_trace(go.Scatter(
            x=[0, L_crest, X_exit + 5], 
            y=[0, tinggi_lereng, tinggi_lereng],
            mode='lines', line=dict(color='green', width=3),
            name='Permukaan Lereng', fill='tozeroy', fillcolor='rgba(34, 139, 34, 0.2)'
        ))

        # Gambar Bidang Gelincir (Lingkaran)
        theta = np.linspace(np.arcsin((0 - Xc)/R), np.arcsin((X_exit - Xc)/R), 100)
        x_arc = Xc + R * np.sin(theta)
        y_arc = Yc - R * np.cos(theta)
        
        fig.add_trace(go.Scatter(
            x=x_arc, y=y_arc,
            mode='lines', line=dict(color='red', width=2, dash='dash'),
            name='Bidang Gelincir Kritis', fill='tonexty', fillcolor='rgba(255, 0, 0, 0.1)'
        ))

        # Gambar Garis-Garis Irisan (Slices)
        for x_ed in x_edges:
            if x_ed <= L_crest:
                y_s = x_ed * np.tan(beta)
            else:
                y_s = tinggi_lereng
            y_sl = Yc - np.sqrt(R**2 - (x_ed - Xc)**2)
            fig.add_trace(go.Scatter(
                x=[x_ed, x_ed], y=[y_sl, y_s],
                mode='lines', line=dict(color='gray', width=1), showlegend=False
            ))

        fig.update_layout(
            title=f"Analisis Stabilitas Lereng Bendungan Urugan (Metode Bishop)<br>Safety Factor (FS) = <b>{FS:.3f}</b>",
            xaxis_title="Jarak Horizontal (m)", yaxis_title="Elevasi (m)",
            plot_bgcolor='aliceblue',
            yaxis=dict(scaleanchor="x", scaleratio=1), # Mengunci aspek rasio 1:1 agar lingkaran tidak lonjong
            showlegend=True
        )

        return {
            "Tinggi_Lereng_m": tinggi_lereng,
            "Sudut_Lereng_Derajat": kemiringan_derajat,
            "Kohesi_c_kPa": c,
            "Sudut_Geser_Phi_Derajat": phi,
            "Berat_Volume_Gamma_kN_m3": gamma,
            "Safety_Factor_FS": round(FS, 3),
            "Status_Keamanan": status_lereng
        }, fig
    # ==============================================================================
    # INSTRUMENTASI DAM SAFETY (PIEZOMETER & INCLINOMETER)
    # ==============================================================================
    def simulasi_dam_safety_dashboard(self, kedalaman_lubang_m=20, hari_pengamatan=30):
        """
        Simulasi pembacaan instrumen keamanan bendungan (Dam Safety)
        meliputi Piezometer (Tekanan Air Pori) dan Inclinometer (Pergerakan Lateral).
        """
        import pandas as pd
        import numpy as np
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        from datetime import datetime, timedelta

        # 1. GENERATE DUMMY DATA: PIEZOMETER (Time-Series Tekanan Air)
        dates = [datetime.now() - timedelta(days=i) for i in range(hari_pengamatan)]
        dates.reverse() # Urutkan dari terlama ke terbaru
        
        # Simulasi tekanan air pori naik karena curah hujan tinggi
        base_pwp = 45.0 # kPa
        trend = np.linspace(0, 15.0, hari_pengamatan)
        noise = np.random.normal(0, 2.0, hari_pengamatan)
        pwp_values = base_pwp + trend + noise
        threshold_pwp = 60.0 # Batas waspada kPa (Redline)

        df_piezo = pd.DataFrame({'Tanggal': dates, 'PWP_kPa': pwp_values})
        status_piezo = "🔴 SIAGA (Tekanan Pori Meningkat Tajam)" if pwp_values[-1] >= threshold_pwp else "🟢 AMAN NORMAL"

        # 2. GENERATE DUMMY DATA: INCLINOMETER (Depth-Profile Pergerakan)
        depths = np.linspace(0, kedalaman_lubang_m, 21)
        # Simulasi pergerakan lateral (mm) memuncak di kedalaman bidang gelincir (misal di kedalaman 10m)
        slip_depth = 10.0
        displacement = 15.0 * np.exp(-0.1 * (depths - slip_depth)**2)
        noise_disp = np.random.normal(0, 0.5, len(depths))
        displacement += noise_disp
        
        # Di dasar (depth max), pergerakan harus 0 (asumsi pipa tertanam kuat di batuan keras)
        displacement[-1] = 0.0

        df_inclino = pd.DataFrame({'Kedalaman_m': depths, 'Displacement_mm': displacement})
        max_disp = df_inclino['Displacement_mm'].max()
        threshold_disp = 20.0 # Batas pergerakan waspada (mm)
        status_inclino = "🔴 WASPADA (Pergerakan Terdeteksi)" if max_disp >= threshold_disp else "🟢 DEFORMASI WAJAR"

        # 3. VISUALISASI DASHBOARD (Plotly Subplots Kiri & Kanan)
        fig = make_subplots(rows=1, cols=2, 
                            subplot_titles=("<b>Piezometer</b> (Tekanan Air Pori)", 
                                            "<b>Inclinometer</b> (Deformasi Lateral)"))

        # Plot Kiri: Piezometer (X=Waktu, Y=PWP)
        fig.add_trace(go.Scatter(x=df_piezo['Tanggal'], y=df_piezo['PWP_kPa'], 
                                 mode='lines+markers', name='PWP Aktual', line=dict(color='dodgerblue')), row=1, col=1)
        fig.add_hline(y=threshold_pwp, line_dash="dash", line_color="red", 
                      annotation_text="Batas Siaga", row=1, col=1)
        
        # Plot Kanan: Inclinometer (X=Pergerakan, Y=Kedalaman)
        fig.add_trace(go.Scatter(x=df_inclino['Displacement_mm'], y=df_inclino['Kedalaman_m'], 
                                 mode='lines+markers', name='Displacement', line=dict(color='darkorange', width=3)), row=1, col=2)
        fig.add_hline(y=slip_depth, line_dash="dot", line_color="gray", 
                      annotation_text="Indikasi Bidang Gelincir", row=1, col=2)

        # Update Layout Axis
        fig.update_xaxes(title_text="Tanggal Pemantauan", row=1, col=1)
        fig.update_yaxes(title_text="Tekanan Air Pori (kPa)", row=1, col=1)
        
        fig.update_xaxes(title_text="Pergerakan Lateral (mm)", row=1, col=2)
        # Sumbu Y untuk Inclinometer WAJIB di-reverse agar 0m (permukaan) ada di bagian atas
        fig.update_yaxes(title_text="Kedalaman (m)", autorange="reversed", row=1, col=2) 

        fig.update_layout(title_text="<b>🖥️ Dashboard Real-Time Keamanan Bendungan (Dam Safety)</b>",
                          height=500, showlegend=False, plot_bgcolor='whitesmoke')

        hasil_analisis = {
            "Pengamatan_Terakhir": df_piezo['Tanggal'].iloc[-1].strftime("%Y-%m-%d"),
            "Piezometer_PWP_kPa": round(pwp_values[-1], 2),
            "Status_Piezometer": status_piezo,
            "Inclinometer_Pergerakan_Max_mm": round(max_disp, 2),
            "Lokasi_Kritis_Kedalaman_m": round(df_inclino.loc[df_inclino['Displacement_mm'].idxmax(), 'Kedalaman_m'], 1),
            "Status_Inclinometer": status_inclino
        }

        return hasil_analisis, fig
