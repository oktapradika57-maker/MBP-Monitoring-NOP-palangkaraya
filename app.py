import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Halaman Dashboard
st.set_page_config(page_title="Dashboard Analisis RH Genset Real-time", layout="wide")
st.title("📊 Dashboard Analisis & Komparasi Jam Backup Genset (Live Data)")
st.markdown("---")

# 2. Memuat Data Menggunakan Metode CSV Cerdas (Auto-Fix Column Error)
@st.cache_data(ttl=600)
def load_data_from_link():
    sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    
    # LANGKAH 1: Baca baris pertama saja untuk mengambil semua nama kolom asli dari Google Sheets
    df_header = pd.read_csv(sheet_url, nrows=1)
    semua_kolom = df_header.columns.tolist()
    
    # LANGKAH 2: Daftar kolom target yang ingin kita ambil (abaikan Note, Description, dll)
    kolom_target = [
        'Ticket Number SWFM', 'Type Ticket', 'Severity', 'Site Id', 'Site Name', 
        'Regional', 'Cluster TO', 'Site Class', 'RH Start Time', 'RH Stop Time', 
        'RH Awal', 'RH Akhir', 'Jumlah Liter'
    ]
    
    # LANGKAH 3: Filter otomatis. Hanya ambil kolom target yang VALID dan COCOK dengan Google Sheets
    # Ini mencegah error "Usecols do not match" jika ada salah ketik huruf besar/kecil di database
    kolom_aman_terdeteksi = [col for col in semua_kolom if col in kolom_target]
    
    # LANGKAH 4: Tarik data penuh hanya untuk kolom yang aman saja
    df = pd.read_csv(sheet_url, usecols=kolom_aman_terdeteksi)
    
    # ─── PROSES & KALKULASI DATA ───
    
    # Pastikan format waktu benar jika kolomnya terdeteksi
    if 'RH Start Time' in df.columns and 'RH Stop Time' in df.columns:
        df['RH Start Time'] = pd.to_datetime(df['RH Start Time'], errors='coerce')
        df['RH Stop Time'] = pd.to_datetime(df['RH Stop Time'], errors='coerce')
        df['Durasi Aktual Waktu (Jam)'] = ((df['RH Stop Time'] - df['RH Start Time']).dt.total_seconds() / 3600).round(2)
    else:
        df['Durasi Aktual Waktu (Jam)'] = 0

    # Pastikan format RH mesin benar jika kolomnya terdeteksi
    if 'RH Awal' in df.columns and 'RH Akhir' in df.columns:
        df['RH Awal'] = pd.to_numeric(df['RH Awal'], errors='coerce').fillna(0)
        df['RH Akhir'] = pd.to_numeric(df['RH Akhir'], errors='coerce').fillna(0)
        df['Durasi RH Genset (Jam)'] = (df['RH Akhir'] - df['RH Awal']).round(2)
    else:
        df['Durasi RH Genset (Jam)'] = 0
    
    # Hitung Deviasi Selisih
    df['Selisih Deviasi (Jam)'] = (df['Durasi RH Genset (Jam)'] - df['Durasi Aktual Waktu (Jam)']).round(2)
    
    return df

try:
    with st.spinner('Sedang menarik data terbaru dari Google Sheets... Mohon tunggu.'):
        df = load_data_from_link()

    # 3. Fitur Filter di Sidebar
    st.sidebar.header("Filter Dashboard")
    
    # Filter Regional (jika kolom ada)
    if 'Regional' in df.columns:
        df["Regional"] = df["Regional"].astype(str).str.strip()
        regional_options = [r for r in df["Regional"].unique() if r != 'nan' and pd.notna(r)]
        selected_regional = st.sidebar.multiselect("Pilih Regional:", options=regional_options, default=regional_options)
        df_filtered = df[df["Regional"].isin(selected_regional)]
    else:
        df_filtered = df

    # Filter Type Ticket (jika kolom ada)
    if 'Type Ticket' in df.columns:
        df_filtered["Type Ticket"] = df_filtered["Type Ticket"].astype(str).str.strip()
        type_options = [t for t in df_filtered["Type Ticket"].unique() if t != 'nan' and pd.notna(t)]
        selected_type = st.sidebar.multiselect("Pilih Type Ticket:", options=type_options, default=type_options)
        df_filtered = df_filtered[df_filtered["Type Ticket"].isin(selected_type)]

    # 4. Ringkasan Utama (KPI Cards)
    total_jam_waktu = df_filtered['Durasi Aktual Waktu (Jam)'].sum()
    total_jam_rh = df_filtered['Durasi RH Genset (Jam)'].sum()
    total_deviasi = df_filtered['Selisih Deviasi (Jam)'].sum()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Durasi Waktu Log (Kalender)", f"{total_jam_waktu:,.2f} Jam")
    with col2:
        st.metric("Total Durasi Delta RH (Mesin)", f"{total_jam_rh:,.2f} Jam")
    with col3:
        st.metric("Total Selisih Deviasi", f"{total_deviasi:,.2f} Jam", delta=f"{total_deviasi:.2f} Jam", delta_color="inverse")

    st.markdown("---")

    # 5. Grafik Komparasi Berdampingan
    st.subheader("📌 Grafik Komparasi: Waktu Kalender vs Delta RH")
    df_sample = df_filtered.dropna(subset=['Ticket Number SWFM'] if 'Ticket Number SWFM' in df_filtered.columns else []).head(30)
    
    id_col = 'Ticket Number SWFM' if 'Ticket Number SWFM' in df_filtered.columns else df_filtered.index.name
    
    chart_df = df_sample.reset_index().melt(
        id_vars=[id_col, 'Site Name'] if 'Site Name' in df_filtered.columns else [id_col], 
        value_vars=['Durasi Aktual Waktu (Jam)', 'Durasi RH Genset (Jam)'],
        var_name='Metode Perhitungan', value_name='Total Jam'
    )
    
    fig_compare = px.bar(
        chart_df, 
        x=id_col, 
        y='Total Jam', 
        color='Metode Perhitungan', 
        barmode='group',
        title="Komparasi Jam Backup (Top 30 Data)",
        labels={id_col: 'ID / Nomor Tiket', 'Total Jam': 'Durasi (Jam)'}
    )
    st.plotly_chart(fig_compare, use_container_width=True)

    st.markdown("---")

    # 6. Baris Visualisasi Grafik Kedua (Severity)
    if 'Severity' in df_filtered.columns:
        st.subheader("📌 Distribusi Severity Ticket")
        severity_data = df_filtered['Severity'].dropna().value_counts().reset_index()
        fig_sev = px.pie(severity_data, values='count', names='Severity', hole=0.4)
        st.plotly_chart(fig_sev, use_container_width=True)

    st.markdown("---")

    # 7. Tabel Tampilan Utama & Detail Audit Lapangan
    st.subheader("📋 Tabel Detail Analisis Data dan Validasi Lapangan")
    
    # Tampilkan kolom apa saja yang berhasil lolos sensor otomatis tadi
    kolom_tampilan_akhir = [col for col in df_filtered.columns if col in kolom_aman_terdeteksi] + ['Durasi Aktual Waktu (Jam)', 'Durasi RH Genset (Jam)', 'Selisih Deviasi (Jam)']
    
    st.dataframe(df_filtered[kolom_tampilan_akhir], use_container_width=True)

except Exception as e:
    st.error(f"⚠️ Terjadi kendala teknis saat memuat data: {e}")
