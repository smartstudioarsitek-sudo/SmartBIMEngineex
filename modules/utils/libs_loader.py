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
class DXF_QTO_Engine:
    """
    Mesin Quantity Take-Off (QTO) 2D berbasis Vektor dengan Boolean Geometri.
    Membaca file DXF dan mengekstrak Luasan (Area) serta Panjang (Length).
    Mampu mendeteksi poligon di dalam poligon (lubang/void) dan otomatis mengurangkannya.
    """
    def __init__(self):
        self.engine_name = "SmartBIM Vector QTO Engine (Boolean Active)"

    def extract_qto_from_dxf(self, file_stream):
        import ezdxf
        import pandas as pd
        import tempfile
        import os
        import math
        
        # Import Shapely untuk operasi Boolean Geometri (pengurangan lubang)
        try:
            from shapely.geometry import Polygon, LineString, Point
        except ImportError:
            return None, "Library 'shapely' belum terinstall. Mesin QTO gagal dimuat."

        # 1. Simpan stream DXF sementara ke disk
        file_stream.seek(0)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            tmp.write(file_stream.read())
            tmp_path = tmp.name

        try:
            doc = ezdxf.readfile(tmp_path)
            msp = doc.modelspace()
            
            qto_data = []
            
            # Wadah penampung geometri per layer
            layer_polygons = {}
            layer_lines = {}

            # 2. Iterasi semua entitas di Modelspace CAD
            for entity in msp:
                layer_name = entity.dxf.layer
                dxftype = entity.dxftype()

                # Abaikan layer standar/sampah visual yang tidak butuh dihitung
                if any(abaikan in layer_name.lower() for abaikan in ['dim', 'text', 'defpoints', '0', 'grid', 'as', 'arsir', 'hatch']):
                    continue

                # A. Tangkap LWPOLYLINE (Bisa berupa Garis atau Area)
                if dxftype == 'LWPOLYLINE':
                    points = list(entity.get_points(format='xy'))
                    if len(points) < 2: continue
                    
                    # Cek apakah poligon tertutup (Bentuk Area)
                    if entity.is_closed or points[0] == points[-1]:
                        if len(points) >= 3:
                            poly = Polygon(points)
                            # Coba perbaiki poligon yang self-intersecting (garisnya silang)
                            if not poly.is_valid:
                                poly = poly.buffer(0) 
                                
                            if poly.area > 0:
                                layer_polygons.setdefault(layer_name, []).append(poly)
                    else:
                        # Jika terbuka, hitung panjangnya (Line)
                        line = LineString(points)
                        layer_lines[layer_name] = layer_lines.get(layer_name, 0.0) + line.length

                # B. Tangkap LINE biasa
                elif dxftype == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    length = math.dist((start.x, start.y), (end.x, end.y))
                    if length > 0:
                        layer_lines[layer_name] = layer_lines.get(layer_name, 0.0) + length

                # C. Tangkap CIRCLE (Bisa diubah jadi Poligon Area untuk pilar bulat dll)
                elif dxftype == 'CIRCLE':
                    center = (entity.dxf.center.x, entity.dxf.center.y)
                    radius = entity.dxf.radius
                    if radius > 0:
                        circle_poly = Point(center).buffer(radius)
                        layer_polygons.setdefault(layer_name, []).append(circle_poly)

            os.remove(tmp_path)

            # 3. EKSEKUSI BOOLEAN GEOMETRI (Pengurangan Lubang/Void)
            for layer, polys in layer_polygons.items():
                # Urutkan poligon dari yang terluas ke terkecil
                # Logika: Poligon terluas pasti pelat utama, yang lebih kecil di dalamnya pasti lubang
                polys_sorted = sorted(polys, key=lambda p: p.area, reverse=True)
                
                final_polys = []
                for p in polys_sorted:
                    is_hole = False
                    # Cek apakah poligon 'p' ini berada di dalam perut poligon utama yang sudah ada
                    for i, fp in enumerate(final_polys):
                        if fp.contains(p):
                            # BOOLEAN DIFFERENCE: Kurangi luasan utama dengan lubang ini
                            final_polys[i] = fp.difference(p)
                            is_hole = True
                            break
                            
                    if not is_hole:
                        # Jika bukan lubang, jadikan poligon utama baru di layer ini
                        final_polys.append(p)
                        
                # Agregasi total luas bersih (Net Area) untuk layer ini
                total_area = sum(fp.area for fp in final_polys)
                if total_area > 0:
                    qto_data.append({"Layer (Item Pekerjaan)": layer, "Kategori": "Luasan (m2)", "Volume": total_area})

            # 4. Agregasi Total Panjang (Line)
            for layer, length in layer_lines.items():
                if length > 0:
                    qto_data.append({"Layer (Item Pekerjaan)": layer, "Kategori": "Panjang (m)", "Volume": length})

            if not qto_data:
                return None, "File DXF terbaca, tetapi tidak ada entitas Poligon/Garis yang valid di layer konstruksi."

            # 5. Rekapitulasi Akhir
            df = pd.DataFrame(qto_data)
            df_rekap = df.groupby(['Layer (Item Pekerjaan)', 'Kategori'])['Volume'].sum().reset_index()
            df_rekap['Volume'] = df_rekap['Volume'].round(3)

            return df_rekap, "Sukses"

        except Exception as e:
            if os.path.exists(tmp_path): os.remove(tmp_path)
            return None, f"Gagal memproses DXF: {str(e)}"

# ==============================================================================
# END OF FILE
# ==============================================================================

