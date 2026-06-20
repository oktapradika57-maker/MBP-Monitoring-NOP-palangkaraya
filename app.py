
import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.request
import urllib.error
import io
import socket

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Data Validation Dashboard", layout="wide", initial_sidebar_state="expanded")

st.title("Dashboard Validasi Input Tim 🔍")
st.markdown("Memantau anomali, kewajaran, dan ketepatan input data RH dan Waktu secara *real-time*.")
st.markdown("---")

# --- MENGAMBIL DATA DENGAN TIMEOUT KETAT (ANTI-FREEZE) ---
@st.cache_resource(ttl=60) # Cache diperbarui setiap 1 menit agar tidak mengunci data error
def load_excel_safe():
    sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
    xlsx_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'}
    request = urllib.request.Request(xlsx_url, headers=headers)
    
    try:
        # Diberikan timeout=15 detik agar aplikasi TIDAK AKAN PERNAH HANG/BLANK selamanya di Cloud
        with urllib.request.urlopen(request, timeout=15) as response:
            file_data = response.read()
            
        xl = pd.ExcelFile(io.BytesIO(file_data))
        return xl, None
    except socket.timeout:
        return None, "⏳ Koneksi Timeout: Server Google Sheets terlalu lama merespons. Silakan klik tombol 'Muat Ulang Data' di bawah."
    except urllib.error.URLError as e:
        return None, f"❌ Gagal Terhubung ke Google: {e.reason}. Pastikan link spreadsheet tidak diubah."
    except Exception as e:
        return None, f"⚠️ Gangguan Sistem: {str(e)}"

# Menampilkan indikator pemuatan data
with st.spinner('🔄 Sedang mengambil data terbaru dari Google Sheets (Maksimal 15 detik)...'):
    xl_file, error_msg = load_excel_safe()

# --- PENANGANAN JIKA TERJADI TIMEOUT / ERROR ---
if xl_file is None:
    st.error(error_msg)
    if st.button("🔄 Muat Ulang Data (Coba Lagi)"):
        st.cache_resource.clear()
        st.rerun()
        
    st.info("""
    **Tips Perbaikan Kendala Terbuka:**
    1. Lakukan **Reboot App** melalui halaman utama dashboard *share.streamlit.io* Anda jika halaman ini tetap tidak berubah.
    2. Pastikan file `requirements.txt` di GitHub Anda sudah berisi baris: `openpyxl`
    """)
