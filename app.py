import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Data Validation Dashboard", layout="wide", initial_sidebar_state="expanded")

st.title("Dashboard Validasi Input Tim 🔍")
st.markdown("Sistem ini akan **menghitung secara otomatis** nilai Delta RH dan Delta Waktu berdasarkan input Awal & Akhir.")
st.markdown("---")

# --- SIDEBAR UTAMA ---
with st.sidebar:
    st.header("⚙️ Konfigurasi Data")
    
    selected_sheet = st.selectbox("Pilih Tab / Sheet Data:", ["Sheet1", "Pivot Table 1"])
    
    if st.button("🔄 Segarkan Data Sheets"):
        st.cache_data.clear()
        st.rerun()

    # --- MENGAMBIL DATA MENTAH CSV DARI GOOGLE SHEETS ---
    @st.cache_data(ttl=60)
    def load_data_csv(sheet_name):
        sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
        encoded_sheet = urllib.parse.quote(sheet_name)
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_sheet}"
        
        try:
            df_final = pd.read_csv(url)
            df_final.columns = df_final.columns.str.strip()
            return df_final, None
        except Exception as e:
            return None, str(e)

    with st.spinner('🔄 Menarik data dari Google Sheets...'):
        df, error_msg = load_data_csv(selected_sheet)

# --- PENANGANAN DATA UTAMA ---
if df is None:
    st.error("🚨 Gagal memuat data. Pastikan status Google Sheets sudah 'Anyone with the link'.")
