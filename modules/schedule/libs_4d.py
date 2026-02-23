# ==============================================================================
# 📄 NAMA FILE: libs_4d.py
# 📍 LOKASI: modules/schedule/libs_4d.py
# 🛠️ FUNGSI: 4D BIM Scheduling, Gantt Chart, CPM (NetworkX), & Kurva-S
# ==============================================================================

import pandas as pd
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import math

class Schedule_4D_Engine:
    def __init__(self):
        self.engine_name = "SmartBIM 4D Schedule & S-Curve Engine"
        
        # Asumsi Produktivitas Tenaga Kerja (Sederhana dari AHSP)
        # Format: (Kapasitas harian, Satuan)
        self.produktivitas = {
            "Pembersihan Lahan": 500,  # m2 / hari
            "Galian Tanah": 50,        # m3 / hari
            "Pondasi": 15,             # m3 / hari
            "Struktur Beton": 20,      # m3 / hari
            "Pekerjaan Baja": 1000,    # kg / hari
            "Dinding & Plester": 40,   # m2 / hari
            "Atap & Plafon": 50,       # m2 / hari
            "MEP": 1,                  # ls / hari (Asumsi per lantai/zona)
            "Finishing": 30            # m2 / hari
        }

    # ==========================================
    # 1. AUTO WBS & CPM CALCULATOR
    # ==========================================
    def hitung_cpm_dan_jadwal(self, df_boq, tanggal_mulai_str="2026-03-01"):
        """
        Mengubah BOQ menjadi WBS, menghitung durasi berdasarkan produktivitas, 
        lalu menentukan Jalur Kritis (CPM) dengan NetworkX.
        """
        try:
            start_date = datetime.strptime(tanggal_mulai_str, "%Y-%m-%d")
            total_biaya_proyek = df_boq['Total Harga (Rp)'].sum()
            
            wbs_data = []
            
            # 1. Mengubah BOQ menjadi Task (WBS) dan Estimasi Durasi
            for index, row in df_boq.iterrows():
                task_name = row['Nama Pekerjaan']
                vol = row['Volume']
                biaya = row['Total Harga (Rp)']
                
                # Hitung Bobot (%)
                bobot = (biaya / total_biaya_proyek) * 100 if total_biaya_proyek > 0 else 0
                
                # Tentukan Produktivitas (Fuzzy Matching sederhana)
                kapasitas_per_hari = 10 # Default
                for key, prod in self.produktivitas.items():
                    if key.lower() in task_name.lower() or key.split()[0].lower() in task_name.lower():
                        kapasitas_per_hari = prod
                        break
                
                # Hitung Durasi (Minimal 1 hari)
                durasi = math.ceil(vol / kapasitas_per_hari)
                durasi = max(1, durasi)
                
                wbs_data.append({
                    "Task ID": f"T-{index+1}",
                    "Task": task_name,
                    "Volume": vol,
                    "Durasi (Hari)": durasi,
                    "Bobot (%)": round(bobot, 2),
                    "Biaya (Rp)": biaya,
                    "Predecessor": f"T-{index}" if index > 0 else None # Asumsi sekuensial sederhana (Finish-to-Start)
                })
                
            df_wbs = pd.DataFrame(wbs_data)
            
            # 2. Perhitungan CPM menggunakan NetworkX
            G = nx.DiGraph()
            for index, row in df_wbs.iterrows():
                G.add_node(row['Task ID'], duration=row['Durasi (Hari)'], task=row['Task'])
                if pd.notna(row['Predecessor']):
                    preds = str(row['Predecessor']).split(',')
                    for p in preds:
                        p = p.strip()
                        if p in G.nodes:
                            G.add_edge(p, row['Task ID'])
                            
            # Menghitung Early Start (ES) dan Early Finish (EF)
            es = {}
            ef = {}
            for node in nx.topological_sort(G):
                dur = G.nodes[node]['duration']
                preds = list(G.predecessors(node))
                if not preds:
                    es[node] = start_date
                else:
                    # Cari tanggal selesai paling akhir dari pendahulu
                    max_ef = max([ef[p] for p in preds])
                    es[node] = max_ef
                ef[node] = es[node] + timedelta(days=dur)
                
            # Pasang kembali ke DataFrame
            df_wbs['Start'] = df_wbs['Task ID'].map(es)
            df_wbs['Finish'] = df_wbs['Task ID'].map(ef)
            
            return {"status": "success", "data": df_wbs}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==========================================
    # 2. GENERATE GANTT CHART (INTERAKTIF)
    # ==========================================
    def gambar_gantt_chart(self, df_wbs):
        """
        Membuat Gantt Chart interaktif menggunakan Plotly Express.
        """
        # Plotly Express Timeline jauh lebih modern daripada figure_factory
        fig = px.timeline(
            df_wbs, 
            x_start="Start", 
            x_end="Finish", 
            y="Task", 
            color="Bobot (%)",
            hover_data=["Durasi (Hari)", "Biaya (Rp)"],
            title="📊 Gantt Chart Proyek (4D BIM)",
            color_continuous_scale=px.colors.sequential.Tealgrn
        )
        # Balik sumbu Y agar task pertama ada di atas
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(xaxis_title="Timeline Proyek", yaxis_title="Work Breakdown Structure (WBS)")
        
        return fig

    # ==========================================
    # 3. GENERATE KURVA-S
    # ==========================================
    def gambar_kurva_s(self, df_wbs):
        """
        Menghasilkan grafik Kurva-S (Rencana Progres Kumulatif) berdasarkan Gantt Chart.
        """
        min_date = df_wbs['Start'].min()
        max_date = df_wbs['Finish'].max()
        
        # Buat rentang waktu harian
        date_range = pd.date_range(start=min_date, end=max_date)
        df_progress = pd.DataFrame({"Tanggal": date_range})
        df_progress['Bobot_Harian'] = 0.0
        
        # Distribusikan bobot setiap task ke hari-hari aktifnya (Secara Linier)
        for index, row in df_wbs.iterrows():
            start = row['Start']
            finish = row['Finish']
            durasi = row['Durasi (Hari)']
            bobot = row['Bobot (%)']
            
            if durasi > 0:
                bobot_per_hari = bobot / durasi
                # Tambahkan bobot ke tanggal yang sesuai
                mask = (df_progress['Tanggal'] >= start) & (df_progress['Tanggal'] < finish)
                df_progress.loc[mask, 'Bobot_Harian'] += bobot_per_hari
                
        # Hitung Kumulatif (Kurva S)
        df_progress['Progres_Kumulatif (%)'] = df_progress['Bobot_Harian'].cumsum()
        
        # Pastikan maksimal 100% (mengatasi masalah pembulatan float)
        df_progress['Progres_Kumulatif (%)'] = df_progress['Progres_Kumulatif (%)'].clip(upper=100.0)

        # Plot menggunakan Graph Objects
        fig = go.Figure()
        
        # Area Grafik Kumulatif (S-Curve)
        fig.add_trace(go.Scatter(
            x=df_progress['Tanggal'], 
            y=df_progress['Progres_Kumulatif (%)'],
            mode='lines', 
            name='Rencana Progres (S-Curve)',
            line=dict(color='firebrick', width=4, shape='spline'), # Spline agar melengkung mulus seperti 'S'
            fill='tozeroy',
            fillcolor='rgba(178, 34, 34, 0.1)'
        ))
        
        # Bar Chart untuk Bobot Harian (Histogram)
        fig.add_trace(go.Bar(
            x=df_progress['Tanggal'], 
            y=df_progress['Bobot_Harian'],
            name='Bobot Pekerjaan Harian (%)',
            marker_color='royalblue',
            opacity=0.5,
            yaxis='y2' # Gunakan sumbu Y kedua di sebelah kanan
        ))

        fig.update_layout(
            title="📈 Kurva-S Proyek & Distribusi Bobot Harian",
            xaxis_title="Timeline",
            yaxis=dict(title="Progres Kumulatif (%)", range=[0, 105]),
            yaxis2=dict(title="Bobot Harian (%)", overlaying='y', side='right', showgrid=False),
            hovermode="x unified",
            legend=dict(x=0.01, y=0.99)
        )
        
        return fig