else:
    # --- SIDEBAR UTAMA ---
    with st.sidebar:
        st.header("⚙️ Konfigurasi Data")
        sheet_names = xl_file.sheet_names
        selected_sheet = st.selectbox("Pilih Tab / Sheet Data:", sheet_names)
        
        # Tombol manual clear cache di sidebar untuk kenyamanan user
        if st.button("🔄 Segarkan Data Sheets"):
            st.cache_resource.clear()
            st.cache_data.clear()
            st.rerun()
            
        # --- DETEKSI BARIS HEADER OTOMATIS ---
        @st.cache_data(ttl=30)
        def parse_sheet_smart(sheet_name):
            df_raw = xl_file.parse(sheet_name, header=None)
            header_row_index = 0
            for idx, row in df_raw.iterrows():
                row_values_str = row.astype(str).str.lower().values
                if any('rh' in val or 'delta' in val or 'time' in val for val in row_values_str):
                    header_row_index = idx
                    break
            
            df_final = xl_file.parse(sheet_name, skiprows=header_row_index)
            df_final.columns = df_final.columns.str.strip()
            return df_final

        df = parse_sheet_smart(selected_sheet)
        all_columns = df.columns.tolist()
        
        st.markdown("---")
        st.header("🔗 Pemetaan Kolom")
        
        def auto_detect(keywords, columns):
            for col in columns:
                if any(kw in str(col).lower() for kw in keywords):
                    return col
            return columns[0] if columns else ""

        col_rh_awal = st.selectbox("Kolom RH Awal:", all_columns, index=all_columns.index(auto_detect(['awal', 'start', 'initial', 'rh 1', 'rh_awal'], all_columns)) if auto_detect(['awal', 'start', 'initial', 'rh 1', 'rh_awal'], all_columns) in all_columns else 0)
        col_rh_akhir = st.selectbox("Kolom RH Akhir:", all_columns, index=all_columns.index(auto_detect(['akhir', 'end', 'final', 'rh 2', 'rh_akhir'], all_columns)) if auto_detect(['akhir', 'end', 'final', 'rh 2', 'rh_akhir'], all_columns) in all_columns else 0)
        col_delta_rh = st.selectbox("Kolom Delta RH:", all_columns, index=all_columns.index(auto_detect(['delta rh', 'd rh', 'Δ rh', 'drh'], all_columns)) if auto_detect(['delta rh', 'd rh', 'Δ rh', 'drh'], all_columns) in all_columns else 0)
        col_delta_time = st.selectbox("Kolom Delta Time:", all_columns, index=all_columns.index(auto_detect(['delta time', 'd time', 'waktu', 'Δ time', 'dtime'], all_columns)) if auto_detect(['delta time', 'd time', 'waktu', 'Δ time', 'dtime'], all_columns) in all_columns else 0)

        st.markdown("---")
        st.header("⚠️ Batas Toleransi")
        batas_delta_rh = st.number_input("Maksimal Delta RH", value=15.0, step=1.0)
        batas_delta_time = st.number_input("Maksimal Delta Time", value=60.0, step=1.0)

    # --- PROSES VALIDASI DATA DATA ---
    df_clean = df.copy()
    df_clean['RH awal_num'] = pd.to_numeric(df_clean[col_rh_awal], errors='coerce')
    df_clean['RH akhir_num'] = pd.to_numeric(df_clean[col_rh_akhir], errors='coerce')
    df_clean['Delta RH_num'] = pd.to_numeric(df_clean[col_delta_rh], errors='coerce')
    df_clean['Delta Time_num'] = pd.to_numeric(df_clean[col_delta_time], errors='coerce')
    
    kolom_cek = ['RH awal_num', 'RH akhir_num', 'Delta RH_num', 'Delta Time_num']

    df_clean['Status Validasi'] = 'Wajar (Normal)'
    kondisi_anomali = (
        (df_clean['Delta RH_num'].abs() > batas_delta_rh) | 
        (df_clean['Delta Time_num'] > batas_delta_time) |
        (df_clean['RH awal_num'] < 0) | (df_clean['RH awal_num'] > 100) |
        (df_clean['RH akhir_num'] < 0) | (df_clean['RH akhir_num'] > 100) |
        (df_clean[kolom_cek].isna().any(axis=1))
    )
    df_clean.loc[kondisi_anomali, 'Status Validasi'] = 'Tidak Wajar (Perlu Dicek)'

    # --- LAYOUT INTERMUKA TAB ---
    tab1, tab2, tab3 = st.tabs(["📊 Ringkasan KPI & Data", "🚩 Daftar Anomali (Wajib Cek)", "📈 Grafik Analisis Kualitas"])

    with tab1:
        total_data = len(df_clean)
        df_anomali = df_clean[df_clean['Status Validasi'] == 'Tidak Wajar (Perlu Dicek)']
        total_anomali = len(df_anomali)
        persen_anomali = (total_anomali / total_data * 100) if total_data > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Input Data", total_data)
        col2.metric("Data Terindikasi Salah", total_anomali, f"{persen_anomali:.1f}% tingkat kesalahan", delta_color="inverse")
        col3.metric("Rata-rata Delta RH", f"{df_clean['Delta RH_num'].mean():.2f}" if not df_clean['Delta RH_num'].isna().all() else "0.00")
        
        st.markdown("### 📋 Semua Baris Data pada Tab Aktif")
        kolom_tampil = list(set([col_rh_awal, col_rh_akhir, col_delta_rh, col_delta_time])) + ['Status Validasi']
        st.dataframe(df_clean[kolom_tampil], use_container_width=True, height=350)

    with tab2:
        st.markdown("### 🚩 Baris Data Berstatus Tidak Wajar")
        if total_anomali > 0:
            st.error(f"Ditemukan {total_anomali} baris data yang memerlukan perbaikan segera!")
            st.dataframe(df_anomali[kolom_tampil], use_container_width=True)
        else:
            st.success("🎉 Sempurna! Seluruh baris data pada sheet ini berstatus wajar.")

    with tab3:
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            fig_hist = px.histogram(
                df_clean, x="Delta RH_num", color="Status Validasi", 
                labels={'Delta RH_num': 'Delta RH'},
                color_discrete_map={"Wajar (Normal)": "#008080", "Tidak Wajar (Perlu Dicek)": "#DC143C"},
                title="Peta Distribusi Sebaran Delta RH"
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            
        with chart_col2:
            fig_scatter = px.scatter(
                df_clean, x="Delta Time_num", y="Delta RH_num", color="Status Validasi",
                labels={'Delta Time_num': 'Delta Time', 'Delta RH_num': 'Delta RH'},
                color_discrete_map={"Wajar (Normal)": "#008080", "Tidak Wajar (Perlu Dicek)": "#DC143C"},
                title="Scatter Plot: Korelasi Delta Time vs Delta RH"
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
