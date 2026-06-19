import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Halaman Dashboard
st.set_page_config(page_title="Dashboard Analisis RH Genset", layout="wide")
st.title("📊 Dashboard Analisis & Komparasi Jam Backup Genset (Live Data)")
st.markdown("---")

# 2. Memuat Data Menggunakan Metode CSV Cerdas
@st.cache_data(ttl=300)  # Refresh otomatis setiap 5 menit jika halaman direload
def load_data_from_link():
    sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    
    # Ambil struktur kolom pertama kali
    df_header = pd.read_csv(sheet_url, nrows=1)
    semua_kolom = df_header.columns.tolist()
    
    # Kolom krusial yang kita butuhkan dari spreadsheet Anda
    kolom_target = [
        'Ticket Number SWFM', 'Type Ticket', 'Severity', 'Site Id', 'Site Name', 
        'Regional', 'Cluster TO', 'Site Class', 'RH Start Time', 'RH Stop Time', 
        'RH Awal', 'RH Akhir', 'Delta RH', 'Jumlah Liter'
    ]
    
    # Validasi kolom yang benar-benar ada di Google Sheets Anda
    kolom_aman = [col for col in semua_kolom if col in kolom_target]
    
    # Tarik data penuh secara aman
    df = pd.read_csv(sheet_url, usecols=kolom_aman)
    
    # --- MEMBERSIHKAN & PROSES DATA ---
    # Konversi kolom teks Id/Name menjadi string bersih agar filter dropdown lancar
    for col in ['Site Id', 'Site Name', 'Ticket Number SWFM', 'Regional', 'Type Ticket']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
    # Pastikan format data waktu aman
    if 'RH Start Time' in df.columns and 'RH Stop Time' in df.columns:
        df['RH Start Time'] = pd.to_datetime(df['RH Start Time'], errors='coerce')
        df['RH Stop Time'] = pd.to_datetime(df['RH Stop Time'], errors='coerce')
        # Hitung durasi aktual log (dalam jam)
        df['Durasi Aktual Waktu (Jam)'] = ((df['RH Stop Time'] - df['RH Start Time']).dt.total_seconds() / 3600).round(2)
    else:
        df['Durasi Aktual Waktu (Jam)'] = 0.0

    # Menggunakan 'Delta RH' asli dari spreadsheet Anda (Kolom BX)
    if 'Delta RH' in df.columns:
        df['Delta RH'] = pd.to_numeric(df['Delta RH'], errors='coerce').fillna(0.0).round(2)
    else:
        # Fallback jika kolom bermasalah
        if 'RH Awal' in df.columns and 'RH Akhir' in df.columns:
            df['RH Awal'] = pd.to_numeric(df['RH Awal'], errors='coerce').fillna(0.0)
            df['RH Akhir'] = pd.to_numeric(df['RH Akhir'], errors='coerce').fillna(0.0)
            df['Delta RH'] = (df['RH Akhir'] - df['RH Awal']).round(2)
        else:
            df['Delta RH'] = 0.0
            
    # Selisih/Deviasi: Jam Mesin Asli (Delta RH) dikurangi Jam Waktu Log
    df['Selisih Deviasi (Jam)'] = (df['Delta RH'] - df['Durasi Aktual Waktu (Jam)']).round(2)
    
    return df

