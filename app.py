import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Halaman Dashboard
st.set_page_config(page_title="Dashboard Analisis RH Genset", layout="wide")
st.title("📊 Dashboard Analisis & Komparasi Jam Backup Genset")
st.markdown("---")

# 2. Memuat Data dari Google Sheets / Excel
@st.cache_data
def load_data():
    # Ganti dengan path file lokal Anda jika dijalankan offline, 
    # atau biarkan membaca langsung dari database Anda.
    df = pd.read_excel("database_mbp.xlsx") 
    
    # Konversi kolom waktu ke format datetime agar bisa dikurangi
    df['RH Start Time'] = pd.to_datetime(df['RH Start Time'], errors='coerce')
    df['RH Stop Time'] = pd.to_datetime(df['RH Stop Time'], errors='coerce')
    
    # ─── LOGIKA PERHITUNGAN UTAMA ───
    
    # A. Menghitung Durasi Real/Aktual berdasarkan Jam Kalender (dalam satuan Jam)
    df['Durasi Aktual Waktu (Jam)'] = (df['RH Stop Time'] - df['RH Start Time']).dt.total_seconds() / 3600
    df['Durasi Aktual Waktu (Jam)'] = df['Durasi Aktual Waktu (Jam)'].round(2)
    
    # B. Menghitung Durasi dari Angka Hour Meter (RH) Mesin Genset
    # Catatan: Jika Anda menggunakan kolom 'RH Awal' & 'RH Akhir', silakan ganti nama kolomnya di bawah ini
    df['Durasi RH Genset (Jam)'] = df['RH Stop'] - df['RH Start']
    df['Durasi RH Genset (Jam)'] = df['Durasi RH Genset (Jam)'].round(2)
    
    # C. Komparasi Selisih (Mencari deviasi/selisih antara hitungan Waktu vs hitungan RH)
    df['Selisih Komparasi (Jam)'] = (df['Durasi RH Genset (Jam)'] - df['Durasi Aktual Waktu (Jam)']).round(2)
    
    return df

try:
    df = load_data()

    # 3. Filter Sidebar (Contoh berdasarkan Site Name)
    st.sidebar.header("Filter Data")
    site_options = df["Site Name"].dropna().unique()
    selected_site = st.sidebar.multiselect("Pilih Site Name:", options=site_options, default=site_options[:5] if len(site_options) > 0 else None)

    if selected_site:
        df_filtered = df[df["Site Name"].isin(selected_site)]
    else:
        df_filtered = df

    # 4. Ringkasan KPI Utama
    total_aktual = df_filtered['Durasi Aktual Waktu (Jam)'].sum()
    total_rh = df_filtered['Durasi RH Genset (Jam)'].sum()
    total_selisih = df_filtered['Selisih Komparasi (Jam)'].sum()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Jam Backup (Waktu Aktual)", f"{total_aktual:.2f} Jam")
    with col2:
        st.metric("Total Jam Backup (RH Genset)", f"{total_rh:.2f} Jam")
    with col3:
        st.metric("Total Selisih (Deviasi)", f"{total_selisih:.2f} Jam", 
                  help="Jika angka menjauhi nilai 0, tandanya ada ketidakcocokan antara jam kerja genset di lapangan dengan laporan waktu log.")

    st.markdown("---")

    # 5. Grafik Komparasi Berdampingan
    st.subheader("📌 Grafik Batang Komparasi per Tiket")
    
    # Restrukturisasi data agar bisa dibaca Plotly Express secara 'grouped'
    chart_df = df_filtered.reset_index().melt(
        id_vars=['Ticket Number SWFM', 'Site Name'], 
        value_vars=['Durasi Aktual Waktu (Jam)', 'Durasi RH Genset (Jam)'],
        var_name='Metode Hitung', value_name='Total Jam'
    )
    
    fig_compare = px.bar(
        chart_df, 
        x='Ticket Number SWFM', 
        y='Total Jam', 
        color='Metode Hitung', 
        barmode='group',
        title="Perbandingan Jam Backup Kalender (Waktu) vs Angka Hour Meter Mesin (RH)",
        labels={'Ticket Number SWFM': 'Nomor Tiket SWFM'}
    )
    st.plotly_chart(fig_compare, use_container_width=True)

    st.markdown("---")

    # 6. Tabel Tampilan Detail
    st.subheader("📋 Tabel Detail Komparasi & Validasi Data")
    kolom_tampilan = [
        'Ticket Number SWFM', 'Site Name', 
        'RH Start Time', 'RH Stop Time', 'Durasi Aktual Waktu (Jam)',
        'RH Start', 'RH Stop', 'Durasi RH Genset (Jam)',
        'Selisih Komparasi (Jam)'
    ]
    st.dataframe(df_filtered[kolom_tampilan], use_container_width=True)

except Exception as e:
    st.error(f"⚠️ Terjadi kesalahan pembacaan atau kalkulasi data: {e}")
