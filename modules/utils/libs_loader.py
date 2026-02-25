# ==============================================================================
# 📄 NAMA FILE: libs_loader.py
# 📍 LOKASI: modules/utils/libs_loader.py
# 🛠️ FUNGSI: Universal File Reader (DXF 3D, GIS Vektor, DEM Raster, GPX, ZIP)
# ==============================================================================

import streamlit as st
import pandas as pd
import geopandas as gpd
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
import io
import os
import tempfile
import zipfile   # <-- DIKEMBALIKAN: Untuk membaca Shapefile (SHP) di dalam ZIP
import gpxpy     # <-- DIKEMBALIKAN: Untuk membaca track GPS alat ukur

# ---------------------------------------------------------
# 1. IMPORT ENGINE GIS (Vektor: GeoJSON, KML)
# ---------------------------------------------------------
try:
    from modules.utils.libs_gis import GIS_Engine
    HAS_GIS_ENGINE = True
except ImportError:
    HAS_GIS_ENGINE = False

# ---------------------------------------------------------
# 2. IMPORT RASTERIO (Raster: DEM, TIF)
# ---------------------------------------------------------
try:
    import rasterio
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False


def safe_chunked_save(uploaded_file, suffix):
    """
    [AUDIT PATCH]: Pemrosesan Memori Parsial (Chunked Stream)
    Mencegah ledakan memori RAM dengan membaca file per 4MB dan langsung 
    membuangnya ke Virtual Disk, menghindari penggunaan .getvalue() yang fatal.
    """
    import tempfile
    
    # Kembalikan pointer file ke awal sebelum membaca
    uploaded_file.seek(0) 
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    # Baca file lapis demi lapis (Chunking 4 Megabytes)
    for chunk in iter(lambda: uploaded_file.read(4096 * 1024), b''): 
        temp_file.write(chunk)
    temp_file.close()
    
    return temp_file.name

