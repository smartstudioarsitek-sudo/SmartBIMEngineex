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
        # =====================================================================
        # BLOK 1: HANDLING DXF (CAD & TOPOGRAFI 3D)
        # =====================================================================
        if filename.endswith(".dxf"):
            stream = io.StringIO(uploaded_file.getvalue().decode('utf-8', errors='ignore'))
            doc = ezdxf.read(stream)
            msp = doc.modelspace()
            
            # --- A. EKSTRAK TEKS ---
            text_entities = []
            for e in msp.query('TEXT MTEXT'):
                if e.dxftype() == 'TEXT':
                    text_entities.append(e.dxf.text)
                elif e.dxftype() == 'MTEXT':
                    text_entities.append(e.text)
            
            unique_texts = list(set(text_entities))
            
            text_info = f"**Analisis Otomatis File DXF:**\n"
            text_info += f"- Versi DXF: {doc.dxfversion}\n"
            text_info += f"- Teks Terbaca: {', '.join(unique_texts[:50])} ...\n"
            
            # --- B. EKSTRAK KOORDINAT 3D (Z) ---
            titik_3d = []
            for e in msp.query('POINT LWPOLYLINE POLYLINE 3DFACE'):
                if e.dxftype() == 'POINT':
                    titik_3d.append((e.dxf.location.x, e.dxf.location.y, e.dxf.location.z))
                elif e.dxftype() == 'LWPOLYLINE':
                    for pt in e.get_points(format='xy'):
                        titik_3d.append((pt[0], pt[1], e.dxf.elevation))
                elif e.dxftype() == 'POLYLINE':
                    if e.is_3d_polyline or e.is_polygon_mesh:
                        for v in e.vertices:
                            titik_3d.append((v.dxf.location.x, v.dxf.location.y, v.dxf.location.z))
                    else:
                        z_elev = e.dxf.elevation.z if hasattr(e.dxf.elevation, 'z') else e.dxf.elevation[2] if isinstance(e.dxf.elevation, tuple) else e.dxf.elevation
                        for v in e.vertices:
                            titik_3d.append((v.dxf.location.x, v.dxf.location.y, z_elev))
                elif e.dxftype() == '3DFACE':
                    for vtx in [e.dxf.vtx0, e.dxf.vtx1, e.dxf.vtx2, e.dxf.vtx3]:
                        titik_3d.append((vtx.x, vtx.y, vtx.z))

            if titik_3d:
                titik_unik = list(set(titik_3d)) 
                df_data = pd.DataFrame(titik_unik, columns=['X', 'Y', 'Z'])
                text_info += f"\n**Data Topografi (Elevasi 3D):**\n"
                text_info += f"- Ditemukan {len(df_data)} titik koordinat spasial 3D.\n"
                text_info += f"- Elevasi Terendah: {df_data['Z'].min():.2f} mdpl\n"
                text_info += f"- Elevasi Tertinggi: {df_data['Z'].max():.2f} mdpl\n"
                text_info += f"*Instruksi AI: Jika user meminta Cut & Fill, gunakan Dataframe ini.*\n"

            # --- C. RENDER GAMBAR ---
            fig = plt.figure(figsize=(10, 6))
            ax = fig.add_axes([0, 0, 1, 1])
            ctx = RenderContext(doc)
            out = MatplotlibBackend(ax)
            Frontend(ctx, out).draw_layout(msp, finalize=True)
            
            image_buf = io.BytesIO()
            fig.savefig(image_buf, format='png', dpi=150)
            image_buf.seek(0)
            plt.close(fig)

        # =====================================================================
        # BLOK 2: HANDLING GIS VEKTOR (GEOJSON, KML, KMZ)
        # =====================================================================
        elif filename.endswith(('.geojson', '.kml', '.kmz')):
            if not HAS_GIS_ENGINE:
                text_info = "⚠️ File spasial terdeteksi, tetapi modul libs_gis belum aktif."
            else:
                ekstensi = f".{filename.split('.')[-1]}"
                with tempfile.NamedTemporaryFile(delete=False, suffix=ekstensi) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                try:
                    gis = GIS_Engine()
                    hasil = gis.analisis_luas_geojson(tmp_path)
                    
                    text_info = f"**Analisis Spasial Area (GIS):**\n"
                    text_info += f"- Nama File: {filename}\n"
                    
                    if "error" not in hasil:
                        text_info += f"- Total Luas Area: **{hasil['Total_Luas_m2']} m2** ({hasil['Total_Luas_Ha']} Hektar)\n"
                        text_info += "\n*Instruksi untuk AI: Gunakan luas presisi ini untuk menghitung RAB Pembersihan Lahan.* \n"
                    else:
                        text_info += f"- Error: {hasil['error']}\n"
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

        # =====================================================================
        # BLOK 3: HANDLING GIS RASTER (DEM, TIF, TIFF)
        # =====================================================================
        elif filename.endswith(('.tif', '.tiff', '.dem')):
            if not HAS_RASTERIO:
                text_info = "⚠️ File DEM terdeteksi, tetapi library 'rasterio' belum terinstall."
            else:
                ekstensi = f".{filename.split('.')[-1]}"
                with tempfile.NamedTemporaryFile(delete=False, suffix=ekstensi) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                    
                try:
                    with rasterio.open(tmp_path) as dataset:
                        elevasi = dataset.read(1)
                        nodata_val = dataset.nodata
                        valid_elevasi = elevasi[elevasi != nodata_val] if nodata_val is not None else elevasi

                        text_info = f"**Analisis Digital Elevation Model (DEM):**\n"
                        text_info += f"- Nama File: {filename}\n"
                        text_info += f"- Elevasi Terendah Lahan: **{valid_elevasi.min():.2f} mdpl**\n"
                        text_info += f"- Elevasi Tertinggi Lahan: **{valid_elevasi.max():.2f} mdpl**\n"
                        text_info += "\n*Instruksi AI: Gunakan data elevasi ini untuk analisis kontur/longsor.*\n"
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

        # =====================================================================
        # BLOK 4: HANDLING GPS DATA (.GPX)
        # =====================================================================
        elif filename.endswith('.gpx'):
            gpx_data = uploaded_file.getvalue().decode('utf-8', errors='ignore')
            gpx = gpxpy.parse(gpx_data)
            
            total_titik = sum([len(segment.points) for track in gpx.tracks for segment in track.segments])
            total_waypoint = len(gpx.waypoints)
            
            text_info = f"**Analisis Data GPS (.GPX):**\n"
            text_info += f"- Nama File: {filename}\n"
            text_info += f"- Jumlah Jalur / Trackpoints: {total_titik} titik\n"
            text_info += f"- Jumlah Waypoints (Patok): {total_waypoint} titik\n"
            text_info += "*Instruksi AI: Ini adalah data hasil tracking GPS lapangan.*\n"

        # =====================================================================
        # BLOK 5: HANDLING SHAPEFILE BUNDLE (.ZIP)
        # =====================================================================
        elif filename.endswith('.zip'):
            # Membaca Shapefile (SHP) yang dikompres menjadi ZIP langsung menggunakan GeoPandas
            try:
                gdf = gpd.read_file(uploaded_file)
                total_luas_m2 = 0
                
                # Cek jika ada poligon untuk dihitung luasnya
                if not gdf.empty and gdf.geom_type[0] in ['Polygon', 'MultiPolygon']:
                    gdf_metric = gdf.to_crs(epsg=3857) # Konversi ke meter
                    total_luas_m2 = gdf_metric.geometry.area.sum()
                
                text_info = f"**Analisis Bundle Shapefile (.ZIP):**\n"
                text_info += f"- Nama File: {filename}\n"
                text_info += f"- Jumlah Entitas / Poligon: {len(gdf)} buah\n"
                if total_luas_m2 > 0:
                    text_info += f"- Total Luas Area: **{round(total_luas_m2, 2)} m2** ({round(total_luas_m2/10000, 2)} Hektar)\n"
            except Exception as e:
                text_info = f"Gagal membaca Shapefile di dalam ZIP: {e}"

        # =====================================================================
        # BLOK 6: FORMAT LAINNYA
        # =====================================================================
        else:
            text_info = f"Data {filename} diterima sebagai referensi."

    except Exception as e:
        return f"Gagal membaca struktur file: {str(e)}", None, None

    return text_info, image_buf, df_data

# ==============================================================================
# END OF FILE
# ==============================================================================
