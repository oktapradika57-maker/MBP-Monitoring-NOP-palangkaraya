import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Halaman Dashboard
st.set_page_config(page_title="Dashboard Delta RH & Liter Genset", layout="wide")
st.title("📊 Dashboard Analisis Delta RH & Konsumsi Liter BBM Genset")
st.markdown("---")

# 2. Memuat Data Menggunakan Metode CSV Cerdas
@st.cache_data(ttl=300)
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
        'RH Awal', 'RH Akhir', 'Delta RH', 'Jumlah Liter', 'NOP', 'Month', 'PIC Take Over Ticket'
    ]
    
    # Validasi kolom yang benar-benar ada di Google Sheets Anda
    kolom_aman = [col for col in semua_kolom if col in kolom_target]
    
    # Tarik data penuh secara aman
    df = pd.read_csv(sheet_url, usecols=kolom_aman)
    
    # --- MEMBERSIHKAN & PROSES DATA ---
    # Konversi kolom teks utama menjadi string bersih agar filter lancar
    kolom_teks = ['Site Id', 'Site Name', 'Ticket Number SWFM', 'Regional', 'Type Ticket', 'NOP', 'Month', 'PIC Take Over Ticket']
    for col in kolom_teks:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
    # Pastikan format angka untuk Delta RH dan Jumlah Liter aman
    if 'Delta RH' in df.columns:
        df['Delta RH'] = pd.to_numeric(df['Delta RH'], errors='coerce').fillna(0.0)
    else:
        df['Delta RH'] = 0.0

    if 'Jumlah Liter' in df.columns:
        df['Jumlah Liter'] = pd.to_numeric(df['Jumlah Liter'], errors='coerce').fillna(0.0)
    else:
        df['Jumlah Liter'] = 0.0
        
    return df

try:
    with st.spinner('Sedang menarik data dari Google Sheets... Mohon tunggu.'):
        df = load_data_from_link()

    # 3. FITUR FILTER SIDEBAR PERMINTAAN BARU
    st.sidebar.header("Filter Navigasi")
    
    # Filter 1: NOP
    if 'NOP' in df.columns:
        nop_options = sorted([n for n in df["NOP"].unique() if n != 'nan' and pd.notna(n)])
        selected_nop = st.sidebar.multiselect("Pilih NOP:", options=nop_options, default=nop_options[:2] if nop_options else None)
        if selected_nop:
            df = df[df["NOP"].isin(selected_nop)]

    # Filter 2: Month (Bulan)
    if 'Month' in df.columns:
        month_options = sorted([m for m in df["Month"].unique() if m != 'nan' and pd.notna(m)])
        selected_month = st.sidebar.multiselect("Pilih Bulan (Month):", options=month_options, default=month_options if month_options else None)
        if selected_month:
            df = df[df["Month"].isin(selected_month)]

    # Filter 3: PIC Take Over Ticket
    if 'PIC Take Over Ticket' in df.columns:
        pic_options = sorted([p for p in df["PIC Take Over Ticket"].unique() if p != 'nan' and pd.notna(p)])
        selected_pic = st.sidebar.multiselect("Pilih PIC Take Over:", options=pic_options)
        if selected_pic:
            df = df[df["PIC Take Over Ticket"].isin(selected_pic)]

    # Filter 4: Dropdown Site Id
    if 'Site Id' in df.columns:
        site_id_options = sorted([s for s in df["Site Id"].unique() if s != 'nan' and pd.notna(s)])
        selected_site_id = st.sidebar.multiselect("Pilih Site Id:", options=site_id_options, default=site_id_options[:5] if site_id_options else None)
        if selected_site_id:
            df_filtered = df[df["Site Id"].isin(selected_site_id)]
        else:
            df_filtered = df
    else:
        df_filtered = df

    # 4. RINGKASAN UTAMA (KPI Cards)
    total_delta_rh = df_filtered['Delta RH'].sum()
    total_liter = df_filtered['Jumlah Liter'].sum()
    total_records = len(df_filtered)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Data Terfilter", f"{total_records:,} Tiket")
    with col2:
        st.metric("Total Delta RH (Jam Mesin)", f"{total_delta_rh:,.2f} Jam")
    with col3:
        st.metric("Total Konsumsi BBM (Jumlah Liter)", f"{total_liter:,.2f} Liter")

    st.markdown("---")

    # 5. VISUALISASI GRAFIK BARU
    if not df_filtered.empty:
        col_graph1, col_graph2 = st.columns(2)
        
        with col_graph1:
            st.subheader("📌 Total Delta RH per Site Id")
            # Mengelompokkan total Delta RH berdasarkan Site Id
            rh_per_site = df_filtered.groupby('Site Id')['Delta RH'].sum().reset_index()
            rh_per_site = rh_per_site.sort_values(by='Delta RH', ascending=False).head(30) # Ambil top 30 agar rapi
            
            fig_rh = px.bar(
                rh_per_site,
                x='Site Id',
                y='Delta RH',
                text_auto='.1f',
                title="Total Akumulasi Delta RH Berdasarkan Site Id (Top 30)",
                color_discrete_sequence=['#e67e22'] # Warna oranye khas mesin
            )
            fig_rh.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_rh, use_container_width=True)
            
        with col_graph2:
            st.subheader("📌 Total Jumlah Liter per Site Id")
            # Mengelompokkan total Jumlah Liter berdasarkan Site Id
            liter_per_site = df_filtered.groupby('Site Id')['Jumlah Liter'].sum().reset_index()
            liter_per_site = liter_per_site.sort_values(by='Jumlah Liter', ascending=False).head(30) # Ambil top 30
            
            fig_liter = px.bar(
                liter_per_site,
                x='Site Id',
                y='Jumlah Liter',
                text_auto='.0f',
                title="Total Konsumsi BBM (Jumlah Liter) Berdasarkan Site Id (Top 30)",
                color_discrete_sequence=['#2cc3c3'] # Warna cyan/hijau bensin
            )
            fig_liter.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_liter, use_container_width=True)
            
    else:
        st.warning("Tidak ada data yang cocok dengan kombinasi filter Anda saat ini.")

    st.markdown("---")

    # 6. TABEL DETAIL AMAN (Anti-Crash saat dibuka)
    st.subheader("📋 Tabel Detail Analisis Lapangan (Filtered)")
    
    # Tentukan urutan kolom tampilan di tabel
    kolom_tampilan = [
        'Ticket Number SWFM', 'NOP', 'Month', 'PIC Take Over Ticket', 'Site Id', 'Site Name', 
        'Regional', 'Cluster TO', 'Site Class', 'RH Awal', 'RH Akhir', 'Delta RH', 'Jumlah Liter'
    ]
    kolom_tersedia = [c for c in kolom_tampilan if c in df_filtered.columns]
    
    df_tabel_tampil = df_filtered[kolom_tersedia].copy()
    
    # Merender tabel Streamlit dengan performa maksimal
    st.dataframe(df_tabel_tampil, use_container_width=True)

except Exception as e:
    st.error(f"⚠️ Terjadi kendala teknis saat memuat dashboard: {e}")