def process_special_file(uploaded_file):
    """
    Fungsi Universal untuk membaca file CAD & GIS dengan Proteksi Memori.
    Output: (text_summary, image_buffer, dataframe_raw)
    """
    filename = uploaded_file.name.lower()
    text_info = ""
    image_buf = None
    df_data = None
    
    # Batasan Ekstraksi (Safety Limiters untuk mencegah RAM Penuh saat parsing)
    MAX_TEXT_ENTITIES = 500
    MAX_3D_POINTS = 50000

    try:
        # =====================================================================
        # BLOK 1: HANDLING DXF (CAD & TOPOGRAFI 3D) DENGAN DISK-STREAMING
        # =====================================================================
        if filename.endswith(".dxf"):
            import ezdxf
            from ezdxf.addons.drawing import RenderContext, Frontend
            from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
            import matplotlib.pyplot as plt
            import io
            import os
            
            # 1. Simpan ke Disk secara parsial (Anti-Crash)
            tmp_path = safe_chunked_save(uploaded_file, ".dxf")
            
            try:
                # 2. Baca file langsung dari Disk (Jauh lebih hemat RAM daripada StringIO)
                doc = ezdxf.readfile(tmp_path)
                msp = doc.modelspace()
                
                # --- A. EKSTRAK TEKS (DENGAN BATASAN MEMORI) ---
                text_entities = set()
                # Menggunakan generator untuk tidak menumpuk semua data di awal
                for e in msp.query('TEXT MTEXT'):
                    if len(text_entities) >= MAX_TEXT_ENTITIES: break
                    
                    if e.dxftype() == 'TEXT': text_entities.add(e.dxf.text)
                    elif e.dxftype() == 'MTEXT': text_entities.add(e.text)
                
                unique_texts = list(text_entities)
                
                text_info = f"**Analisis Otomatis File DXF (Mode Terproteksi):**\n"
                text_info += f"- Versi DXF: {doc.dxfversion}\n"
                text_info += f"- Teks Terbaca: {', '.join(unique_texts[:20])} ... (Dibatasi {len(unique_texts)} entri untuk memori)\n"
                
                # --- B. EKSTRAK KOORDINAT 3D Z (DENGAN BATASAN MEMORI) ---
                titik_3d = set()
                
                for e in msp.query('POINT LWPOLYLINE POLYLINE 3DFACE'):
                    if len(titik_3d) >= MAX_3D_POINTS: 
                        text_info += f"\n⚠️ **Peringatan Densitas Masif**: Pembacaan titik dihentikan pada {MAX_3D_POINTS} koordinat untuk mencegah crash sistem.\n"
                        break
                        
                    if e.dxftype() == 'POINT':
                        titik_3d.add((round(e.dxf.location.x, 3), round(e.dxf.location.y, 3), round(e.dxf.location.z, 3)))
                    elif e.dxftype() == 'LWPOLYLINE':
                        for pt in e.get_points(format='xy'):
                            titik_3d.add((round(pt[0], 3), round(pt[1], 3), round(e.dxf.elevation, 3)))
                    elif e.dxftype() == '3DFACE':
                        for vtx in [e.dxf.vtx0, e.dxf.vtx1, e.dxf.vtx2, e.dxf.vtx3]:
                            titik_3d.add((round(vtx.x, 3), round(vtx.y, 3), round(vtx.z, 3)))

                if titik_3d:
                    df_data = pd.DataFrame(list(titik_3d), columns=['X', 'Y', 'Z'])
                    text_info += f"\n**Data Topografi (Elevasi 3D):**\n"
                    text_info += f"- Berhasil mengekstrak {len(df_data)} titik koordinat spasial.\n"
                    text_info += f"- Elevasi Terendah: {df_data['Z'].min():.2f} mdpl\n"
                    text_info += f"- Elevasi Tertinggi: {df_data['Z'].max():.2f} mdpl\n"
                    text_info += f"*Instruksi AI: Jika user meminta Cut & Fill, gunakan Dataframe ini.*\n"

                # --- C. RENDER GAMBAR (Diperkecil DPI-nya untuk Cloud) ---
                fig = plt.figure(figsize=(8, 5))
                ax = fig.add_axes([0, 0, 1, 1])
                ctx = RenderContext(doc)
                out = MatplotlibBackend(ax)
                Frontend(ctx, out).draw_layout(msp, finalize=True)
                
                image_buf = io.BytesIO()
                fig.savefig(image_buf, format='png', dpi=100) # DPI diturunkan dari 150 ke 100 agar ringan
                image_buf.seek(0)
                plt.close(fig)

            finally:
                # 3. Selalu bersihkan file temporary dari disk agar harddisk server tidak penuh
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        # =====================================================================
        # BLOK 2: HANDLING GIS VEKTOR (GEOJSON, KML, KMZ)
        # =====================================================================
        elif filename.endswith(('.geojson', '.kml', '.kmz')):
            if not HAS_GIS_ENGINE:
                text_info = "⚠️ File spasial terdeteksi, tetapi modul libs_gis belum aktif."
            else:
                ekstensi = f".{filename.split('.')[-1]}"
                tmp_path = safe_chunked_save(uploaded_file, ekstensi)
                
                try:
                    gis = GIS_Engine()
                    hasil = gis.analisis_luas_geojson(tmp_path)
                    
                    text_info = f"**Analisis Spasial Area (GIS):**\n"
                    text_info += f"- Nama File: {filename}\n"
                    
                    if "error" not in hasil:
                        text_info += f"- Total Luas Area: **{hasil['Total_Luas_m2']} m2** ({hasil['Total_Luas_Ha']} Hektar)\n"
                    else:
                        text_info += f"- Error: {hasil['error']}\n"
                finally:
                    import os
                    if os.path.exists(tmp_path): os.remove(tmp_path)

        # =====================================================================
        # BLOK 3: HANDLING GIS RASTER (DEM, TIF, TIFF)
        # =====================================================================
        elif filename.endswith(('.tif', '.tiff', '.dem')):
            if not HAS_RASTERIO:
                text_info = "⚠️ File DEM terdeteksi, tetapi library 'rasterio' belum terinstall."
            else:
                ekstensi = f".{filename.split('.')[-1]}"
                tmp_path = safe_chunked_save(uploaded_file, ekstensi)
                
                try:
                    with rasterio.open(tmp_path) as dataset:
                        # Resampling bacaan untuk menghindari Out-of-Memory pada peta resolusi miliaran pixel
                        scale_factor = 0.1 # Baca 10% resolusi
                        
                        elevasi = dataset.read(
                            1, 
                            out_shape=(
                                int(dataset.height * scale_factor),
                                int(dataset.width * scale_factor)
                            )
                        )
                        nodata_val = dataset.nodata
                        valid_elevasi = elevasi[elevasi != nodata_val] if nodata_val is not None else elevasi

                        text_info = f"**Analisis Digital Elevation Model (DEM):**\n"
                        text_info += f"- Nama File: {filename}\n"
                        text_info += f"- Elevasi Terendah Lahan: **{valid_elevasi.min():.2f} mdpl**\n"
                        text_info += f"- Elevasi Tertinggi Lahan: **{valid_elevasi.max():.2f} mdpl**\n"
                finally:
                    import os
                    if os.path.exists(tmp_path): os.remove(tmp_path)

        # =====================================================================
        # BLOK LAINNYA: (GPX & ZIP) - Tetap gunakan logika bawaan yang ringan
        # =====================================================================
        elif filename.endswith('.gpx'):
            import gpxpy
            gpx_data = uploaded_file.getvalue().decode('utf-8', errors='ignore')
            gpx = gpxpy.parse(gpx_data)
            total_titik = sum([len(segment.points) for track in gpx.tracks for segment in track.segments])
            text_info = f"**Analisis Data GPS (.GPX):**\n- Jalur: {total_titik} titik\n- Patok: {len(gpx.waypoints)}"

        elif filename.endswith('.zip'):
            try:
                gdf = gpd.read_file(uploaded_file)
                if not gdf.empty and gdf.geom_type[0] in ['Polygon', 'MultiPolygon']:
                    gdf_metric = gdf.to_crs(epsg=3857) 
                    total_luas_m2 = gdf_metric.geometry.area.sum()
                    text_info = f"**Analisis Shapefile (.ZIP):**\n- Entitas: {len(gdf)} buah\n- Luas: {round(total_luas_m2, 2)} m2"
            except Exception as e:
                text_info = f"Gagal membaca Shapefile di dalam ZIP: {e}"
        else:
            text_info = f"Data {filename} diterima sebagai referensi."

    except Exception as e:
        return f"Gagal membaca struktur file: {str(e)}", None, None

    return text_info, image_buf, df_data


# ==============================================================================
# END OF FILE
# ==============================================================================
