import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse

st.set_page_config(page_title="Dashboard MBP", layout="wide")

st.title("📊 Dashboard Validasi Data MBP")

# Konfigurasi Akses Data
sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"

@st.cache_data(ttl=300)
def load_data(sheet_name):
    encoded_sheet = urllib.parse.quote(sheet_name)
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_sheet}"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        # PEMBERSIH OTOMATIS: Hapus baris yang semua datanya kosong
        df = df.dropna(how='all')
        return df
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return None

# Sidebar
selected_sheet = st.sidebar.selectbox("Pilih Tab:", ["Sheet1", "Pivot Table 1"])
df = load_data(selected_sheet)

if df is not None:
    # Identifikasi kolom secara aman
    cols = df.columns.tolist()
    
    with st.sidebar:
        st.header("Mapping Kolom")
        rh_awal = st.selectbox("Kolom RH Awal:", cols, index=0)
        rh_akhir = st.selectbox("Kolom RH Akhir:", cols, index=1)
        waktu_m = st.selectbox("Kolom Waktu Mulai:", cols, index=2)
        waktu_s = st.selectbox("Kolom Waktu Selesai:", cols, index=3)

    # PROSES DATA AMAN (Data Cleaning)
    df_clean = df.copy()
    
    # Mengonversi ke angka dan memaksa error menjadi NaN agar tidak crash
    df_clean['RHA'] = pd.to_numeric(df_clean[rh_awal], errors='coerce')
    df_clean['RHK'] = pd.to_numeric(df_clean[rh_akhir], errors='coerce')
    
    # Hitung Delta
    df_clean['Delta RH'] = df_clean['RHK'] - df_clean['RHA']
    
    # Tampilkan Data
    st.subheader(f"Data dari {selected_sheet}")
    st.dataframe(df_clean)
    
    # Visualisasi
    st.subheader("Grafik Delta RH")
    fig = px.bar(df_clean.dropna(subset=['Delta RH']), y='Delta RH', title="Distribusi Delta RH per Baris")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Menunggu data...")
