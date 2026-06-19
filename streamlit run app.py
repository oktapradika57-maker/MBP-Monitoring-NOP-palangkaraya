import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Halaman Dashboard
st.set_page_config(page_title="Dashboard Analisis RH Genset Real-time", layout="wide")
st.title("📊 Dashboard Analisis & Komparasi Jam Backup Genset (Live Data)")
st.markdown("---")

# 2. Memuat Data Langsung dari Google Sheets Link menggunakan format Excel (.xlsx)
@st.cache_data(ttl=600)  # Data otomatis di-refresh setiap 10 menit jika halaman di-reload
def load_data_from_link():
    # ID unik dari Google Sheets Anda
    sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
    
    # Menggunakan format export=xlsx agar stabil dan tidak error karena koma di dalam teks (Note/Description)
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    
    # Membaca sheet pertama
    df = pd.read_excel(sheet_url, sheet_name=0)
    
    # Memastikan format kolom waktu menjadi datetime agar bisa dihitung selisihnya
    df['RH Start Time'] = pd.to_datetime(df['RH Start Time'], errors='coerce')
    df['RH Stop Time'] = pd.to_datetime(df['RH Stop Time'], errors='coerce')
    
    # Bersihkan nama kolom Regional dari spasi tak terlihat
    if 'Regional' in df.columns:
        df["Regional"] = df["Regional"].astype(str).str.strip()
        
    # ─── LOGIKA PERHITUNGAN DAN SINKRONISASI DATA ───
    
    # A. Menghitung Durasi Real berdasarkan Selisih Waktu (RH Stop Time - RH Start Time) dalam Jam
    df['Durasi Aktual Waktu (Jam)'] = (df['RH Stop Time'] - df['RH Start Time']).dt.total_seconds() / 3600
    df['Durasi Aktual Waktu (Jam)'] = df['Durasi Aktual Waktu (Jam)'].round(2)
    
    # B. Mengambil data Delta RH (Selisih Jam Genset) berdasarkan kolom RH Akhir dan RH Awal
    df['Durasi RH Genset (Jam)'] = df['RH Akhir'] - df['RH Awal']
    df['Durasi RH Genset (Jam)'] = df['Durasi RH Genset (Jam)'].round(2)
    
    # C. Komparasi Selisih: (Durasi Mesin/Delta RH) vs (Durasi Aktual Waktu)
    df['Selisih Deviasi (Jam)'] = (df['Durasi RH Genset (Jam)'] - df['Durasi Aktual Waktu (Jam)']).round(2)
    
    return df

try:
    with st.spinner('Sedang menarik data terbaru dari Google Sheets...'):
        df = load_data_from_link()

    # 3. Fitur Filter di Sidebar berdasarkan Regional dan Type Ticket
    st.sidebar.header("Filter Dashboard")
    
    # Filter Regional
    regional_options = [r for r in df["Regional"].unique() if r != 'nan' and pd.notna(r)]
    selected_regional = st.sidebar.multiselect("Pilih Regional:", options=regional_options, default=regional_options)
    
    # Filter Type Ticket
    type_options = df["Type Ticket"].dropna().unique() if "Type Ticket" in df.columns else []
    selected_type = st.sidebar.multiselect("Pilih Type Ticket:", options=type_options, default=type_options)

    # Terapkan filter ke DataFrame
    df_filtered = df[df["Regional"].isin(selected_regional)]
    if len(type_options) > 0:
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

    # 5. Baris Visualisasi Grafik Pertama (Komparasi & Severity)
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("📌 Grafik Komparasi: Waktu Kalender vs Delta RH")
        # Ambil sampel 30 data teratas yang di-filter agar grafik tidak terlalu padat
        df_sample = df_filtered.head(30)
        
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
            title="Komparasi Jam Backup (Top 30 Data)",
            labels={'Ticket Number SWFM': 'Nomor Tiket SWFM', 'Total Jam': 'Durasi (Jam)'}
        )
        st.plotly_chart(fig_compare, use_container_width=True)

    with col_chart2:
        st.subheader("📌 Distribusi Severity Ticket")
        if "Severity" in df_filtered.columns:
            severity_data = df_filtered['Severity'].value_counts().reset_index()
            fig_sev = px.pie(severity_data, values='count', names='Severity', hole=0.4,
                             title="Persentase Tingkat Keparahan (Severity)")
            st.plotly_chart(fig_sev, use_container_width=True)
        else:
            st.info("Kolom 'Severity' tidak ditemukan di database.")

    st.markdown("---")

    # 6. Baris Visualisasi Grafik Kedua (Top Cluster & Site Class)
    col_chart3, col_chart4 = st.columns(2)

    with col_chart3:
        st.subheader("📌 Top 10 Cluster Terbanyak")
        if "Cluster TO" in df_filtered.columns:
            cluster_data = df_filtered['Cluster TO'].value_counts().head(10).reset_index()
            fig_cluster = px.bar(cluster_data, x='count', y='Cluster TO', orientation='h',
                                 title="10 Cluster Teratas Berdasarkan Jumlah Tiket",
                                 labels={'count': 'Jumlah Tiket', 'Cluster TO': 'Nama Cluster'})
            fig_cluster.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_cluster, use_container_width=True)
        else:
            st.info("Kolom 'Cluster TO' tidak ditemukan di database.")

    with col_chart4:
        st.subheader("📌 Distribusi Site Class")
        if "Site Class" in df_filtered.columns:
            site_class_data = df_filtered['Site Class'].value_counts().reset_index()
            fig_site = px.bar(site_class_data, x='Site Class', y='count', color='Site Class',
                              title="Jumlah Tiket per Kategori Site Class")
            st.plotly_chart(fig_site, use_container_width=True)
        else:
            st.info("Kolom 'Site Class' tidak ditemukan di database.")

    st.markdown("---")

    # 7. Tabel Tampilan Utama & Detail Audit Lapangan
    st.subheader("📋 Tabel Detail Analisis Data dan Validasi Lapangan")
    
    # Menampilkan kombinasi kolom dasar dan kolom perhitungan baru
    kolom_tampilan = [
        'Ticket Number SWFM', 'Site Id', 'Site Name', 'Regional',
        'RH Start Time', 'RH Stop Time', 'Durasi Aktual Waktu (Jam)',
        'RH Awal', 'RH Akhir', 'Durasi RH Genset (Jam)',
        'Selisih Deviasi (Jam)'
    ]
    
    # Opsional: Masukkan kolom 'Jumlah Liter' jika ada di data Anda
    if 'Jumlah Liter' in df_filtered.columns:
        kolom_tampilan.append('Jumlah Liter')
        
    # Memastikan hanya kolom yang benar-benar ada di DataFrame yang dipanggil
    kolom_tersedia = [col for col in kolom_tampilan if col in df_filtered.columns]
    
    st.dataframe(df_filtered[kolom_tersedia], use_container_width=True)

except Exception as e:
    st.error(f"⚠️ Terjadi error saat memuat data atau pustaka 'openpyxl' belum terinstall. Detail Error: {e}")
