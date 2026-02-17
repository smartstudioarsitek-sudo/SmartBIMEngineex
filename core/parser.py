# core/parser.py
import streamlit as st
import ifcopenshell
import ifcopenshell.util.element as Element
import pandas as pd
import tempfile
import os
from utils.mapping import get_indonesian_name

class IFCParser:
    
    @staticmethod
    @st.cache_resource(show_spinner="⚙️ Sedang membedah struktur file IFC...", ttl=3600)
    def load_ifc(uploaded_file):
        """
        Memuat file IFC secara fisik ke tempfile untuk stabilitas memori.
        Menggunakan cache_resource karena object 'file' IFC tidak bisa di-pickle.
        TTL 3600 detik = Cache hilang setelah 1 jam (Mencegah memory leak).
        """
        try:
            # Membuat file sementara agar ifcopenshell bisa membaca path fisik
            # Ini lebih robust daripada membaca bytes stream langsung
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            
            # Membuka file menggunakan path
            model = ifcopenshell.open(tmp_path)
            
            # Opsional: Hapus file temp setelah diload ke memori C++ IfcOpenShell
            # os.unlink(tmp_path) 
            return model
            
        except Exception as e:
            st.error(f"❌ Critical Error saat memuat IFC: {e}")
            return None

    @staticmethod
    @st.cache_data(show_spinner="📊 Mengompilasi Bill of Quantities (BoQ)...")
    def extract_metadata(_model):
        """
        Ekstraksi Data Non-Geometris (Lazy Loading).
        Hanya mengambil Property Set (Pset) untuk tabel.
        Menggunakan cache_data karena Outputnya DataFrame (Serializable).
        """
        data = []
        
        # Ambil semua elemen fisik bangunan
        elements = _model.by_type("IfcProduct")
        
        total_items = len(elements)
        progress_bar = st.progress(0)
        
        for i, el in enumerate(elements):
            # Update progress bar setiap 10% agar tidak memperlambat loop
            if i % (total_items // 10 + 1) == 0:
                progress_bar.progress(i / total_items)

            # Klasifikasi Bahasa Indonesia
            kategori_asli = el.is_a()
            kategori_indo = get_indonesian_name(kategori_asli)
            
            # Ambil properti dasar (Volume, Luas, dll jika ada di Qto)
            # Menggunakan utilitas standar IfcOpenShell untuk stabilitas
            psets = Element.get_psets(el)
            
            # Mencari Quantities (Qto)
            volume = 0.0
            area = 0.0
            
            # Logika pencarian Volume/Area di berbagai Pset standar
            for pset_name, pset_data in psets.items():
                if 'Qto' in pset_name or 'BaseQuantities' in pset_name:
                    if 'NetVolume' in pset_data: volume = pset_data['NetVolume']
                    elif 'Volume' in pset_data: volume = pset_data['Volume']
                    
                    if 'NetArea' in pset_data: area = pset_data['NetArea']
                    elif 'Area' in pset_data: area = pset_data['Area']

            data.append({
                "GlobalId": el.GlobalId,
                "Kategori": kategori_indo,
                "Nama Elemen": el.Name if el.Name else "Tanpa Nama",
                "Lantai": Element.get_container(el).Name if Element.get_container(el) else "N/A",
                "Volume (m3)": round(volume, 3) if volume else 0,
                "Luas (m2)": round(area, 2) if area else 0,
                "RawType": kategori_asli
            })
            
        progress_bar.empty() # Hapus progress bar setelah selesai
        
        df = pd.DataFrame(data)
        return df