try:
    with st.spinner('Sedang menarik data dari Google Sheets... Mohon tunggu.'):
        df = load_data_from_link()

    # 3. FITUR FILTER BARU (Menggunakan Dropdown Site Id murni)
    st.sidebar.header("Filter Navigasi")
    
    # Ambil list semua Site Id unik yang valid (bukan teks 'nan')
    site_id_options = sorted([s for s in df["Site Id"].unique() if s != 'nan' and pd.notna(s)])
    
    # Dropdown Multi-select khusus Site Id (Default: memunculkan 3 site pertama agar grafik rapi)
    selected_site_id = st.sidebar.multiselect(
        "Pilih Site Id:", 
        options=site_id_options, 
        default=site_id_options[:3] if len(site_id_options) > 0 else None
    )
    
    # Terapkan filter ke dataframe utama
    if selected_site_id:
        df_filtered = df[df["Site Id"].isin(selected_site_id)]
    else:
        df_filtered = df

    # 4. RINGKASAN UTAMA (KPI Cards)
    total_jam_waktu = df_filtered['Durasi Aktual Waktu (Jam)'].sum()
    total_delta_rh = df_filtered['Delta RH'].sum()
    total_deviasi = df_filtered['Selisih Deviasi (Jam)'].sum()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Durasi Waktu Log (Kalender)", f"{total_jam_waktu:,.2f} Jam")
    with col2:
        st.metric("Total Delta RH Asli (Jam Mesin)", f"{total_delta_rh:,.2f} Jam")
    with col3:
        st.metric("Total Selisih Deviasi", f"{total_deviasi:,.2f} Jam", delta=f"{total_deviasi:.2f} Jam", delta_color="inverse")

    st.markdown("---")

    # 5. PERBAIKAN GRAFIK (Lebih bersih dan dikelompokkan per Site Id/Tiket)
    st.subheader("📌 Grafik Komparasi: Durasi Aktual Waktu vs Delta RH")
    
    if not df_filtered.empty:
        # Supaya grafik tidak menumpuk berantakan, kita batasi maksimal 40 tiket teratas yang tampil di chart
        df_chart_sample = df_filtered.head(40)
        
        # Mengubah struktur data agar bisa dibaca barmode 'group' dengan benar
        chart_df = df_chart_sample.reset_index().melt(
            id_vars=['Ticket Number SWFM', 'Site Id', 'Site Name'], 
            value_vars=['Durasi Aktual Waktu (Jam)', 'Delta RH'],
            var_name='Metode Hitung', value_name='Total Jam'
        )
        
        # Membuat grafik batang berdampingan yang presisi
        fig_compare = px.bar(
            chart_df, 
            x='Ticket Number SWFM', 
            y='Total Jam', 
            color='Metode Hitung', 
            barmode='group',
            text_auto='.1f', # Munculkan angka jam di atas batang grafik agar mudah dibaca
            title=f"Perbandingan Backup per Tiket untuk Site Terpilih (Maks. 40 Tiket Utama)",
            labels={'Ticket Number SWFM': 'Nomor Tiket SWFM', 'Total Jam': 'Durasi (Jam)'},
            color_discrete_map={'Durasi Aktual Waktu (Jam)': '#3498db', 'Delta RH': '#e67e22'} # Warna biru vs orange kontras
        )
        fig_compare.update_layout(xaxis_tickangle=-45, legend_title_text='Kategori')
        st.plotly_chart(fig_compare, use_container_width=True)
    else:
        st.warning("Tidak ada data untuk Site Id yang dipilih.")

    st.markdown("---")

    # 6. PERBAIKAN TABEL DETAIL (Konversi paksa ke string/format aman agar 100% bisa dibuka)
    st.subheader("📋 Tabel Detail Analisis Data dan Validasi Lapangan")
    
    # Kolom final yang disajikan di monitor
    kolom_tampilan_akhir = [
        'Ticket Number SWFM', 'Site Id', 'Site Name', 'Regional', 'Cluster TO', 'Site Class',
        'RH Start Time', 'RH Stop Time', 'Durasi Aktual Waktu (Jam)',
        'RH Awal', 'RH Akhir', 'Delta RH', 'Selisih Deviasi (Jam)'
    ]
    if 'Jumlah Liter' in df_filtered.columns:
        kolom_tampilan_akhir.append('Jumlah Liter')
        
    kolom_tersedia = [c for c in kolom_tampilan_akhir if c in df_filtered.columns]
    
    # Pembersihan final sebelum masuk st.dataframe (Mengubah objek waktu / kosong agar tidak crash saat dibuka)
    df_tabel_tampil = df_filtered[kolom_tersedia].copy()
    if 'RH Start Time' in df_tabel_tampil.columns:
        df_tabel_tampil['RH Start Time'] = df_tabel_tampil['RH Start Time'].dt.strftime('%Y-%m-%d %H:%M').fillna('-')
    if 'RH Stop Time' in df_tabel_tampil.columns:
        df_tabel_tampil['RH Stop Time'] = df_tabel_tampil['RH Stop Time'].dt.strftime('%Y-%m-%d %H:%M').fillna('-')
    
    # Menampilkan tabel aman tanpa takut error loading data lagi
    st.dataframe(df_tabel_tampil, use_container_width=True)

except Exception as e:
    st.error(f"⚠️ Terjadi kendala teknis saat memuat dashboard: {e}")
