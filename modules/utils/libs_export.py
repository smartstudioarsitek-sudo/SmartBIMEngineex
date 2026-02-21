import pandas as pd
from io import BytesIO
import numpy as np
import xlsxwriter

class Export_Engine:
    def __init__(self):
        pass

    def create_dxf(self, drawing_type, params):
        dxf = "0\nSECTION\n2\nENTITIES\n"
        
        def add_line(x1, y1, x2, y2, layer="STRUKTUR"):
            return f"0\nLINE\n8\n{layer}\n10\n{x1}\n20\n{y1}\n30\n0.0\n11\n{x2}\n21\n{y2}\n31\n0.0\n"
        
        def add_text(x, y, text, height=0.15, layer="TEXT"):
            return f"0\nTEXT\n8\n{layer}\n10\n{x}\n20\n{y}\n30\n0.0\n40\n{height}\n1\n{text}\n"
        
        def add_circle(x, y, radius, layer="BESI"):
            return f"0\nCIRCLE\n8\n{layer}\n10\n{x}\n20\n{y}\n30\n0.0\n40\n{radius}\n"

        if drawing_type == "BALOK":
            b = params['b'] / 1000; h = params['h'] / 1000; dia = params['dia'] / 1000
            # Beton
            dxf += add_line(0, 0, b, 0) + add_line(b, 0, b, h) + add_line(b, h, 0, h) + add_line(0, h, 0, 0)
            # Tulangan
            selimut = 0.04; y_pos = selimut + 0.01 + dia/2
            dxf += add_circle(selimut+0.01, y_pos, dia/2, "BESI") # Kiri
            dxf += add_circle(b-selimut-0.01, y_pos, dia/2, "BESI") # Kanan
            dxf += add_text(b/2-0.1, -0.2, f"{int(params['n'])} D{int(params['dia'])}")

        elif drawing_type == "FOOTPLATE":
            B = params['B']
            dxf += add_line(0, 0, B, 0) + add_line(B, 0, B, B) + add_line(B, B, 0, B) + add_line(0, B, 0, 0)
            dxf += add_text(B/2-0.2, -0.2, f"Pondasi {B}x{B}m")

        elif drawing_type == "TALUD":
            H = params['H']; Ba = params['Ba']; Bb = params['Bb']
            dxf += add_line(0, 0, Bb, 0) + add_line(Bb, 0, Bb, H) + add_line(Bb, H, Bb-Ba, H) + add_line(Bb-Ba, H, 0, 0)
            dxf += add_text(Bb/2, -0.5, f"Talud H={H}m")
            
        dxf += "0\nENDSEC\n0\nEOF"
        return dxf

    def create_excel_report(self, df_rab, session_data):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_rab.to_excel(writer, sheet_name='RAB Final', index=False)
            
            # Sheet Data Teknis
            tech_data = {'Parameter': ['Mutu Beton', 'Mutu Baja'], 'Nilai': [f"{session_data.get('fc',0)} MPa", f"{session_data.get('fy',0)} MPa"]}
            pd.DataFrame(tech_data).to_excel(writer, sheet_name='Data Teknis', index=False)
        return output.getvalue()

    def generate_7tab_rab_excel(self, project_name="Proyek Strategis Nasional"):
        """
        [MODUL 5D BIM]
        Auto-Chain Excel Generator untuk RAB (7 Tab PUPR Standard).
        Menginjeksi formula antar-sheet secara live.
        """
        output = BytesIO()
        # Inisialisasi Workbook
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # --- DEFINISI FORMAT / STYLING ---
        fmt_title = workbook.add_format({'bold': True, 'font_size': 14})
        fmt_header = workbook.add_format({'bold': True, 'bg_color': '#1E3A8A', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        fmt_border = workbook.add_format({'border': 1})
        fmt_currency = workbook.add_format({'num_format': 'Rp #,##0', 'border': 1})
        fmt_currency_bold = workbook.add_format({'num_format': 'Rp #,##0', 'border': 1, 'bold': True, 'bg_color': '#D1D5DB'})
        
        # --- MEMBUAT 7 SHEET SESUAI TUNTUTAN AUDITOR ---
        ws_rekap = workbook.add_worksheet('1. Rekap')
        ws_rab = workbook.add_worksheet('2. RAB')
        ws_boq = workbook.add_worksheet('3. Backup BOQ')
        ws_ahsp = workbook.add_worksheet('4. AHSP S2 30 2025')
        ws_smkk = workbook.add_worksheet('5. SMKK')
        ws_tkdn = workbook.add_worksheet('6. TKDN')
        ws_basic = workbook.add_worksheet('7. Basic Price')

        # =======================================================
        # TAB 7: BASIC PRICE (Sumber Mata Air Harga)
        # =======================================================
        ws_basic.set_column('B:B', 30)
        ws_basic.write('A1', 'DAFTAR HARGA DASAR UPAH & MATERIAL', fmt_title)
        
        headers_basic = ['No', 'Uraian', 'Satuan', 'Harga Dasar (Rp)']
        for col, h in enumerate(headers_basic): ws_basic.write(2, col, h, fmt_header)
        
        # Baris 4 (Index 3): Semen Portland
        ws_basic.write('A4', 1, fmt_border)
        ws_basic.write('B4', 'Semen Portland', fmt_border)
        ws_basic.write('C4', 'kg', fmt_border)
        ws_basic.write('D4', 1500, fmt_currency) # Harga Semen Rp 1.500/kg
        
        # Baris 5 (Index 4): Pekerja
        ws_basic.write('A5', 2, fmt_border)
        ws_basic.write('B5', 'Pekerja (Tukang)', fmt_border)
        ws_basic.write('C5', 'OH', fmt_border)
        ws_basic.write('D5', 150000, fmt_currency) # Upah Rp 150.000/hari

        # =======================================================
        # TAB 4: AHSP (Menarik harga dari Tab 7)
        # =======================================================
        ws_ahsp.set_column('B:B', 35)
        ws_ahsp.write('A1', 'ANALISA HARGA SATUAN PEKERJAAN (AHSP)', fmt_title)
        ws_ahsp.write('A2', 'Item: 1 m3 Pengecoran Beton K-300')
        
        headers_ahsp = ['Kategori', 'Uraian', 'Koefisien', 'Satuan', 'Harga Dasar', 'Subtotal']
        for col, h in enumerate(headers_ahsp): ws_ahsp.write(3, col, h, fmt_header)
        
        # Bahan: Semen
        ws_ahsp.write('A5', 'Bahan', fmt_border)
        ws_ahsp.write('B5', 'Semen Portland', fmt_border)
        ws_ahsp.write('C5', 413.0, fmt_border) # Koef K-300
        ws_ahsp.write('D5', 'kg', fmt_border)
        # SUNTIKAN RUMUS EXCEL 1: Ambil Harga dari Tab 7 Sel D4
        ws_ahsp.write_formula('E5', "='7. Basic Price'!D4", fmt_currency)
        ws_ahsp.write_formula('F5', "=C5*E5", fmt_currency) # Koef x Harga Dasar
        
        # Upah: Pekerja
        ws_ahsp.write('A6', 'Upah', fmt_border)
        ws_ahsp.write('B6', 'Pekerja', fmt_border)
        ws_ahsp.write('C6', 1.65, fmt_border) # Koef Upah
        ws_ahsp.write('D6', 'OH', fmt_border)
        # SUNTIKAN RUMUS EXCEL 2: Ambil Harga dari Tab 7 Sel D5
        ws_ahsp.write_formula('E6', "='7. Basic Price'!D5", fmt_currency)
        ws_ahsp.write_formula('F6', "=C6*E6", fmt_currency)
        
        # Total Harga Satuan (Sel F7)
        ws_ahsp.write('E7', 'Total Harga Satuan', fmt_header)
        ws_ahsp.write_formula('F7', "=SUM(F5:F6)", fmt_currency_bold)

        # =======================================================
        # TAB 3: BACKUP BOQ (Data dari Ekstraksi IFC/BIM)
        # =======================================================
        ws_boq.set_column('B:B', 30)
        ws_boq.write('A1', 'BACKUP BILL OF QUANTITIES (BOQ) DARI BIM IFC', fmt_title)
        
        headers_boq = ['No', 'Elemen IFC', 'Perhitungan Dimensi', 'Volume Total', 'Satuan']
        for col, h in enumerate(headers_boq): ws_boq.write(2, col, h, fmt_header)
        
        ws_boq.write('A4', 1, fmt_border)
        ws_boq.write('B4', 'IfcColumn (Kolom K1)', fmt_border)
        ws_boq.write('C4', '10 unit x (0.4m x 0.4m x 4m)', fmt_border)
        ws_boq.write('D4', 64.0, fmt_border) # Volume statis dari BIM
        ws_boq.write('E4', 'm3', fmt_border)

        # =======================================================
        # TAB 2: RAB (Menjahit Volume BOQ x Harga AHSP)
        # =======================================================
        ws_rab.set_column('B:B', 35)
        ws_rab.write('A1', f'RENCANA ANGGARAN BIAYA (RAB) - {project_name.upper()}', fmt_title)
        
        headers_rab = ['No', 'Uraian Pekerjaan', 'Volume', 'Satuan', 'Harga Satuan (Rp)', 'Total Harga (Rp)']
        for col, h in enumerate(headers_rab): ws_rab.write(2, col, h, fmt_header)
        
        ws_rab.write('A4', 'I', fmt_border)
        ws_rab.write('B4', 'PEKERJAAN BETON STRUKTURAL', fmt_border)
        
        # SUNTIKAN RUMUS EXCEL 3: Ambil Volume dari Tab 3 (BOQ) Sel D4
        ws_rab.write_formula('C4', "='3. Backup BOQ'!D4", fmt_border)
        ws_rab.write('D4', 'm3', fmt_border)
        # SUNTIKAN RUMUS EXCEL 4: Ambil Harga Satuan dari Tab 4 (AHSP) Sel F7
        ws_rab.write_formula('E4', "='4. AHSP S2 30 2025'!F7", fmt_currency)
        # Total = Volume x Harga Satuan
        ws_rab.write_formula('F4', "=C4*E4", fmt_currency)
        
        # Total Divisi (Sel F5)
        ws_rab.write('E5', 'TOTAL DIVISI STRUKTUR', fmt_header)
        ws_rab.write_formula('F5', "=SUM(F4:F4)", fmt_currency_bold)

        # =======================================================
        # TAB 1: REKAPITULASI (Termasuk PPN)
        # =======================================================
        ws_rekap.set_column('B:B', 35)
        ws_rekap.write('A1', 'REKAPITULASI BIAYA PROYEK', fmt_title)
        
        headers_rekap = ['No', 'Divisi Pekerjaan', 'Total Harga (Rp)']
        for col, h in enumerate(headers_rekap): ws_rekap.write(2, col, h, fmt_header)
        
        ws_rekap.write('A4', 1, fmt_border)
        ws_rekap.write('B4', 'Pekerjaan Struktur', fmt_border)
        # SUNTIKAN RUMUS EXCEL 5: Ambil Total Divisi dari Tab 2 (RAB) Sel F5
        ws_rekap.write_formula('C4', "='2. RAB'!F5", fmt_currency)
        
        # Rekap Final + PPN
        ws_rekap.write('B6', 'A. TOTAL BIAYA FISIK', fmt_header)
        ws_rekap.write_formula('C6', "=SUM(C4:C4)", fmt_currency_bold)
        
        ws_rekap.write('B7', 'B. PPN 11%', fmt_header)
        ws_rekap.write_formula('C7', "=C6 * 0.11", fmt_currency_bold) # Hitung PPN Otomatis
        
        ws_rekap.write('B8', 'C. GRAND TOTAL (A + B)', fmt_header)
        ws_rekap.write_formula('C8', "=C6 + C7", fmt_currency_bold)

        # =======================================================
        # TAB 5 (SMKK) & TAB 6 (TKDN) - Placeholder
        # =======================================================
        ws_smkk.write('A1', 'RENCANA BIAYA PENERAPAN SMKK (K3)', fmt_title)
        ws_smkk.write('A3', 'Data biaya K3 akan ter-generate di sini pada modul penuh.')
        
        ws_tkdn.write('A1', 'PERHITUNGAN TINGKAT KOMPONEN DALAM NEGERI (TKDN)', fmt_title)
        ws_tkdn.write('A3', 'Data proporsi material lokal vs impor dihitung di sini.')

        workbook.close()
        return output.getvalue()
