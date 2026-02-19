import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
import io
import logging
import re

# Matikan log ezdxf yang berisik
logging.getLogger("ezdxf").setLevel(logging.ERROR)

def extract_text_recursive(entity, container_list, visited_blocks=None):
    """
    Menggali teks di dalam Block/Group secara rekursif.
    """
    if visited_blocks is None: visited_blocks = set()

    try:
        dxftype = entity.dxftype()
        
        # 1. TEXT & MTEXT
        if dxftype in ['TEXT', 'MTEXT']:
            raw_text = entity.dxf.text
            # Bersihkan format AutoCAD yang aneh (misal \A1; \P)
            clean_text = re.sub(r'\\P|\\A1;|\\C\d+;|{|}|\\f.*?;', ' ', raw_text)
            clean_text = clean_text.replace("%%c", "Ø").replace("%%d", "°").strip()
            if clean_text: container_list.append(f"Teks: {clean_text}")
            
        # 2. DIMENSION
        elif dxftype == 'DIMENSION':
            text = entity.dxf.text
            if not text or text == "<>": # <> artinya pakai nilai asli
                try: text = f"{entity.get_measurement():.2f}"
                except: text = "?"
            container_list.append(f"Dimensi: {text}")
            
        # 3. INSERT (BLOCK)
        elif dxftype == 'INSERT':
            block_name = entity.dxf.name
            if block_name not in visited_blocks:
                visited_blocks.add(block_name)
                if entity.doc:
                    block_layout = entity.block()
                    for sub_entity in block_layout:
                        extract_text_recursive(sub_entity, container_list, visited_blocks)
    except:
        pass

def parse_raw_dxf_text(content_str):
    """
    FALLBACK: Jika ezdxf gagal total, kita cari teks secara manual (Regex).
    DXF menyimpan teks dengan kode group '1'.
    """
    found_texts = []
    # Pola: kode grup 1 diikuti teks (DXF text value)
    # Ini mencari baris angka 1, lalu baris berikutnya adalah teksnya
    lines = content_str.split('\n')
    for i, line in enumerate(lines):
        if line.strip() == '1' and i + 1 < len(lines):
            text_candidate = lines[i+1].strip()
            # Filter sampah CAD
            if len(text_candidate) > 2 and not text_candidate.startswith(('AcDb', 'Autodesk', '{')):
                found_texts.append(f"RawData: {text_candidate}")
    return found_texts

def process_dxf_for_ai(dxf_file_bytes):
    img_buffer = None
    extracted_texts = []
    status_msg = ""
    
    # 1. COBA DECODE (Handling Encoding Windows vs UTF8)
    # DXF lama biasanya pakai 'cp1252' (Windows Latin), bukan utf-8.
    try:
        dxf_content_str = dxf_file_bytes.decode('cp1252')
    except:
        try:
            dxf_content_str = dxf_file_bytes.decode('utf-8', errors='ignore')
        except:
            return None, "Gagal decode file. Format binary tidak didukung."

    # 2. COBA BACA PAKAI EZDXF (Cara Normal)
    try:
        # Gunakan stream text, bukan bytes, agar lebih aman
        doc = ezdxf.read(io.StringIO(dxf_content_str))
        msp = doc.modelspace()
        
        # A. Coba Render Gambar
        try:
            fig = plt.figure(facecolor='#2d2d2d')
            ax = fig.add_axes([0, 0, 1, 1])
            ctx = RenderContext(doc)
            out = MatplotlibBackend(ax)
            Frontend(ctx, out).draw_layout(msp, finalize=True)
            
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='png', dpi=150, facecolor='#2d2d2d')
            img_buffer.seek(0)
            plt.close(fig)
        except Exception as e:
            status_msg += f"[Visual Gagal: {str(e)}] "
            img_buffer = None

        # B. Ekstrak Teks Terstruktur
        visited = set()
        for entity in msp:
            extract_text_recursive(entity, extracted_texts, visited)
            
    except Exception as e:
        # 3. JIKA GAGAL: JALUR DARURAT (Regex Parsing)
        status_msg += f"[Mode Darurat Aktif: {str(e)}] "
        extracted_texts = parse_raw_dxf_text(dxf_content_str)

    # 4. FINALISASI DATA
    # Hapus duplikat dan urutkan
    unique_texts = sorted(list(set(extracted_texts)))
    
    # Ambil sampel agar token AI tidak meledak
    final_context = "\n".join(unique_texts[:500])
    
    if not final_context:
        final_context = "File DXF terbaca tapi tidak ditemukan teks/dimensi. (Kemungkinan gambar hanya garis murni)."
    
    return img_buffer, f"Status: {status_msg}\n\nDATA TEKNIS:\n{final_context}"


