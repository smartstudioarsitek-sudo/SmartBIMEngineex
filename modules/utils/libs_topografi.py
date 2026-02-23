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
