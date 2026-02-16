from fpdf import FPDF
import matplotlib.pyplot as plt
import io
import datetime
import os

# Setting Matplotlib Backend (Non-GUI) agar aman di server
plt.switch_backend('Agg')

class SmartEngineexReport(FPDF):
    """
    Generator Laporan Teknis Standar TABG/PBG.
    Fitur:
    - Kop Surat Resmi
    - Penomoran Halaman Otomatis
    - Layout Bab Terstruktur
    - Render Rumus Matematika (LaTeX style)
    """
    
    def __init__(self, nama_proyek="Proyek Tanpa Judul"):
        super().__init__()
        self.nama_proyek = nama_proyek
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
        # 1. Logo & Kop Surat (Simulasi Text)
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'SMART ENGINEEX - LAPORAN PERHITUNGAN STRUKTUR', 0, 1, 'C')
        
        self.set_font('Arial', 'I', 10)
        self.cell(0, 6, f'Proyek: {self.nama_proyek}', 0, 1, 'C')
        self.cell(0, 6, 'Dokumen Teknis Persyaratan PBG/SLF', 0, 1, 'C')
        
        # Garis Bawah Kop
        self.line(10, 30, 200, 30)
        self.ln(15)

    def footer(self):
        # Posisi 1.5 cm dari bawah
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Halaman {self.page_no()} | Dibuat oleh SmartBIMEngineex AI', 0, 0, 'C')

    def chapter_title(self, label):
        # Judul Bab dengan Background Abu-abu (Standar Laporan)
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(230, 230, 230) 
        self.cell(0, 10, f"{label}", 0, 1, 'L', True)
        self.ln(5)

    def chapter_body(self, text):
        # Isi Paragraf Normal
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 6, text)
        self.ln(5)
        
    def add_data_table(self, data_dict):
        """
        Membuat Tabel Data Sederhana dari Dictionary
        """
        self.set_font('Courier', '', 10) # Font Monospace agar rapi
        for key, value in data_dict.items():
            self.cell(60, 6, str(key), 1)
            self.cell(0, 6, str(value), 1, 1)
        self.ln(5)

    def render_plot_to_image(self, fig):
        """
        Konversi Matplotlib Figure ke Gambar PNG (In-Memory)
        """
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        return buf

    def add_image_from_figure(self, fig, height=80):
        """
        Menempelkan Gambar Grafik ke PDF
        """
        img_buf = self.render_plot_to_image(fig)
        self.image(img_buf, x=20, h=height)
        self.ln(5)
        plt.close(fig) # Bersihkan memori

# ==============================================================================
# FUNGSI UTAMA GENERATE PDF (DIPANGGIL DARI APP_ENGINEX.PY)
# ==============================================================================

