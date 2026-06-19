import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Halaman Dashboard
st.set_page_config(page_title="Dashboard Analisis RH Genset Real-time", layout="wide")
st.title("📊 Dashboard Analisis & Komparasi Jam Backup Genset (Live Data)")
st.markdown("---")

# 2. Memuat Data Langsung dari Google Sheets Link
@st.cache_data(ttl=600)  # Data otomatis di-refresh setiap 10 menit jika halaman di-reload
def load_data_from_link():
    # ID unik dari Google Sheets Anda
    sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
    # Menggunakan gid=0 untuk membaca 'Sheet1' (sheet pertama)
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    
    # Membaca data CSV langsung dari url google sheets
    df = pd.read_csv(sheet_url)
    
    # Memastikan format kolom waktu menjadi datetime agar bisa dihitung selisihnya
    df['RH Start Time'] = pd.to_datetime(df['RH Start Time'], errors='coerce')
    df['RH Stop Time'] = pd.to_datetime(df['RH Stop Time'], errors='coerce')
    
    # ─── LOGIKA PERHITUNGAN DAN SINKRONISASI DATA ───
    
    # A. Menghitung Durasi Real berdasarkan Selisih Waktu (RH Stop Time - RH Start Time) dalam Jam
    df['Durasi Aktual Waktu (Jam)'] = (df['RH Stop Time'] - df['RH Start Time']).dt.total_seconds() / 3600
    df['Durasi Aktual Waktu (Jam)'] = df['Durasi Aktual Waktu (Jam)'].round(2)
    
    # B. Mengambil data Delta RH (Selisih Jam Genset) dari data asli Anda, atau hitung ulang untuk memastikan
    df['Durasi RH Genset (Jam)'] = df['RH Akhir'] - df['RH Awal']
    df['Durasi RH Genset (Jam)'] = df['Durasi RH Genset (Jam)'].round(2)
    
    # C. Komparasi Selisih: (Durasi Mesin/Delta RH) vs (Durasi Aktual Waktu)
    df['Selisih Deviasi (Jam)'] = (df['Durasi RH Genset (Jam)'] - df['Durasi Aktual Waktu (Jam)']).round(2)
    
    return df

try:
    with st.spinner('Sedang menarik data terbaru dari Google Sheets...'):
        df = load_data_from_link()

    # 3. Fitur Filter di Sidebar berdasarkan Regional
    st.sidebar.header("Filter Dashboard")
    
    # Pastikan data teks bersih dari spasi berlebih
    df["Regional"] = df["Regional"].astype(str).str.strip()
    regional_options = [r for r in df["Regional"].unique() if r != 'nan']
    
    selected_regional = st.sidebar.multiselect("Pilih Regional:", options=regional_options, default=regional_options)
    
    # Terapkan filter awal
    df_filtered = df[df["Regional"].isin(selected_regional)]

    # 4. Ringkasan Utama (KPI Cards)
    total_jam_waktu = df_filtered['Durasi Aktual Waktu (Jam)'].sum()
    total_jam_rh = df_filtered['Durasi RH Genset (Jam)'].sum()
    total_deviasi = df_filtered['Selisih Deviasi (Jam)'].sum()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Durasi Aktual Waktu (Log)", f"{total_jam_waktu:,.2f} Jam")
    with col2:
        st.metric("Total Durasi Delta RH (Mesin)", f"{total_jam_rh:,.2f} Jam")
    with col3:
        st.metric("Total Selisih Deviasi", f"{total_deviasi:,.2f} Jam", delta=f"{total_deviasi:.2f} Jam", delta_color="inverse")

    st.markdown("---")

    # 5. Visualisasi Grafik Komparasi
    st.subheader("📌 Grafik Komparasi: Durasi Aktual Waktu vs Delta RH (Genset)")
    
    # Ambil sampel 30 data teratas yang di-filter agar grafik tidak terlalu padat/berat
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
        title="Komparasi Jam Backup Kalender Waktu vs Angka Jam Mesin (Top 30 Data)",
        labels={'Ticket Number SWFM': 'Nomor Tiket SWFM', 'Total Jam': 'Durasi (Jam)'}
    )
    st.plotly_chart(fig_compare, use_container_width=True)

    st.markdown("---")

    # 6. Tabel Tampilan Utama Sesuai Kolom Gambar Anda
    st.subheader("📋 Tabel Analisis Data dan Validasi Lapangan")
    
    # Menampilkan kolom spesifik yang paling penting untuk kebutuhan audit Anda
    kolom_tampilan = [
        'Ticket Number SWFM', 'Site Id', 'Site Name', 'Regional',
        'RH Start Time', 'RH Stop Time', 'Durasi Aktual Waktu (Jam)',
        'RH Awal', 'RH Akhir', 'Durasi RH Genset (Jam)',
        'Selisih Deviasi (Jam)', 'Jumlah Liter'
    ]
    
    st.dataframe(df_filtered[kolom_tampilan], use_container_width=True)

except Exception as e:
    st.error(f"⚠️ Terjadi error saat memuat data. Mohon pastikan link dapat diakses publik atau format kolom sesuai. Detail Error: {e}")
