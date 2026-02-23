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
            
            # Gunakan .read() dari memori (StringIO) agar aman di Streamlit
            stream = io.StringIO(uploaded_file.getvalue().decode('utf-8', errors='ignore'))
            doc = ezdxf.read(stream)
            msp = doc.modelspace()
            
            # A. Ekstrak Teks (Mata AI membaca Tulisan)
            text_entities = []
            # Ambil MTEXT dan TEXT biasa
            for e in msp.query('TEXT MTEXT'):
                if e.dxftype() == 'TEXT':
                    text_entities.append(e.dxf.text)
                elif e.dxftype() == 'MTEXT':
                    text_entities.append(e.text)
            
            unique_texts = list(set(text_entities)) # Hapus duplikat
            
            text_info = f"**Analisis Otomatis File DXF:**\n"
            text_info += f"- Versi DXF: {doc.dxfversion}\n"
            text_info += f"- Teks Terbaca: {', '.join(unique_texts)}\n"

            # B. Render Gambar (Mata AI melihat Garis)
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
