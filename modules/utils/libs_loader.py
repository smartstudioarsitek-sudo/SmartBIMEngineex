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
            # Baca DXF
            doc = ezdxf.readfile(io.BytesIO(uploaded_file.getvalue()))
            msp = doc.modelspace()
            
            # A. Ekstrak Teks (Untuk Otak AI)
            layers = [layer.dxf.name for layer in doc.layers]
            text_entities = [e.dxf.text for e in msp.query('TEXT MTEXT')[:50]] # Ambil 50 teks pertama
            
            text_info = f"**Analisis File DXF:**\n"
            text_info += f"- Versi DXF: {doc.dxfversion}\n"
            text_info += f"- Jumlah Layer: {len(layers)}\n"
            text_info += f"- Layer List: {', '.join(layers[:10])}...\n"
            text_info += f"- Sample Teks: {', '.join(text_entities)}\n"

            # B. Render Gambar (Untuk Mata AI)
            fig = plt.figure(figsize=(10, 10))
            ax = fig.add_axes([0, 0, 1, 1])
            ctx = RenderContext(doc)
            out = MatplotlibBackend(ax)
            Frontend(ctx, out).draw_layout(msp, finalize=True)
            
            image_buf = io.BytesIO()
            fig.savefig(image_buf, format='png', dpi=150)
            image_buf.seek(0)
            plt.close(fig)

        # --- 2. HANDLING DWG (CAD BINARY) ---
        elif filename.endswith(".dwg"):
            text_info = "⚠️ **Peringatan Format DWG:**\n"
            text_info += "Gemini tidak bisa membaca file DWG secara langsung (Format Tertutup).\n"
            text_info += "Saran: Silakan 'Save As' file ini ke format **DXF** di AutoCAD/ZWCAD agar bisa dibaca presisi (Vektor)."
            # Tidak ada preview untuk DWG (kecuali pakai API berbayar)

        # --- 3. HANDLING GIS (GeoJSON, KML, SHP) ---
        elif filename.endswith((".geojson", ".kml", ".json", ".zip", ".kmz")):
            
            # Trik khusus untuk Shapefile (.shp) yang biasanya di-zip
            if filename.endswith(".zip"):
                # Unzip sementara
                with tempfile.TemporaryDirectory() as tmpdirname:
                    with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                        zip_ref.extractall(tmpdirname)
                    
                    # Cari file .shp atau .kml dalam zip
                    shp_files = [f for f in os.listdir(tmpdirname) if f.endswith(('.shp', '.kml', '.geojson'))]
                    if shp_files:
                        file_path = os.path.join(tmpdirname, shp_files[0])
                        gdf = gpd.read_file(file_path)
                    else:
                        return "Gagal: Tidak ditemukan file SHP/KML dalam ZIP.", None, None
            
            # Trik untuk KMZ (Zipped KML)
            elif filename.endswith(".kmz"):
                with tempfile.TemporaryDirectory() as tmpdirname:
                    with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                        zip_ref.extractall(tmpdirname)
                        # Cari doc.kml
                        kml_file = os.path.join(tmpdirname, "doc.kml")
                        # Geopandas butuh driver KML (fiona)
                        gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'rw'
                        gdf = gpd.read_file(kml_file)

            else:
                # GeoJSON / KML biasa
                if filename.endswith(".kml"):
                    gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'rw'
                gdf = gpd.read_file(uploaded_file)

            # A. Ekstrak Data (Untuk Otak AI)
            crs_info = gdf.crs.name if gdf.crs else "Unknown CRS"
            geom_type = gdf.geom_type.unique().tolist()
            
            text_info = f"**Analisis Data Spasial (GIS):**\n"
            text_info += f"- Coordinate System: {crs_info}\n"
            text_info += f"- Tipe Geometri: {geom_type}\n"
            text_info += f"- Jumlah Fitur: {len(gdf)} entitas\n"
            text_info += f"- Kolom Data: {', '.join(gdf.columns)}\n"
            text_info += f"\n**Sample Data Atribut:**\n"
            text_info += gdf.drop(columns='geometry').head(5).to_markdown()

            # B. Render Peta (Untuk Mata AI)
            fig, ax = plt.subplots(figsize=(10, 10))
            gdf.plot(ax=ax, color='blue', alpha=0.5, edgecolor='black')
            plt.title(f"Visualisasi {filename}")
            plt.axis('off')
            
            image_buf = io.BytesIO()
            plt.savefig(image_buf, format='png', dpi=150)
            image_buf.seek(0)
            plt.close(fig)
            
            df_data = gdf # Simpan dataframe jika butuh analisa lanjut

        # --- 4. HANDLING GPX (GPS TRACK) ---
        elif filename.endswith(".gpx"):
            gpx = gpxpy.parse(uploaded_file)
            points = []
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        points.append({'lat': point.latitude, 'lon': point.longitude, 'ele': point.elevation})
            
            df_gpx = pd.DataFrame(points)
            
            text_info = f"**Analisis Data GPX (GPS):**\n"
            text_info += f"- Jumlah Titik Track: {len(df_gpx)}\n"
            text_info += f"- Elevasi Min/Max: {df_gpx['ele'].min()} m / {df_gpx['ele'].max()} m\n"
            
            # Plot Jalur
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(df_gpx['lon'], df_gpx['lat'], color='red', linewidth=2)
            plt.title("Jalur Tracking GPX")
            
            image_buf = io.BytesIO()
            plt.savefig(image_buf, format='png', dpi=100)
            image_buf.seek(0)
            plt.close(fig)

    except Exception as e:
        return f"Error membaca file {filename}: {str(e)}", None, None

    return text_info, image_buf, df_data
