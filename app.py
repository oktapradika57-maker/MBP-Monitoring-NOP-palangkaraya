import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Data Validation Dashboard", layout="wide", initial_sidebar_state="expanded")

st.title("Dashboard Validasi Input Tim 🔍")
st.markdown("Memantau anomali, kewajaran, dan ketepatan input data RH dan Waktu secara *real-time*.")
st.markdown("---")

# --- MENGAMBIL DATA (DENGAN INDIKATOR LOADING & CACHE OPTIMAL) ---
# Menggunakan st.cache_resource untuk file Excel agar tidak dibaca ulang setiap klik
@st.cache_resource(ttl=300) # Data di-cache selama 5 menit untuk menghemat kuota & mempercepat loading
def load_excel_data():
    sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
    xlsx_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    try:
        xl = pd.ExcelFile(xlsx_url)
        return xl
    except Exception:
        return None

# Menampilkan animasi loading profesional agar user tahu sistem sedang bekerja
with st.spinner('🔄 Menghubungkan dan mengunduh data dari Google Sheets... Mohon tunggu sebentar.'):
    xl_file = load_excel_data()

# --- PENANGANAN JIKA GAGAL KONEKSI ---
if xl_file is None:
    st.error("🚨 Gagal memuat data dari Google Sheets.")
    st.info("Pastikan status berbagi (Share) di Google Sheets Anda sudah diatur ke 'Anyone with the link can view'.")
else:
    # --- SIDEBAR PENGATURAN USER INTERFACE ---
    with st.sidebar:
        st.header("⚙️ Sumber Data & Tab")
        
        sheet_names = xl_file.sheet_names
        selected_sheet = st.selectbox("Pilih Tab / Sheet Data:", sheet_names)
        
        # Mengambil data dari tab yang dipilih (di-cache per tab agar cepat)
        @st.cache_data(ttl=60)
        def parse_sheet(xl, sheet):
            df_sheet = xl.parse(sheet)
            df_sheet.columns = df_sheet.columns.str.strip()
            return df_sheet

        df = parse_sheet(xl_file, selected_sheet)
        all_columns = df.columns.tolist()
        
        st.markdown("---")
        st.header("🔗 Pemetaan Kolom (Mapping)")
        
        def tebak_kolom(keywords, columns):
            for col in columns:
                if any(kw in str(col).lower() for kw in keywords):
                    return col
            return columns[0] if columns else ""

        col_rh_awal = st.selectbox("Kolom RH Awal:", all_columns, index=all_columns.index(tebak_kolom(['awal', 'start', 'initial', 'rh 1'], all_columns)) if tebak_kolom(['awal', 'start', 'initial', 'rh 1'], all_columns) in all_columns else 0)
        col_rh_akhir = st.selectbox("Kolom RH Akhir:", all_columns, index=all_columns.index(tebak_kolom(['akhir', 'end', 'final', 'rh 2'], all_columns)) if tebak_kolom(['akhir', 'end', 'final', 'rh 2'], all_columns) in all_columns else 0)
        col_delta_rh = st.selectbox("Kolom Delta RH:", all_columns, index=all_columns.index(tebak_kolom(['delta rh', 'd rh', 'Δ rh', 'drh'], all_columns)) if tebak_kolom(['delta rh', 'd rh', 'Δ rh', 'drh'], all_columns) in all_columns else 0)
        col_delta_time = st.selectbox("Kolom Delta Time:", all_columns, index=all_columns.index(tebak_kolom(['delta time', 'd time', 'waktu', 'Δ time', 'dtime'], all_columns)) if tebak_kolom(['delta time', 'd time', 'waktu', 'Δ time', 'dtime'], all_columns) in all_columns else 0)

        st.markdown("---")
        st.header("⚠️ Batas Toleransi Validasi")
        batas_delta_rh = st.number_input("Maksimal Batas Delta RH", value=15.0, step=1.0)
        batas_delta_time = st.number_input("Maksimal Batas Delta Time", value=60.0, step=1.0)

    # --- PROSES DATA & VALIDASI ---
    df_clean = df.copy()
    df_clean['RH awal'] = pd.to_numeric(df_clean[col_rh_awal], errors='coerce')
    df_clean['RH akhir'] = pd.to_numeric(df_clean[col_rh_akhir], errors='coerce')
    df_clean['Delta RH'] = pd.to_numeric(df_clean[col_delta_rh], errors='coerce')
    df_clean['Delta Time'] = pd.to_numeric(df_clean[col_delta_time], errors='coerce')
    
    kolom_fokus = ['RH awal', 'RH akhir', 'Delta RH', 'Delta Time']

    df_clean['Status Data'] = 'Wajar (Normal)'
    kondisi_anomali = (
        (df_clean['Delta RH'].abs() > batas_delta_rh) | 
        (df_clean['Delta Time'] > batas_delta_time) |
        (df_clean['RH awal'] < 0) | (df_clean['RH awal'] > 100) |
        (df_clean['RH akhir'] < 0) | (df_clean['RH akhir'] > 100) |
        (df_clean[kolom_fokus].isna().any(axis=1))
    )
    df_clean.loc[kondisi_anomali, 'Status Data'] = 'Tidak Wajar (Perlu Dicek)'

    # --- LAYOUT TAB UTAMA ---
    tab1, tab2, tab3 = st.tabs(["📊 Ringkasan KPI & Data", "🚩 Daftar Anomali (Wajib Cek)", "📈 Grafik Analisis Kualitas"])

    with tab1:
        total_data = len(df_clean)
        df_anomali = df_clean[df_clean['Status Data'] == 'Tidak Wajar (Perlu Dicek)']
        total_anomali = len(df_anomali)
        persen_anomali = (total_anomali / total_data * 100) if total_data > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Input Data", total_data)
        col2.metric("Data Terindikasi Salah/Anomali", total_anomali, f"{persen_anomali:.1f}% tingkat kesalahan", delta_color="inverse")
        col3.metric("Rata-rata Delta RH Keseluruhan", f"{df_clean['Delta RH'].mean():.2f}")
        
        st.markdown("### 📋 Semua Data pada Tab Aktif")
        kolom_tampil = list(set([col_rh_awal, col_rh_akhir, col_delta_rh, col_delta_time])) + ['Status Data']
        st.dataframe(df_clean[kolom_tampil], use_container_width=True, height=350)

    with tab2:
        st.markdown("### 🚩 Baris Data Berstatus Tidak Wajar")
        if total_anomali > 0:
            st.error(f"Ditemukan {total_anomali} baris data yang harus segera divalidasi oleh tim!")
            st.dataframe(df_anomali[kolom_tampil], use_container_width=True)
        else:
            st.success("🎉 Sempurna! Tidak ditemukan kesalahan input data sama sekali pada sheet ini.")

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