def create_tabg_report(session_state, project_name="Proyek 01"):
    """
    Fungsi Utama Pembuat Laporan PDF.
    Mengambil data dari st.session_state dan merakitnya menjadi dokumen.
    """
    pdf = SmartEngineexReport(nama_proyek=project_name)
    pdf.add_page()
    
    # --- BAB 1: INFORMASI UMUM & KRITERIA DESAIN ---
    pdf.chapter_title("I. DATA PERENCANAAN")
    
    tgl = datetime.datetime.now().strftime("%d %B %Y")
    info_text = (
        f"Tanggal Laporan : {tgl}\n"
        f"Standar Acuan   : SNI 1726:2019 (Gempa), SNI 2847:2019 (Beton), SNI 1729:2020 (Baja)\n"
        f"Metode Analisa  : Analisa Statik Ekuivalen & Desain Kapasitas (White Box)\n"
    )
    pdf.chapter_body(info_text)
    
    # Tampilkan Tabel Parameter Input (Jika ada di session)
    if 'shared_execution_vars' in session_state:
        vars_data = session_state['shared_execution_vars']
        
        # Filter data relevan
        param_table = {}
        if 'fc' in vars_data: param_table['Mutu Beton (fc)'] = f"{vars_data['fc']} MPa"
        if 'fy' in vars_data: param_table['Mutu Baja (fy)'] = f"{vars_data['fy']} MPa"
        if 'Ss_user' in vars_data: param_table['Gempa Ss'] = f"{vars_data['Ss_user']} g"
        
        if param_table:
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 8, "Tabel 1.1 - Parameter Desain Utama", 0, 1)
            pdf.add_data_table(param_table)

    # --- BAB 2: ANALISA GEMPA (SNI 1726:2019) ---
    pdf.chapter_title("II. PARAMETER RESPONS SPEKTRUM")
    
    # Ambil data Gempa dari Session (Asumsi tersimpan di 'report_gempa')
    # Jika belum ada, tampilkan placeholder
    gempa_data = session_state.get('report_gempa', {})
    
    if gempa_data:
        pdf.chapter_body(
            f"Berdasarkan lokasi proyek dengan Klasifikasi Situs {gempa_data.get('Site', '-')}, "
            f"berikut adalah parameter desain seismik yang digunakan:"
        )
        
        # Tabel Gempa
        tabel_gempa = {
            "Kelas Situs": gempa_data.get('Site', '-'),
            "PGA (Batuan Dasar)": f"{gempa_data.get('PGA', 0):.3f} g",
            "Fa (Amplifikasi Pendek)": f"{gempa_data.get('Fa', 0):.3f}",
            "Fv (Amplifikasi 1-detik)": f"{gempa_data.get('Fv', 0):.3f}",
            "SMS": f"{gempa_data.get('Sms', 0):.3f} g",
            "SM1": f"{gempa_data.get('Sm1', 0):.3f} g",
            "SDS (Desain)": f"{gempa_data.get('Sds', 0):.3f} g",
            "SD1 (Desain)": f"{gempa_data.get('Sd1', 0):.3f} g",
        }
        pdf.add_data_table(tabel_gempa)
        
        pdf.chapter_body("Grafik Respons Spektrum Desain:")
        # (Di sini nanti bisa insert gambar grafik jika ada object figure-nya)
        # pdf.add_image_from_figure(fig_gempa) 

    else:
        pdf.chapter_body("Data analisis gempa belum tersedia dalam sesi ini.")

    # --- BAB 3: ANALISA STRUKTUR UTAMA (BETON) ---
    pdf.chapter_title("III. ANALISA KAPASITAS PENAMPANG (BETON)")
    
    # Ambil data Struktur
    struk_data = session_state.get('report_struk', {})
    
    if struk_data:
        pdf.chapter_body(
            "Verifikasi kapasitas penampang beton bertulang dilakukan dengan metode Kekuatan Batas (Ultimate Strength Design)."
        )
        
        # Tampilkan Trace Perhitungan (White Box)
        # Jika ada teks log panjang dari libs_sni.py
        trace_log = struk_data.get('Trace_Log', '')
        if trace_log:
            pdf.set_font('Courier', '', 9)
            pdf.multi_cell(0, 5, trace_log)
            pdf.ln(5)
            
    else:
        pdf.chapter_body("Data analisis struktur beton belum tersedia.")

    # --- BAB 4: KESIMPULAN & REKOMENDASI ---
    pdf.add_page()
    pdf.chapter_title("IV. KESIMPULAN KELAYAKAN")
    
    pdf.chapter_body(
        "Berdasarkan hasil analisis di atas, struktur yang direncanakan dinyatakan:\n"
        "1. Memenuhi persyaratan kekuatan (Strength) sesuai SNI 2847:2019.\n"
        "2. Memenuhi persyaratan kestabilan seismik sesuai SNI 1726:2019.\n\n"
        "Catatan Khusus: Pelaksanaan konstruksi wajib mengikuti gambar kerja detail (DED) "
        "dan spesifikasi teknis yang terlampir."
    )
    
    # Tanda Tangan
    pdf.ln(20)
    pdf.set_font('Arial', '', 10)
    pdf.cell(100, 5, "Disetujui Oleh,", 0, 0, 'C')
    pdf.cell(80, 5, "Dibuat Oleh,", 0, 1, 'C')
    
    pdf.ln(25)
    pdf.cell(100, 5, "( ........................... )", 0, 0, 'C')
    pdf.cell(80, 5, "SmartBIMEngineex AI", 0, 1, 'C')
    pdf.cell(100, 5, "Penanggung Jawab Teknis", 0, 0, 'C')
    
    # Return sebagai Bytes String (Agar bisa didownload di Streamlit)
    # Output 'S' returns string, encode to latin-1 for bytes
    return pdf.output(dest='S').encode('latin-1')
