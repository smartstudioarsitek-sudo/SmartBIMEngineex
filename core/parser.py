# FILE: core/parser.py
import streamlit as st
import ifcopenshell
import ifcopenshell.util.element as Element
import pandas as pd
import tempfile
import os

# Mencoba import mapping yang sudah ada di folder modules/utils/
try:
    from modules.utils.mapping import get_indonesian_name
except ImportError:
    # Fallback jika gagal import
    def get_indonesian_name(x): return x

class IFCParser:
    
    @staticmethod
    @st.cache_resource(show_spinner="⚙️ Sedang membedah struktur file IFC...", ttl=3600)
    def load_ifc(uploaded_file):
        """Memuat file IFC fisik ke tempfile agar hemat RAM."""
        try:
            # Trik Tempfile untuk IfcOpenShell (Wajib untuk Streamlit Cloud)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            
            model = ifcopenshell.open(tmp_path)
            return model
        except Exception as e:
            st.error(f"❌ Critical Error saat memuat IFC: {e}")
            return None

    @staticmethod
    @st.cache_data(show_spinner="📊 Mengompilasi Bill of Quantities (BoQ)...")
    def extract_metadata(_model):
        """Ekstraksi Data untuk Tabel (DataFrame)."""
        data = []
        # Ambil semua produk fisik
        elements = _model.by_type("IfcProduct")
        
        # Limitasi visual untuk performa (Opsional, bisa dilepas)
        total_items = len(elements)
        
        progress_bar = st.progress(0)
        
        for i, el in enumerate(elements):
            if i % 100 == 0: # Update progress tiap 100 item
                progress_bar.progress(min(i / total_items, 1.0))

            # Mapping Nama (IfcWall -> Dinding)
            kategori_indo = get_indonesian_name(el.is_a())
            
            # Ambil Quantity (Volume/Luas)
            psets = Element.get_psets(el)
            vol = 0.0
            area = 0.0
            
            # Logic pintar cari volume di berbagai Pset
            for pset_name, pset_data in psets.items():
                if 'Qto' in pset_name or 'BaseQuantities' in pset_name:
                    vol = pset_data.get('NetVolume', pset_data.get('Volume', vol))
                    area = pset_data.get('NetArea', pset_data.get('Area', area))

            data.append({
                "GlobalId": el.GlobalId,
                "Kategori": kategori_indo,
                "Nama Elemen": el.Name if el.Name else "-",
                "Lantai": Element.get_container(el).Name if Element.get_container(el) else "N/A",
                "Volume (m3)": round(vol, 3),
                "Luas (m2)": round(area, 2)
            })
            
        progress_bar.empty()
        return pd.DataFrame(data)
