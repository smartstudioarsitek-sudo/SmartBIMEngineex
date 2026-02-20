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
            
            # FIX: Gunakan .read() dari memori (StringIO) agar tidak crash di Streamlit Cloud
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

        # --- HANDLING LAINNYA (Placeholder biar tidak error) ---
        else:
            text_info = "Format file belum didukung penuh oleh visualizer, namun data mentah telah diterima."

    except Exception as e:
        return f"Gagal membaca struktur file: {str(e)}", None, None

    return text_info, image_buf, df_data
