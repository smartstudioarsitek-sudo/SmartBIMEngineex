import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
import io

def process_dxf_for_ai(dxf_file_bytes):
    # 1. Baca File DXF dari Memory
    doc = ezdxf.readfile(io.BytesIO(dxf_file_bytes))
    msp = doc.modelspace()
    
    # --- JALUR A: Render Image Super Tajam ---
    # Setup rendering context
    fig = plt.figure()
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    Frontend(ctx, out).draw_layout(msp, finalize=True)
    
    # Simpan ke Buffer Gambar (High DPI)
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', dpi=300) # 300 DPI = Tajam!
    img_buffer.seek(0)
    plt.close(fig)
    
    # --- JALUR B: Ekstrak Teks Murni (Data Mentah) ---
    extracted_texts = []
    
    # Ambil Teks Biasa (TEXT & MTEXT)
    for entity in msp.query('TEXT MTEXT'):
        extracted_texts.append(f"Teks: {entity.dxf.text} (Posisi: {entity.dxf.insert})")
        
    # Ambil Dimensi (DIMENSION) - Ini Kuncinya!
    for dim in msp.query('DIMENSION'):
        # Kadang nilai dimensi ada di text_override, kadang di actual measurement
        measurement = dim.dxf.text if dim.dxf.text else f"{dim.get_measurement():.2f}"
        extracted_texts.append(f"Dimensi: {measurement}")

    text_data_context = "\n".join(extracted_texts[:200]) # Ambil 200 sampel pertama agar tidak overload token
    
    return img_buffer, text_data_context

# --- CONTOH INTEGRASI DI STREAMLIT ---
# uploaded_file = st.file_uploader("Upload DXF", type=["dxf"])
# if uploaded_file:
#     image_data, text_data = process_dxf_for_ai(uploaded_file.read())
#     
#     # Tampilkan Gambar Hasil Render
#     st.image(image_data, caption="Rendered CAD View")
#     
#     # Kirim ke Gemini
#     prompt = f"""
#     Analisis gambar denah ini.
#     Gunakan DATA PRESISI berikut untuk dimensi (JANGAN TEBAK SENDIRI):
#     {text_data}
#     """
#     model.generate_content([prompt, Image.open(image_data)])
# ... imports sama ...

def extract_text_recursive(entity, container_list):
    """Fungsi pembantu untuk masuk ke dalam BLOCK"""
    if entity.dxftype() in ['TEXT', 'MTEXT']:
        container_list.append(f"Teks: {entity.dxf.text}")
    elif entity.dxftype() == 'DIMENSION':
         measurement = entity.dxf.text if entity.dxf.text else f"{entity.get_measurement():.2f}"
         container_list.append(f"Dimensi: {measurement}")
    elif entity.dxftype() == 'INSERT':
        # INI KUNCINYA: Jika ketemu Block, masuk ke dalamnya!
        block_layout = entity.block()
        for sub_entity in block_layout:
            extract_text_recursive(sub_entity, container_list)

def process_dxf_for_ai(dxf_file_bytes):
    doc = ezdxf.readfile(io.BytesIO(dxf_file_bytes))
    msp = doc.modelspace()
    
    # ... (Bagian render gambar sudah oke) ...
    
    extracted_texts = []
    
    # Iterasi semua entity, termasuk yang di dalam BLOCK
    for entity in msp:
        extract_text_recursive(entity, extracted_texts)

    # Filter sampah (misal teks copyright Autodesk)
    clean_texts = [t for t in extracted_texts if "Autodesk" not in t and "Produced by" not in t]
    
    text_data_context = "\n".join(clean_texts[:300]) # Naikkan limit sedikit
    
    return img_buffer, text_data_context
