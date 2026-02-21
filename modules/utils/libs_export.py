# modules/utils/libs_export.py
import pandas as pd
from io import BytesIO
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
        
        if drawing_type == "BALOK":
            b = params['b'] / 1000; h = params['h'] / 1000
            dxf += add_line(0, 0, b, 0) + add_line(b, 0, b, h) + add_line(b, h, 0, h) + add_line(0, h, 0, 0)
            dxf += add_text(b/2-0.1, -0.2, "Detail Balok")
        dxf += "0\nENDSEC\n0\nEOF"
        return dxf

    def generate_7tab_rab_excel(self, project_name="Proyek Strategis Nasional", df_boq=None):
        """
        Auto-Chain Excel Generator yang menerima DATA ASLI dari ekstraksi IFC.
        """
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # --- DEFINISI FORMAT ---
        fmt_title = workbook.add_format({'bold': True, 'font_size': 14})
        fmt_header = workbook.add_format({'bold': True, 'bg_color': '#1E3A8A', 'font_color': 'white', 'border': 1, 'align': 'center'})
        fmt_border = workbook.add_format({'border': 1})
        fmt_currency = workbook.add_format({'num_format': 'Rp #,##0', 'border': 1})
        fmt_currency_bold = workbook.add_format({'num_format': 'Rp #,##0', 'border': 1, 'bold': True, 'bg_color': '#D1D5DB'})
        
        # --- MEMBUAT 7 SHEET ---
        ws_rekap = workbook.add_worksheet('1. Rekap')
        ws_rab = workbook.add_worksheet('2. RAB')
        ws_boq = workbook.add_worksheet('3. Backup BOQ')
        ws_ahsp = workbook.add_worksheet('4. AHSP S2 30 2025')
        ws_smkk = workbook.add_worksheet('5. SMKK')
        ws_tkdn = workbook.add_worksheet('6. TKDN')
        ws_basic = workbook.add_worksheet('7. Basic Price')

        # =======================================================
        # TAB 7: BASIC PRICE & TAB 4: AHSP (Sama seperti sebelumnya)
        # =======================================================
        ws_basic.set_column('B:B', 30)
        ws_basic.write('A1', 'DAFTAR HARGA DASAR UPAH & MATERIAL', fmt_title)
        for col, h in enumerate(['No', 'Uraian', 'Satuan', 'Harga Dasar (Rp)']): ws_basic.write(2, col, h, fmt_header)
        ws_basic.write('A4', 1, fmt_border); ws_basic.write('B4', 'Semen Portland', fmt_border); ws_basic.write('C4', 'kg', fmt_border); ws_basic.write('D4', 1500, fmt_currency)
        ws_basic.write('A5', 2, fmt_border); ws_basic.write('B5', 'Pekerja (Tukang)', fmt_border); ws_basic.write('C5', 'OH', fmt_border); ws_basic.write('D5', 150000, fmt_currency)

        ws_ahsp.set_column('B:B', 35)
        ws_ahsp.write('A1', 'ANALISA HARGA SATUAN PEKERJAAN (AHSP)', fmt_title)
        ws_ahsp.write('A2', 'Item: 1 m3 Pengecoran Beton K-300')
        for col, h in enumerate(['Kategori', 'Uraian', 'Koefisien', 'Satuan', 'Harga Dasar', 'Subtotal']): ws_ahsp.write(3, col, h, fmt_header)
        
        ws_ahsp.write('A5', 'Bahan', fmt_border); ws_ahsp.write('B5', 'Semen', fmt_border); ws_ahsp.write('C5', 413.0, fmt_border); ws_ahsp.write('D5', 'kg', fmt_border)
        ws_ahsp.write_formula('E5', "='7. Basic Price'!D4", fmt_currency); ws_ahsp.write_formula('F5', "=C5*E5", fmt_currency)
        
        ws_ahsp.write('A6', 'Upah', fmt_border); ws_ahsp.write('B6', 'Pekerja', fmt_border); ws_ahsp.write('C6', 1.65, fmt_border); ws_ahsp.write('D6', 'OH', fmt_border)
        ws_ahsp.write_formula('E6', "='7. Basic Price'!D5", fmt_currency); ws_ahsp.write_formula('F6', "=C6*E6", fmt_currency)
        
        ws_ahsp.write('E7', 'Total Harga Satuan', fmt_header); ws_ahsp.write_formula('F7', "=SUM(F5:F6)", fmt_currency_bold)

        # =======================================================
        # TAB 3 & 2: INJEKSI DATA ASLI IFC (DINAMIS)
        # =======================================================
        ws_boq.set_column('B:C', 30)
        ws_boq.write('A1', 'BACKUP BILL OF QUANTITIES (BOQ) DARI BIM IFC', fmt_title)
        for col, h in enumerate(['No', 'Kategori IFC', 'Nama Elemen', 'Volume (m3)']): ws_boq.write(2, col, h, fmt_header)

        ws_rab.set_column('B:B', 40)
        ws_rab.write('A1', f'RENCANA ANGGARAN BIAYA (RAB) - {project_name.upper()}', fmt_title)
        for col, h in enumerate(['No', 'Elemen Struktur', 'Volume', 'Satuan', 'Harga Satuan (Rp)', 'Total Harga (Rp)']): ws_rab.write(2, col, h, fmt_header)

        baris_terakhir_rab = 3

        if df_boq is not None and not df_boq.empty:
            for index, row in df_boq.iterrows():
                row_excel = index + 3 # Mulai dari baris ke-4
                
                # Tulis Data Asli ke Tab BOQ
                ws_boq.write(row_excel, 0, index + 1, fmt_border)
                ws_boq.write(row_excel, 1, str(row['Kategori']), fmt_border)
                ws_boq.write(row_excel, 2, str(row['Nama']), fmt_border)
                ws_boq.write(row_excel, 3, float(row['Volume']), fmt_border)
                
                # Tulis Rumus Auto-Chain ke Tab RAB
                ws_rab.write(row_excel, 0, index + 1, fmt_border)
                ws_rab.write(row_excel, 1, f"Pengecoran {row['Nama']}", fmt_border)
                
                # Ambil Volume dari Tab BOQ
                ws_rab.write_formula(row_excel, 2, f"='3. Backup BOQ'!D{row_excel+1}", fmt_border)
                ws_rab.write(row_excel, 3, 'm3', fmt_border)
                
                # Ambil Harga Satuan dari Tab AHSP
                ws_rab.write_formula(row_excel, 4, "='4. AHSP S2 30 2025'!F7", fmt_currency)
                
                # Kalikan Volume x Harga
                ws_rab.write_formula(row_excel, 5, f"=C{row_excel+1}*E{row_excel+1}", fmt_currency)
                baris_terakhir_rab = row_excel

        # Total RAB
        ws_rab.write(baris_terakhir_rab + 1, 4, 'TOTAL BIAYA STRUKTUR', fmt_header)
        ws_rab.write_formula(baris_terakhir_rab + 1, 5, f"=SUM(F4:F{baris_terakhir_rab+1})", fmt_currency_bold)

        # =======================================================
        # TAB 1: REKAPITULASI (Termasuk PPN)
        # =======================================================
        ws_rekap.set_column('B:B', 35)
        ws_rekap.write('A1', 'REKAPITULASI BIAYA PROYEK', fmt_title)
        for col, h in enumerate(['No', 'Divisi Pekerjaan', 'Total Harga (Rp)']): ws_rekap.write(2, col, h, fmt_header)
        
        ws_rekap.write('A4', 1, fmt_border)
        ws_rekap.write('B4', 'Pekerjaan Beton Struktur', fmt_border)
        # Ambil Total dari Tab RAB
        ws_rekap.write_formula('C4', f"='2. RAB'!F{baris_terakhir_rab + 2}", fmt_currency)
        
        ws_rekap.write('B6', 'A. TOTAL BIAYA FISIK', fmt_header)
        ws_rekap.write_formula('C6', "=SUM(C4:C4)", fmt_currency_bold)
        
        ws_rekap.write('B7', 'B. PPN 11%', fmt_header)
        ws_rekap.write_formula('C7', "=C6 * 0.11", fmt_currency_bold) 
        
        ws_rekap.write('B8', 'C. GRAND TOTAL (A + B)', fmt_header)
        ws_rekap.write_formula('C8', "=C6 + C7", fmt_currency_bold)

        ws_smkk.write('A1', 'TAB SMKK & TKDN UNDER CONSTRUCTION', fmt_title)
        ws_tkdn.write('A1', 'TAB SMKK & TKDN UNDER CONSTRUCTION', fmt_title)

        workbook.close()
        return output.getvalue()
