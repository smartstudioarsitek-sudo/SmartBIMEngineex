import pandas as pd
import numpy as np
from modules.geotek.libs_topografi import Topografi_Engine

print("Membuat data titik ukur topografi (dummy)...")
# Membuat 100 titik acak di area 50x50 meter dengan elevasi bergelombang (Z antara 10m s/d 20m)
np.random.seed(42)
data_titik = {
    'X': np.random.uniform(0, 50, 100),
    'Y': np.random.uniform(0, 50, 100),
    'Z': np.random.uniform(10, 20, 100) # Tanah berbukit
}
df_titik = pd.DataFrame(data_titik)

elevasi_target = 15.0 # Kita mau meratakan tanah di elevasi +15 meter

print("Menghidupkan Mesin Topografi...")
topo = Topografi_Engine()
hasil = topo.hitung_cut_fill(df_titik, elevasi_target)

print("\n--- HASIL ANALISIS EARTHWORK ---")
for k, v in hasil.items():
    print(f"{k}: {v}")
