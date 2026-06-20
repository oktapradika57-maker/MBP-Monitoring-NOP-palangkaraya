import streamlit as st
import pandas as pd
import urllib.parse

st.set_page_config(page_title="Dashboard MBP", layout="wide")

st.title("📊 MBP Quality Control Dashboard")

# Konfigurasi Akses Data
sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"

@st.cache_data(ttl=60)
def load_data(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(sheet_name)}"
    try:
        # Membaca data
        df = pd.read_csv(url)
        # Membersihkan nama kolom
        df.columns = df.columns.str.strip()
        # Membuang baris yang kosong sama sekali
        df = df.dropna(how='all')
        return df
    except Exception as e:
        return None

# Pilih Sheet
selected_sheet = st.sidebar.selectbox("Pilih Tab:", ["Sheet1", "Pivot Table 1"])
df = load_data(selected_sheet)

if df is not None:
    st.sidebar.markdown("---")
    cols = df.columns.tolist()
    
    # Pilih kolom untuk dihitung
    rh_awal = st.sidebar.selectbox("Kolom RH Awal:", cols, index=0)
    rh_akhir = st.sidebar.selectbox("Kolom RH Akhir:", cols, index=1)

    # --- PENGAMANAN DATA (FIX ERROR) ---
    df_clean = df.copy()
    
    # Mengonversi ke angka secara paksa. Jika teks, maka jadi NaN (Not a Number)
    df_clean['Val_Awal'] = pd.to_numeric(df_clean[rh_awal], errors='coerce')
    df_clean['Val_Akhir'] = pd.to_numeric(df_clean[rh_akhir], errors='coerce')
    
    # Menghitung Delta hanya jika kedua kolom berisi angka
    df_clean['Delta RH'] = df_clean['Val_Akhir'] - df_clean['Val_Awal']
    
    # Menampilkan hanya baris yang datanya valid (membuang baris Total/Teks)
    df_display = df_clean.dropna(subset=['Val_Awal', 'Val_Akhir'])

    # --- LAYOUT DASHBOARD ---
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Ringkasan")
        st.metric("Total Data Valid", len(df_display))
        st.metric("Rata-rata Delta", f"{df_display['Delta RH'].mean():.2f}")
    
    with col2:
        st.subheader("Data Detail")
        st.dataframe(df_display[['Val_Awal', 'Val_Akhir', 'Delta RH']], use_container_width=True)

else:
    st.error("Gagal memuat data. Pastikan link Google Sheets Anda sudah diatur menjadi 'Anyone with the link' (Publik).")
