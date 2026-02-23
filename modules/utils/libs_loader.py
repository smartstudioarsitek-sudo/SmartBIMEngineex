import streamlit as st
import pandas as pd
import geopandas as gpd
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
import gpxpy
import zipfile
import tempfile
import os
import io

# 1. Import Engine GIS yang baru dibuat
try:
    from modules.utils.libs_gis import GIS_Engine
    HAS_QGIS = True
except ImportError:
    HAS_QGIS = False

def process_special_file(uploaded_file):
    """
    Fungsi Universal untuk membaca file CAD & GIS.
    Output: (text_summary, image_buffer, dataframe_raw)
    """
    filename = uploaded_file.name.lower()
    text_info = ""
    image_buf = None
    df_data = None

    try:
        # --- 1. HANDLING DXF (CAD) ---
        if filename.endswith(".dxf"):
            
            # Gunakan .read() dari memori (StringIO) agar tidak crash di Streamlit Cloud
            stream = io.StringIO(uploaded_file.getvalue().decode('utf-8', errors='ignore'))
            doc = ezdxf.read(stream)
            msp = doc.modelspace()
            
            # ---------------------------------------------------------
            # A. EKSTRAK TEKS (Mata AI membaca Tulisan)
            # ---------------------------------------------------------
            text_entities = []
            for e in msp.query('TEXT MTEXT'):
                if e.dxftype() == 'TEXT':
                    text_entities.append(e.dxf.text)
                elif e.dxftype() == 'MTEXT':
                    text_entities.append(e.text)
            
            unique_texts = list(set(text_entities))
            
            text_info = f"**Analisis Otomatis File DXF:**\n"
            text_info += f"- Versi DXF: {doc.dxfversion}\n"
            text_info += f"- Teks Terbaca: {', '.join(unique_texts[:50])} ...\n" # Batasi 50 teks agar tidak spam
            
            # ---------------------------------------------------------
            # B. EKSTRAK KOORDINAT 3D (Z / Elevasi Topografi)
            # ---------------------------------------------------------
            titik_3d = []
            
            # Mencari Point (Titik Ukur), Garis Kontur, dan Permukaan 3D
            for e in msp.query('POINT LWPOLYLINE POLYLINE 3DFACE'):
                
                # 1. Jika itu titik dari Total Station
                if e.dxftype() == 'POINT':
                    lokasi = e.dxf.location
                    titik_3d.append((lokasi.x, lokasi.y, lokasi.z))
                
                # 2. Jika itu garis kontur ringan (2D dengan properti elevasi Z)
                elif e.dxftype() == 'LWPOLYLINE':
                    z_elev = e.dxf.elevation
                    for pt in e.get_points(format='xy'):
                        titik_3d.append((pt[0], pt[1], z_elev))
                        
                # 3. Jika itu garis kontur berat / 3D
                elif e.dxftype() == 'POLYLINE':
                    if e.is_3d_polyline or e.is_polygon_mesh:
                        for v in e.vertices:
                            titik_3d.append((v.dxf.location.x, v.dxf.location.y, v.dxf.location.z))
                    else:
                        # 2D Polyline tapi punya elevasi
                        z_elev = e.dxf.elevation.z if hasattr(e.dxf.elevation, 'z') else e.dxf.elevation[2] if isinstance(e.dxf.elevation, tuple) else e.dxf.elevation
                        for v in e.vertices:
                            titik_3d.append((v.dxf.location.x, v.dxf.location.y, z_elev))
                
                # 4. Jika itu mesh segitiga 3D
                elif e.dxftype() == '3DFACE':
                    for vtx in [e.dxf.vtx0, e.dxf.vtx1, e.dxf.vtx2, e.dxf.vtx3]:
                        titik_3d.append((vtx.x, vtx.y, vtx.z))

            # Bersihkan duplikat koordinat dan buat DataFrame
            if titik_3d:
                # Menghapus titik duplikat agar proses komputasi lebih ringan
                titik_unik = list(set(titik_3d)) 
                df_data = pd.DataFrame(titik_unik, columns=['X', 'Y', 'Z'])
                
                text_info += f"\n**Data Topografi (Elevasi):**\n"
                text_info += f"- Ditemukan {len(df_data)} titik koordinat spasial 3D.\n"
                text_info += f"- Elevasi Terendah: {df_data['Z'].min():.2f} mdpl\n"
                text_info += f"- Elevasi Tertinggi: {df_data['Z'].max():.2f} mdpl\n"
                text_info += f"*Instruksi AI: Jika user meminta Cut & Fill, gunakan Dataframe df_data ini ke dalam modul libs_topografi.*\n"

            # ---------------------------------------------------------
            # C. RENDER GAMBAR (Mata AI melihat Garis)
            # ---------------------------------------------------------
            fig = plt.figure(figsize=(10, 6))
            ax = fig.add_axes([0, 0, 1, 1])
            ctx = RenderContext(doc)
            out = MatplotlibBackend(ax)
            Frontend(ctx, out).draw_layout(msp, finalize=True)
            
            image_buf = io.BytesIO()
            fig.savefig(image_buf, format='png', dpi=150)
            image_buf.seek(0)
            plt.close(fig)
        

        # --- 2. HANDLING GIS (GEOJSON, KML, KMZ) DENGAN QGIS ---
        elif filename.endswith(('.geojson', '.kml', '.kmz')):
            if not HAS_QGIS:
                text_info = "⚠️ File spasial terdeteksi, tetapi Mesin QGIS belum aktif di server/lokal."
            else:
                # QGIS butuh file fisik di hardisk (tidak bisa baca langsung dari memori byte Streamlit)
                # Jadi kita buat file temporary (sementara)
                ekstensi = f".{filename.split('.')[-1]}"
                with tempfile.NamedTemporaryFile(delete=False, suffix=ekstensi) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                try:
                    # Panggil Mesin QGIS secara rahasia
                    gis = GIS_Engine()
                    hasil = gis.analisis_luas_geojson(tmp_path)
                    
                    # [BUG FIX 1]: TIDAK ADA gis.shutdown() DI SINI.
                    # Membiarkan QGIS tetap menyala di latar belakang agar upload file 
                    # kedua, ketiga, dst tidak mengalami crash.
                    
                    # Format output agar dibaca oleh LLM AI (The GEMS Grandmaster)
                    text_info = f"**Analisis Spasial Otomatis (via QGIS):**\n"
                    text_info += f"- Nama File: {filename}\n"
                    
                    if "error" not in hasil:
                        text_info += f"- Total Luas Area: **{hasil['Total_Luas_m2']} m2** ({hasil['Total_Luas_Ha']} Hektar)\n"
                        text_info += "- Status: Area batas lahan berhasil dihitung.\n"
                        text_info += "\n*Instruksi untuk AI: Gunakan luas ini secara presisi (jangan dikarang) untuk menghitung RAB Pembersihan Lahan (Striping/Land Clearing) jika diminta oleh user.*"
                    else:
                        text_info += f"- Error: {hasil['error']}"
                        
                finally:
                    # [BUG FIX 2]: PENGHAPUSAN FILE TEMPORARY.
                    # Blok 'finally' memastikan file temp akan selalu dihapus dari hardisk 
                    # walaupun proses QGIS sukses maupun error, sehingga penyimpanan tidak penuh.
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

        # --- 3. HANDLING FORMAT LAINNYA ---
        else:
            text_info = f"Data {filename} diterima sebagai referensi."
            
    except Exception as e:
        return f"Gagal membaca struktur file: {str(e)}", None, None

    return text_info, image_buf, df_data
