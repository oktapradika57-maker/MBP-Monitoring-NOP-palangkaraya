import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Data Validation Dashboard", layout="wide", initial_sidebar_state="expanded")

st.title("Dashboard Validasi Input Tim 🔍")
st.markdown("Memantau anomali, kewajaran, dan ketepatan input data RH dan Waktu secara *real-time*.")
st.markdown("---")

# --- SIDEBAR UTAMA ---
with st.sidebar:
    st.header("⚙️ Konfigurasi Data")
    
    # Menampilkan daftar pilihan sheet sesuai isi database Anda
    selected_sheet = st.selectbox("Pilih Tab / Sheet Data:", ["Sheet1", "Pivot Table 1"])
    
    if st.button("🔄 Segarkan Data Sheets"):
        st.cache_data.clear()
        st.rerun()

    # --- MENGAMBIL DATA DENGAN METODE GVIZ CSV (SANGAT AMAN & RINGAN) ---
    @st.cache_data(ttl=60)
    def load_data_csv(sheet_name):
        sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
        # Melakukan URL Encoding untuk mengantisipasi nama sheet yang menggunakan spasi
        encoded_sheet = urllib.parse.quote(sheet_name)
        
        # URL Google Viz API untuk menarik data langsung dalam format CSV (Bypass Excel Engine)
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_sheet}"
        
        try:
            df_final = pd.read_csv(url)
            # Membersihkan spasi tak terlihat di nama kolom
            df_final.columns = df_final.columns.str.strip()
            return df_final, None
        except Exception as e:
            return None, str(e)

    with st.spinner('🔄 Membaca data aman dari Google Sheets... Mohon tunggu.'):
        df, error_msg = load_data_csv(selected_sheet)

# --- PENANGANAN JIKA GAGAL UNDUH DATA ---
if df is None:
    st.error("🚨 Gagal memuat data dari Google Sheets.")
    st.text(f"Detail Kendala: {error_msg}")
    st.info("""
    **Saran Perbaikan:**
    Pastikan status berbagi di Google Sheets Anda sudah diatur ke **'Anyone with the link can view'**. 
    Jika statusnya masih dibatasi (Restricted), server Streamlit Cloud akan otomatis ditolak oleh Google.
    """)
else:
    all_columns = df.columns.tolist()
    
    if not all_columns:
        st.warning("⚠️ Lembar kerja (sheet) ini kosong atau tidak memiliki nama kolom di baris pertama.")
    else:
        with st.sidebar:
            st.markdown("---")
            st.header("🔗 Pemetaan Kolom")
            st.caption("Sistem mendeteksi kolom otomatis. Sesuaikan jika keliru:")
            
            # Fungsi pencarian indeks otomatis yang aman (Anti-Error / Anti-ValueError)
            def get_index(keywords, columns):
                for idx, col in enumerate(columns):
                    if any(kw in str(col).lower() for kw in keywords):
                        return idx
                return 0

            idx_awal = get_index(['awal', 'start', 'initial', 'rh 1', 'rh_awal'], all_columns)
            idx_akhir = get_index(['akhir', 'end', 'final', 'rh 2', 'rh_akhir'], all_columns)
            idx_delta_rh = get_index(['delta rh', 'd rh', 'Δ rh', 'drh'], all_columns)
            idx_delta_time = get_index(['delta time', 'd time', 'waktu', 'Δ time', 'dtime'], all_columns)

            col_rh_awal = st.selectbox("Kolom RH Awal:", all_columns, index=idx_awal)
            col_rh_akhir = st.selectbox("Kolom RH Akhir:", all_columns, index=idx_akhir)
            col_delta_rh = st.selectbox("Kolom Delta RH:", all_columns, index=idx_delta_rh)
            col_delta_time = st.selectbox("Kolom Delta Time:", all_columns, index=idx_delta_time)

            st.markdown("---")
            st.header("⚠️ Batas Toleransi")
            batas_delta_rh = st.number_input("Maksimal Delta RH", value=15.0, step=1.0)
            batas_delta_time = st.number_input("Maksimal Delta Time", value=60.0, step=1.0)

        # --- PROSES VALIDASI DATA ---
        df_clean = df.copy()
        
        # Konversi tipe data kolom ke numerik (jika ada teks kosong/salah ketik langsung diubah menjadi NaN secara aman)
        df_clean['RH awal_num'] = pd.to_numeric(df_clean[col_rh_awal], errors='coerce')
        df_clean['RH akhir_num'] = pd.to_numeric(df_clean[col_rh_akhir], errors='coerce')
        df_clean['Delta RH_num'] = pd.to_numeric(df_clean[col_delta_rh], errors='coerce')
        df_clean['Delta Time_num'] = pd.to_numeric(df_clean[col_delta_time], errors='coerce')
        
        kolom_cek = ['RH awal_num', 'RH akhir_num', 'Delta RH_num', 'Delta Time_num']

        # Klasifikasi Status Validitas
        df_clean['Status Validasi'] = 'Wajar (Normal)'
        kondisi_anomali = (
            (df_clean['Delta RH_num'].abs() > batas_delta_rh) | 
            (df_clean['Delta Time_num'] > batas_delta_time) |
            (df_clean['RH awal_num'] < 0) | (df_clean['RH awal_num'] > 100) |
            (df_clean['RH akhir_num'] < 0) | (df_clean['RH akhir_num'] > 100) |
            (df_clean[kolom_cek].isna().any(axis=1)) # Menandai baris kosong atau salah ketik huruf
        )
        df_clean.loc[kondisi_anomali, 'Status Validasi'] = 'Tidak Wajar (Perlu Dicek)'

        # --- LAYOUT ANTARMUKA UTAMA (TABS) ---
        tab1, tab2, tab3 = st.tabs(["📊 Ringkasan KPI & Data", "🚩 Daftar Anomali (Wajib Cek)", "📈 Grafik Analisis Kualitas"])

        with tab1:
            total_data = len(df_clean)
            df_anomali = df_clean[df_clean['Status Validasi'] == 'Tidak Wajar (Perlu Dicek)']
            total_anomali = len(df_anomali)
            persen_anomali = (total_anomali / total_data * 100) if total_data > 0 else 0

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Input Data", total_data)
            col2.metric("Data Terindikasi Salah", total_anomali, f"{persen_anomali:.1f}% tingkat kesalahan", delta_color="inverse")
            
            avg_delta_rh = df_clean['Delta RH_num'].mean()
            col3.metric("Rata-rata Delta RH", f"{avg_delta_rh:.2f}" if not pd.isna(avg_delta_rh) else "0.00")
            
            st.markdown("### 📋 Semua Baris Data pada Tab Aktif")
            kolom_tampil = list(set([col_rh_awal, col_rh_akhir, col_delta_rh, col_delta_time])) + ['Status Validasi']
            st.dataframe(df_clean[kolom_tampil], use_container_width=True, height=350)

        with tab2:
            st.markdown("### 🚩 Baris Data Berstatus Tidak Wajar")
            st.caption("Daftar di bawah ini adalah baris data yang melebihi toleransi, bernilai kosong, atau salah ketik huruf.")
            if total_anomali > 0:
                st.error(f"Ditemukan {total_anomali} baris data yang memerlukan perbaikan segera!")
                st.dataframe(df_anomali[kolom_tampil], use_container_width=True)
            else:
                st.success("🎉 Sempurna! Seluruh baris data pada sheet ini bersih dan berstatus wajar.")

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
