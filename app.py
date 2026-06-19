import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Halaman Dashboard
st.set_page_config(page_title="Dashboard Analisis RH Genset Real-time", layout="wide")
st.title("📊 Dashboard Analisis & Komparasi Jam Backup Genset (Live Data)")
st.markdown("---")

# 2. Memuat Data Menggunakan Metode CSV Ringan (Tanpa Butuh Openpyxl)
@st.cache_data(ttl=600)  # Data otomatis di-refresh setiap 10 menit jika halaman di-reload
def load_data_from_link():
    # ID unik dari Google Sheets Anda
    sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
    
    # URL format CSV untuk Sheet1
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    
    # FIX PARSERERROR: Hanya tarik kolom yang penting saja untuk visualisasi & hitungan.
    # Kolom teks panjang seperti 'Note' & 'Description' diabaikan agar tanda koma di dalamnya tidak merusak struktur tabel.
    kolom_yang_dibutuhkan = [
        'Ticket Number SWFM', 'Type Ticket', 'Severity', 'Site Id', 'Site Name', 
        'Regional', 'Cluster TO', 'Site Class', 'RH Start Time', 'RH Stop Time', 
        'RH Awal', 'RH Akhir', 'Jumlah Liter'
    ]
    
    # Membaca data dengan pembatasan kolom murni
    df = pd.read_csv(sheet_url, usecols=kolom_yang_dibutuhkan)
    
    # Memastikan format kolom waktu menjadi datetime agar bisa dihitung selisihnya
    df['RH Start Time'] = pd.to_datetime(df['RH Start Time'], errors='coerce')
    df['RH Stop Time'] = pd.to_datetime(df['RH Stop Time'], errors='coerce')
    
    # Bersihkan data teks dari spasi berlebih
    if 'Regional' in df.columns:
        df["Regional"] = df["Regional"].astype(str).str.strip()
    if 'Type Ticket' in df.columns:
        df["Type Ticket"] = df["Type Ticket"].astype(str).str.strip()
        
    # ─── LOGIKA PERHITUNGAN UTAMA ───
    
    # A. Menghitung Durasi Real berdasarkan Selisih Waktu (RH Stop Time - RH Start Time) dalam satuan Jam
    df['Durasi Aktual Waktu (Jam)'] = (df['RH Stop Time'] - df['RH Start Time']).dt.total_seconds() / 3600
    df['Durasi Aktual Waktu (Jam)'] = df['Durasi Aktual Waktu (Jam)'].round(2)
    
    # B. Menghitung Durasi Kerja Genset berdasarkan Selisih Jam Mekanik (RH Akhir - RH Awal)
    df['Durasi RH Genset (Jam)'] = df['RH Akhir'] - df['RH Awal']
    df['Durasi RH Genset (Jam)'] = df['Durasi RH Genset (Jam)'].round(2)
    
    # C. Komparasi Selisih: (Durasi Mesin) vs (Durasi Aktual Waktu Log)
    df['Selisih Deviasi (Jam)'] = (df['Durasi RH Genset (Jam)'] - df['Durasi Aktual Waktu (Jam)']).round(2)
    
    return df

try:
    with st.spinner('Sedang menarik data terbaru dari Google Sheets... Mohon tunggu beberapa detik.'):
        df = load_data_from_link()

    # 3. Fitur Filter di Sidebar berdasarkan Regional dan Type Ticket
    st.sidebar.header("Filter Dashboard")
    
    # Filter Regional
    regional_options = [r for r in df["Regional"].unique() if r != 'nan' and pd.notna(r)]
    selected_regional = st.sidebar.multiselect("Pilih Regional:", options=regional_options, default=regional_options)
    
    # Filter Type Ticket
    type_options = [t for t in df["Type Ticket"].unique() if t != 'nan' and pd.notna(t)]
    selected_type = st.sidebar.multiselect("Pilih Type Ticket:", options=type_options, default=type_options)

    # Terapkan filter ke DataFrame
    df_filtered = df[df["Regional"].isin(selected_regional) & df["Type Ticket"].isin(selected_type)]

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

    # 5. Baris Visualisasi Grafik Pertama (Komparasi Berdampingan & Severity)
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("📌 Grafik Komparasi: Waktu Kalender vs Delta RH")
        # Ambil sampel 30 data teratas yang lolos filter agar grafik batang tidak terlalu padat
        df_sample = df_filtered.dropna(subset=['Ticket Number SWFM']).head(30)
        
        chart_df = df_sample.reset_index().melt(
            id_vars=['Ticket Number SWFM', 'Site Name'], 
            value_vars=['Durasi Aktual Waktu (Jam)', 'Durasi RH Genset (Jam)'],
            var_name='Metode Perhitungan', value_name='Total Jam'
        )
        
        fig_compare = px.bar(
            chart_df, 
            x='Ticket Number SWFM', 
            y='Total Jam', 
            color='Metode Perhitungan', 
            barmode='group',
            title="Komparasi Jam Backup (Top 30 Data Hasil Filter)",
            labels={'Ticket Number SWFM': 'Nomor Tiket SWFM', 'Total Jam': 'Durasi (Jam)'}
        )
        st.plotly_chart(fig_compare, use_container_width=True)

    with col_chart2:
        st.subheader("📌 Distribusi Severity Ticket")
        severity_data = df_filtered['Severity'].dropna().value_counts().reset_index()
        fig_sev = px.pie(severity_data, values='count', names='Severity', hole=0.4,
                         title="Persentase Tingkat Keparahan (Severity)")
        st.plotly_chart(fig_sev, use_container_width=True)

    st.markdown("---")

    # 6. Baris Visualisasi Grafik Kedua (Top Cluster & Site Class)
    col_chart3, col_chart4 = st.columns(2)

    with col_chart3:
        st.subheader("📌 Top 10 Cluster Terbanyak")
        cluster_data = df_filtered['Cluster TO'].dropna().value_counts().head(10).reset_index()
        fig_cluster = px.bar(cluster_data, x='count', y='Cluster TO', orientation='h',
                             title="10 Cluster Teratas Berdasarkan Jumlah Tiket",
                             labels={'count': 'Jumlah Tiket', 'Cluster TO': 'Nama Cluster'})
        fig_cluster.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_cluster, use_container_width=True)

    with col_chart4:
        st.subheader("📌 Distribusi Site Class")
        site_class_data = df_filtered['Site Class'].dropna().value_counts().reset_index()
        fig_site = px.bar(site_class_data, x='Site Class', y='count', color='Site Class',
                          title="Jumlah Tiket per Kategori Site Class")
        st.plotly_chart(fig_site, use_container_width=True)

    st.markdown("---")

    # 7. Tabel Tampilan Utama & Detail Audit Lapangan
    st.subheader("📋 Tabel Detail Analisis Data dan Validasi Lapangan")
    
    # Memastikan urutan kolom rapi saat disajikan ke tabel
    kolom_tampilan = [
        'Ticket Number SWFM', 'Site Id', 'Site Name', 'Regional', 'Cluster TO', 'Site Class',
        'RH Start Time', 'RH Stop Time', 'Durasi Aktual Waktu (Jam)',
        'RH Awal', 'RH Akhir', 'Durasi RH Genset (Jam)',
        'Selisih Deviasi (Jam)', 'Jumlah Liter'
    ]
    
    st.dataframe(df_filtered[kolom_tampilan], use_container_width=True)

except Exception as e:
    st.error(f"⚠️ Terjadi kendala teknis saat memuat data: {e}")