else:
    all_columns = df.columns.tolist()
    
    if not all_columns:
        st.warning("⚠️ Lembar kerja (sheet) ini kosong.")
    else:
        with st.sidebar:
            st.markdown("---")
            st.header("🔗 Pemetaan Kolom Awal & Akhir")
            st.caption("Karena Delta tidak ada di file, pilih kolom Awal & Akhir di bawah ini agar sistem yang menghitungnya:")
            
            # Mendeteksi otomatis kata kunci
            def get_index(keywords, columns):
                for idx, col in enumerate(columns):
                    if any(kw in str(col).lower() for kw in keywords):
                        return idx
                return 0

            idx_rh_awal = get_index(['awal', 'start', 'rh 1', 'rh awal'], all_columns)
            idx_rh_akhir = get_index(['akhir', 'end', 'rh 2', 'rh akhir'], all_columns)
            idx_waktu_awal = get_index(['waktu awal', 'jam mulai', 'time start', 'jam awal', 'waktu 1', 'jam'], all_columns)
            idx_waktu_akhir = get_index(['waktu akhir', 'jam selesai', 'time end', 'jam akhir', 'waktu 2'], all_columns)

            col_rh_awal = st.selectbox("Kolom RH Awal:", all_columns, index=idx_rh_awal)
            col_rh_akhir = st.selectbox("Kolom RH Akhir:", all_columns, index=idx_rh_akhir)
            col_waktu_awal = st.selectbox("Kolom Waktu / Jam Mulai:", all_columns, index=idx_waktu_awal)
            col_waktu_akhir = st.selectbox("Kolom Waktu / Jam Selesai:", all_columns, index=idx_waktu_akhir)

            st.markdown("---")
            st.header("⚠️ Batas Toleransi")
            batas_delta_rh = st.number_input("Maksimal Delta RH", value=15.0, step=1.0)
            batas_delta_time = st.number_input("Maksimal Delta Time (Menit)", value=60.0, step=1.0)

        # --- 🚀 PROSES HITUNG OTOMATIS (CALCULATING ENGINE) ---
        df_clean = df.copy()
        
        # 1. Pastikan RH dibaca sebagai angka
        df_clean['RH Awal (Num)'] = pd.to_numeric(df_clean[col_rh_awal], errors='coerce')
        df_clean['RH Akhir (Num)'] = pd.to_numeric(df_clean[col_rh_akhir], errors='coerce')
        
        # 2. SISTEM MENGHITUNG DELTA RH
        df_clean['Hitungan Delta RH'] = df_clean['RH Akhir (Num)'] - df_clean['RH Awal (Num)']
        
        # 3. SISTEM MENGHITUNG DELTA WAKTU (Dalam Menit)
        waktu_awal_dt = pd.to_datetime(df_clean[col_waktu_awal].astype(str), errors='coerce')
        waktu_akhir_dt = pd.to_datetime(df_clean[col_waktu_akhir].astype(str), errors='coerce')
        
        # Mengubah selisih waktu menjadi menit (Diambil angka absolut agar tidak minus)
        df_clean['Hitungan Delta Time (Menit)'] = (waktu_akhir_dt - waktu_awal_dt).dt.total_seconds().abs() / 60.0
        
        # Menghapus baris kosong (Misalnya baris 'Total' di paling bawah spreadsheet)
        df_clean = df_clean.dropna(subset=['RH Awal (Num)', 'RH Akhir (Num)'], how='all')

        # 4. KLASIFIKASI VALIDASI & ANOMALI
        kolom_cek = ['RH Awal (Num)', 'RH Akhir (Num)', 'Hitungan Delta RH', 'Hitungan Delta Time (Menit)']
        
        df_clean['Status Validasi'] = 'Wajar (Normal)'
        kondisi_anomali = (
            (df_clean['Hitungan Delta RH'].abs() > batas_delta_rh) | 
            (df_clean['Hitungan Delta Time (Menit)'] > batas_delta_time) |
            (df_clean['RH Awal (Num)'] < 0) | (df_clean['RH Awal (Num)'] > 100) |
            (df_clean['RH Akhir (Num)'] < 0) | (df_clean['RH Akhir (Num)'] > 100) |
            (df_clean[kolom_cek].isna().any(axis=1)) # Menandai error jika tim mengosongkan sel atau salah ketik huruf
        )
        df_clean.loc[kondisi_anomali, 'Status Validasi'] = 'Tidak Wajar (Perlu Dicek)'

        # --- LAYOUT ANTARMUKA UTAMA ---
        tab1, tab2, tab3 = st.tabs(["📊 Ringkasan KPI & Data", "🚩 Daftar Anomali (Wajib Cek)", "📈 Grafik Analisis Kualitas"])

        with tab1:
            total_data = len(df_clean)
            df_anomali = df_clean[df_clean['Status Validasi'] == 'Tidak Wajar (Perlu Dicek)']
            total_anomali = len(df_anomali)
            persen_anomali = (total_anomali / total_data * 100) if total_data > 0 else 0

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Input Data", total_data)
            col2.metric("Data Terindikasi Salah", total_anomali, f"{persen_anomali:.1f}% tingkat kesalahan", delta_color="inverse")
            
            avg_delta_rh = df_clean['Hitungan Delta RH'].abs().mean()
            col3.metric("Rata-rata Perubahan RH", f"{avg_delta_rh:.2f}" if not pd.isna(avg_delta_rh) else "0.00")
            
            st.markdown("### 📋 Data Lengkap dengan Hasil Hitung Otomatis")
            # Menampilkan kolom asli + hasil hitungan
            kolom_tampil = [col_waktu_awal, col_waktu_akhir, col_rh_awal, col_rh_akhir, 'Hitungan Delta RH', 'Hitungan Delta Time (Menit)', 'Status Validasi']
            st.dataframe(df_clean[kolom_tampil], use_container_width=True, height=350)

        with tab2:
            st.markdown("### 🚩 Baris Data Berstatus Tidak Wajar")
            if total_anomali > 0:
                st.error(f"Ditemukan {total_anomali} baris data yang melewati batas atau salah format input!")
                st.dataframe(df_anomali[kolom_tampil], use_container_width=True)
            else:
                st.success("🎉 Sempurna! Seluruh input data dari tim sudah berstatus wajar.")

        with tab3:
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                fig_hist = px.histogram(
                    df_clean, x="Hitungan Delta RH", color="Status Validasi", 
                    color_discrete_map={"Wajar (Normal)": "#008080", "Tidak Wajar (Perlu Dicek)": "#DC143C"},
                    title="Distribusi Perubahan (Delta) RH"
                )
                st.plotly_chart(fig_hist, use_container_width=True)
                
            with chart_col2:
                fig_scatter = px.scatter(
                    df_clean, x="Hitungan Delta Time (Menit)", y="Hitungan Delta RH", color="Status Validasi",
                    color_discrete_map={"Wajar (Normal)": "#008080", "Tidak Wajar (Perlu Dicek)": "#DC143C"},
                    title="Korelasi Durasi Waktu vs Perubahan RH"
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
