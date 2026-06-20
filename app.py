import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Data Validation Dashboard", layout="wide", initial_sidebar_state="expanded")

st.title("Dashboard Validasi Input Tim 🔍")
st.markdown("Memantau anomali, kewajaran, dan ketepatan input data RH dan Waktu secara *real-time*.")
st.markdown("---")

# --- MENGAMBIL DATA (FORMAT EXCEL AGAR BISA MEMBACA SEMUA TAB/SHEET) ---
@st.cache_data(ttl=60)
def load_excel_data():
    sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
    # Mengunduh dalam format .xlsx agar sistem bisa mendeteksi struktur multi-tab
    xlsx_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    try:
        xl = pd.ExcelFile(xlsx_url)
        return xl
    except Exception as e:
        return None

xl_file = load_excel_data()

# --- PENANGANAN JIKA GAGAL KONEKSI ---
if xl_file is None:
    st.error("🚨 Gagal memuat data dari Google Sheets.")
    st.info("""
    **Langkah Perbaikan:**
    1. Pastikan status berbagi (Share) di Google Sheets Anda sudah benar-benar diatur ke **"Anyone with the link can view"**.
    2. Pastikan Anda telah menambahkan `openpyxl` di dalam file `requirements.txt` Anda.
    """)
else:
    # --- SIDEBAR PENGATURAN USER INTERFACE ---
    with st.sidebar:
        st.header("⚙️ Sumber Data & Tab")
        
        # Fitur 1: Memilih Tab/Sheet secara dinamis
        sheet_names = xl_file.sheet_names
        selected_sheet = st.selectbox("Pilih Tab / Sheet Data:", sheet_names)
        
        # Membaca data berdasarkan tab yang dipilih user
        df = xl_file.parse(selected_sheet)
        # Menghapus spasi gaib di awal/akhir nama kolom asli
        df.columns = df.columns.str.strip()
        all_columns = df.columns.tolist()
        
        st.markdown("---")
        st.header("🔗 Pemetaan Kolom (Mapping)")
        st.caption("Jika nama kolom di bawah tidak sesuai, silakan pilih kolom yang benar dari spreadsheet Anda.")
        
        # Fungsi otomatis untuk mendeteksi kata kunci kolom agar user tidak perlu repot memilih manual di awal
        def tebak_kolom(keywords, columns):
            for col in columns:
                if any(kw in str(col).lower() for kw in keywords):
                    return col
            return columns[0] if columns else ""

        # Dropdown Pemetaan Kolom Otomatis / Manual
        col_rh_awal = st.selectbox("Kolom RH Awal:", all_columns, index=all_columns.index(tebak_kolom(['awal', 'start', 'initial', 'rh 1'], all_columns)) if tebak_kolom(['awal', 'start', 'initial', 'rh 1'], all_columns) in all_columns else 0)
        col_rh_akhir = st.selectbox("Kolom RH Akhir:", all_columns, index=all_columns.index(tebak_kolom(['akhir', 'end', 'final', 'rh 2'], all_columns)) if tebak_kolom(['akhir', 'end', 'final', 'rh 2'], all_columns) in all_columns else 0)
        col_delta_rh = st.selectbox("Kolom Delta RH:", all_columns, index=all_columns.index(tebak_kolom(['delta rh', 'd rh', 'Δ rh', 'drh'], all_columns)) if tebak_kolom(['delta rh', 'd rh', 'Δ rh', 'drh'], all_columns) in all_columns else 0)
        col_delta_time = st.selectbox("Kolom Delta Time:", all_columns, index=all_columns.index(tebak_kolom(['delta time', 'd time', 'waktu', 'Δ time', 'dtime'], all_columns)) if tebak_kolom(['delta time', 'd time', 'waktu', 'Δ time', 'dtime'], all_columns) in all_columns else 0)

        st.markdown("---")
        st.header("⚠️ Batas Toleransi Validasi")
        batas_delta_rh = st.number_input("Maksimal Batas Delta RH", value=15.0, step=1.0)
        batas_delta_time = st.number_input("Maksimal Batas Delta Time", value=60.0, step=1.0)
        st.markdown("---")
        st.caption("Dashboard v3.0 | Anti-Error System")

    # --- PROSES PEMBERSIHAN DATA INTERNAL ---
    df_clean = df.copy()
    
    # Memastikan tipe data yang dipetakan dikonversi paksa menjadi angka (mengabaikan jika tim salah ketik huruf)
    df_clean['RH awal'] = pd.to_numeric(df_clean[col_rh_awal], errors='coerce')
    df_clean['RH akhir'] = pd.to_numeric(df_clean[col_rh_akhir], errors='coerce')
    df_clean['Delta RH'] = pd.to_numeric(df_clean[col_delta_rh], errors='coerce')
    df_clean['Delta Time'] = pd.to_numeric(df_clean[col_delta_time], errors='coerce')
    
    kolom_fokus = ['RH awal', 'RH akhir', 'Delta RH', 'Delta Time']

    # Logika Menentukan Data Wajar vs Anomali
    df_clean['Status Data'] = 'Wajar (Normal)'
    kondisi_anomali = (
        (df_clean['Delta RH'].abs() > batas_delta_rh) | 
        (df_clean['Delta Time'] > batas_delta_time) |
        (df_clean['RH awal'] < 0) | (df_clean['RH awal'] > 100) |
        (df_clean['RH akhir'] < 0) | (df_clean['RH akhir'] > 100) |
        (df_clean[kolom_fokus].isna().any(axis=1)) # Jika ada baris kosong atau berisi teks salah input
    )
    df_clean.loc[kondisi_anomali, 'Status Data'] = 'Tidak Wajar (Perlu Dicek)'

    # --- LAYOUT UTAMA DENGAN STRUKTUR TAB PROFESIONAL ---
    tab1, tab2, tab3 = st.tabs(["📊 Ringkasan KPI & Data", "🚩 Daftar Anomali (Wajib Cek)", "📈 Grafik Analisis Kualitas"])

    # TAB 1: RINGKASAN UTAMA
    with tab1:
        total_data = len(df_clean)
        df_anomali = df_clean[df_clean['Status Data'] == 'Tidak Wajar (Perlu Dicek)']
        total_anomali = len(df_anomali)
        persen_anomali = (total_anomali / total_data * 100) if total_data > 0 else 0

        # Menampilkan Ringkasan Angka Indikator
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Input Data", total_data)
        col2.metric("Data Terindikasi Salah/Anomali", total_anomali, f"{persen_anomali:.1f}% tingkat kesalahan", delta_color="inverse")
        col3.metric("Rata-rata Delta RH Keseluruhan", f"{df_clean['Delta RH'].mean():.2f}")
        
        st.markdown("### 📋 Semua Data pada Tab Aktif")
        # Hanya menampilkan kolom relevan yang dipilih user + kolom status agar bersih
        kolom_tampil = list(set([col_rh_awal, col_rh_akhir, col_delta_rh, col_delta_time])) + ['Status Data']
        st.dataframe(df_clean[kolom_tampil], use_container_width=True, height=350)

    # TAB 2: KHUSUS DATA YANG ERROR
    with tab2:
        st.markdown("### 🚩 Baris Data Berstatus Tidak Wajar")
        st.write("Baris di bawah ini terdeteksi melewati batas toleransi atau memiliki kesalahan ketik teks pada kolom angka.")
        if total_anomali > 0:
            st.error(f"Ditemukan {total_anomali} baris data yang harus segera divalidasi oleh tim!")
            st.dataframe(df_anomali[kolom_tampil], use_container_width=True)
        else:
            st.success("🎉 Sempurna! Tidak ditemukan kesalahan input data sama sekali pada sheet ini.")

    # TAB 3: VISUALISASI GRAFIK INTERAKTIF
    with tab3:
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            fig_hist = px.histogram(
                df_clean, x="Delta RH", color="Status Data", 
                color_discrete_map={"Wajar (Normal)": "#008080", "Tidak Wajar (Perlu Dicek)": "#DC143C"},
                title="Peta Distribusi Sebaran Delta RH"
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            
        with chart_col2:
            fig_scatter = px.scatter(
                df_clean, x="Delta Time", y="Delta RH", color="Status Data",
                color_discrete_map={"Wajar (Normal)": "#008080", "Tidak Wajar (Perlu Dicek)": "#DC143C"},
                title="Scatter Plot: Korelasi Delta Time vs Delta RH"
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
