# ==============================================================================
# 📄 NAMA FILE: libs_topografi.py
# 🛠️ FUNGSI: DTM (Digital Terrain Model) & Cut-Fill Engine
# ==============================================================================

import numpy as np
import pandas as pd
from scipy.spatial import Delaunay
import plotly.graph_objects as go
import plotly.figure_factory as ff

class Topografi_Engine:
    def __init__(self):
        self.engine_name = "SmartBIM DTM Engine (Delaunay TIN)"

    def hitung_cut_fill(self, df_points, elevasi_rencana):
        """
        Menghitung volume Galian (Cut) dan Timbunan (Fill) menggunakan metode Prisma TIN.
        Input: 
        - df_points: DataFrame dengan kolom ['X', 'Y', 'Z']
        - elevasi_rencana: Angka (float) elevasi target pengerukan/penimbunan
        """
        try:
            # 1. Ekstrak koordinat menjadi Numpy Array untuk komputasi super cepat
            points_2d = df_points[['X', 'Y']].to_numpy()
            z_vals = df_points['Z'].to_numpy()

            # 2. Buat Jaring Segitiga (Delaunay Triangulation)
            tri = Delaunay(points_2d)

            vol_galian = 0.0
            vol_timbunan = 0.0

            # 3. Iterasi setiap prisma segitiga
            for simplex in tri.simplices:
                # Ambil 3 titik sudut (X, Y) dari segitiga
                p1, p2, p3 = points_2d[simplex]
                # Ambil 3 elevasi (Z) dari segitiga
                z1, z2, z3 = z_vals[simplex]

                # Hitung Luas Segitiga 2D (menggunakan Determinan Matriks)
                luas_2d = 0.5 * abs(p1[0]*(p2[1] - p3[1]) + p2[0]*(p3[1] - p1[1]) + p3[0]*(p1[1] - p2[1]))

                # Hitung Elevasi Rata-rata Segitiga (Prisma)
                z_rata_rata = (z1 + z2 + z3) / 3.0
                
                # Bandingkan dengan Elevasi Rencana (Target)
                selisih_z = z_rata_rata - elevasi_rencana

                if selisih_z > 0:
                    # Jika tanah asli lebih tinggi dari rencana -> GALIAN (Cut)
                    vol_galian += luas_2d * selisih_z
                else:
                    # Jika tanah asli lebih rendah dari rencana -> TIMBUNAN (Fill)
                    vol_timbunan += luas_2d * abs(selisih_z)

            return {
                "Volume_Galian_m3": round(vol_galian, 2),
                "Volume_Timbunan_m3": round(vol_timbunan, 2),
                "Luas_Area_m2": round(df_points['X'].max() - df_points['X'].min(), 2) * round(df_points['Y'].max() - df_points['Y'].min(), 2), # Estimasi kasar bounding box
                "Status": "✅ Perhitungan Presisi Metode TIN Selesai"
            }
        
        except Exception as e:
            return {"error": f"Gagal menghitung topografi: {str(e)}"}

    def visualisasi_3d_terrain(self, df_points, elevasi_rencana):
        """
        Menghasilkan objek grafik Plotly 3D interaktif untuk ditampilkan di Streamlit.
        """
        x = df_points['X'].values
        y = df_points['Y'].values
        z = df_points['Z'].values

        # 1. Buat Permukaan Tanah Asli (Mesh)
        fig = go.Figure(data=[go.Mesh3d(
            x=x, y=y, z=z,
            opacity=0.8,
            color='saddlebrown',
            name='Tanah Asli (Eksisting)'
        )])

        # 2. Buat Permukaan Elevasi Rencana (Bidang Datar)
        # Bounding box untuk plane datar
        plane_x = [x.min(), x.max(), x.max(), x.min()]
        plane_y = [y.min(), y.min(), y.max(), y.max()]
        plane_z = [elevasi_rencana] * 4

        fig.add_trace(go.Mesh3d(
            x=plane_x, y=plane_y, z=plane_z,
            i=[0, 0], j=[1, 2], k=[2, 3], # Indeks segitiga pembentuk persegi
            opacity=0.5,
            color='cyan',
            name=f'Elevasi Rencana (+{elevasi_rencana}m)'
        ))

        fig.update_layout(
            scene=dict(
                xaxis_title='Kordinat X (m)',
                yaxis_title='Kordinat Y (m)',
                zaxis_title='Elevasi Z (m)'
            ),
            title="Visualisasi 3D Cut & Fill Terrain",
            margin=dict(l=0, r=0, b=0, t=40)
        )
        return fig
    # ==============================================================================
    # 4. SIMULASI GENANGAN BANJIR 3D (BATHTUB INUNDATION MODEL)
    # ==============================================================================
    def simulasi_genangan_banjir_3d(self, df_points, elevasi_banjir):
        """
        Mensimulasikan Peta Genangan Banjir (Inundation Map) secara 3D.
        Menghitung luas area yang terendam dan perkiraan volume air.
        Input: 
        - df_points: DataFrame titik topografi ['X', 'Y', 'Z']
        - elevasi_banjir: Muka Air Banjir (MAB) dari hasil analisis hidrolika/hidrologi
        """
        import plotly.graph_objects as go
        from scipy.spatial import Delaunay
        import numpy as np

        try:
            x = df_points['X'].to_numpy()
            y = df_points['Y'].to_numpy()
            z = df_points['Z'].to_numpy()

            # ---------------------------------------------------------
            # A. PERHITUNGAN LUAS & VOLUME GENANGAN (ANALITIK)
            # ---------------------------------------------------------
            points_2d = df_points[['X', 'Y']].to_numpy()
            tri = Delaunay(points_2d)

            luas_genangan = 0.0
            volume_air = 0.0

            # Hitung per prisma segitiga (TIN)
            for simplex in tri.simplices:
                p1, p2, p3 = points_2d[simplex]
                z1, z2, z3 = z[simplex]
                
                # Elevasi rata-rata dasar tanah pada segitiga ini
                z_rata = (z1 + z2 + z3) / 3.0
                
                # Jika tanah di bawah muka air banjir, berarti area ini tergenang
                if z_rata < elevasi_banjir:
                    # Luas segitiga 2D
                    luas_2d = 0.5 * abs(p1[0]*(p2[1] - p3[1]) + p2[0]*(p3[1] - p1[1]) + p3[0]*(p1[1] - p2[1]))
                    kedalaman_air = elevasi_banjir - z_rata
                    
                    luas_genangan += luas_2d
                    volume_air += luas_2d * kedalaman_air

            hasil_analisis = {
                "Elevasi_Muka_Air_Banjir_m": elevasi_banjir,
                "Estimasi_Luas_Genangan_m2": round(luas_genangan, 2),
                "Estimasi_Luas_Genangan_Ha": round(luas_genangan / 10000, 2),
                "Volume_Tampungan_Banjir_m3": round(volume_air, 2),
                "Status": "✅ Simulasi Inundation (Bathtub Model) Berhasil"
            }

            # ---------------------------------------------------------
            # B. VISUALISASI 3D INTERAKTIF (PLOTLY)
            # ---------------------------------------------------------
            fig = go.Figure()

            # 1. Permukaan Tanah Asli (DTM) - Warna Coklat
            fig.add_trace(go.Mesh3d(
                x=x, y=y, z=z,
                opacity=0.9,
                color='saddlebrown',
                name='Topografi Asli'
            ))

            # 2. Bidang Air Banjir (Bathtub Plane) - Warna Biru Transparan
            plane_x = [x.min(), x.max(), x.max(), x.min()]
            plane_y = [y.min(), y.min(), y.max(), y.max()]
            plane_z = [elevasi_banjir] * 4

            fig.add_trace(go.Mesh3d(
                x=plane_x, y=plane_y, z=plane_z,
                i=[0, 0], j=[1, 2], k=[2, 3],
                opacity=0.5,
                color='dodgerblue',
                name=f'Muka Air Banjir (+{elevasi_banjir}m)'
            ))

            # 3. Penanda Titik Kritis Terendam - Warna Merah
            terendam_mask = z <= elevasi_banjir
            if terendam_mask.any():
                fig.add_trace(go.Scatter3d(
                    x=x[terendam_mask], y=y[terendam_mask], z=z[terendam_mask],
                    mode='markers',
                    marker=dict(size=3, color='red', opacity=0.8),
                    name='Area Kritis Terendam'
                ))

            fig.update_layout(
                scene=dict(
                    xaxis_title='Koordinat X (m)',
                    yaxis_title='Koordinat Y (m)',
                    zaxis_title='Elevasi Z (m)'
                ),
                title=f"Peta Genangan Banjir 3D (Elevasi {elevasi_banjir} m)",
                margin=dict(l=0, r=0, b=0, t=40),
                legend=dict(x=0.01, y=0.99)
            )

            return fig, hasil_analisis

        except Exception as e:
            return None, {"error": f"Gagal mensimulasikan genangan 3D: {str(e)}"}
