import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Halaman Dashboard Profesional
st.set_page_config(page_title="Dashboard Profesional Audit Genset", layout="wide")
st.title("📊 Dashboard Eksekutif: Audit Delta RH & Kewajaran BBM Genset")
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
    
    kolom_aman = [col for col in semua_kolom if col in kolom_target]
    df = pd.read_csv(sheet_url, usecols=kolom_aman)
    
    # --- PEMBERSIHAN DATA ---
    kolom_teks = ['Site Id', 'Site Name', 'Ticket Number SWFM', 'Regional', 'Type Ticket', 'NOP', 'Month', 'PIC Take Over Ticket']
    for col in kolom_teks:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
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

    # 3. TYPE FILTER PROFESIONAL (Menggunakan Grid Atas, Bukan Sidebar Samping)
    st.markdown("### 🔍 Panel Filter Data")
    
    # Membuat susunan 4 kolom sejajar untuk dropdown filter
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    
    with f_col1:
        if 'NOP' in df.columns:
            nop_options = sorted([n for n in df["NOP"].unique() if n != 'nan' and pd.notna(n)])
            selected_nop = st.multiselect("📍 Filter NOP:", options=nop_options, default=nop_options[:1] if nop_options else None)
            if selected_nop:
                df = df[df["NOP"].isin(selected_nop)]

    with f_col2:
        if 'Month' in df.columns:
            month_options = sorted([m for m in df["Month"].unique() if m != 'nan' and pd.notna(m)])
            selected_month = st.multiselect("📅 Filter Bulan:", options=month_options, default=month_options if month_options else None)
            if selected_month:
                df = df[df["Month"].isin(selected_month)]

    with f_col3:
        if 'PIC Take Over Ticket' in df.columns:
            pic_options = sorted([p for p in df["PIC Take Over Ticket"].unique() if p != 'nan' and pd.notna(p)])
            selected_pic = st.multiselect("👤 Filter PIC Take Over:", options=pic_options)
            if selected_pic:
                df = df[df["PIC Take Over Ticket"].isin(selected_pic)]

    with f_col4:
        if 'Site Id' in df.columns:
            site_id_options = sorted([s for s in df["Site Id"].unique() if s != 'nan' and pd.notna(s)])
            selected_site_id = st.multiselect("📡 Filter Site Id:", options=site_id_options, default=site_id_options[:5] if site_id_options else None)
            if selected_site_id:
                df_filtered = df[df["Site Id"].isin(selected_site_id)]
            else:
                df_filtered = df
        else:
            df_filtered = df

    st.markdown("---")

    # 4. RINGKASAN UTAMA (KPI Cards)
    total_delta_rh = df_filtered['Delta RH'].sum()
    total_liter = df_filtered['Jumlah Liter'].sum()
    total_records = len(df_filtered)
    
    # Hitung rata-rata rasio konsumsi bbm global terfilter
    rasio_global = (total_liter / total_delta_rh) if total_delta_rh > 0 else 0.0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Data Terfilter", f"{total_records:,} Tiket")
    with col2:
        st.metric("Total Delta RH (Jam Mesin)", f"{total_delta_rh:,.2f} Jam")
    with col3:
        st.metric("Total Konsumsi BBM", f"{total_liter:,.2f} Liter")
    with col4:
        st.metric("Rata-rata Rasio Konsumsi", f"{rasio_global:.2f} Ltr/Jam")

    st.markdown("---")

    # 5. VISUALISASI GRAFIK UTAMA
    if not df_filtered.empty:
        col_graph1, col_graph2 = st.columns(2)
        
        with col_graph1:
            st.subheader("📌 Total Delta RH per Site Id")
            rh_per_site = df_filtered.groupby('Site Id')['Delta RH'].sum().reset_index()
            rh_per_site = rh_per_site.sort_values(by='Delta RH', ascending=False).head(30)
            
            fig_rh = px.bar(
                rh_per_site, x='Site Id', y='Delta RH', text_auto='.1f',
                title="Total Akumulasi Delta RH Berdasarkan Site Id (Top 30)",
                color_discrete_sequence=['#e67e22']
            )
            fig_rh.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_rh, use_container_width=True)
            
        with col_graph2:
            st.subheader("📌 Total Jumlah Liter per Site Id")
            liter_per_site = df_filtered.groupby('Site Id')['Jumlah Liter'].sum().reset_index()
            liter_per_site = liter_per_site.sort_values(by='Jumlah Liter', ascending=False).head(30)
            
            fig_liter = px.bar(
                liter_per_site, x='Site Id', y='Jumlah Liter', text_auto='.0f',
                title="Total Konsumsi BBM (Jumlah Liter) Berdasarkan Site Id (Top 30)",
                color_discrete_sequence=['#2cc3c3']
            )
            fig_liter.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_liter, use_container_width=True)
            
    else:
        st.warning("Tidak ada data yang cocok dengan kombinasi filter Anda saat ini.")

    st.markdown("---")

    # 6. TABEL DETAIL DATA UTAMA
    st.subheader("📋 Tabel Detail Analisis Lapangan")
    kolom_tampilan = [
        'Ticket Number SWFM', 'NOP', 'Month', 'PIC Take Over Ticket', 'Site Id', 'Site Name', 
        'Regional', 'Cluster TO', 'Site Class', 'RH Awal', 'RH Akhir', 'Delta RH', 'Jumlah Liter'
    ]
    kolom_tersedia = [c for c in kolom_tampilan if c in df_filtered.columns]
    df_tabel_tampil = df_filtered[kolom_tersedia].copy()
    st.dataframe(df_tabel_tampil, use_container_width=True)

    st.markdown("---")

    # 7. FITUR BARU: ANALISA PERBANDINGAN KEWAJARAN KONSUMSI BBM (AUDIT REPORT)
    st.subheader("🔍 Analisa Audit: Perbandingan & Kewajaran Konsumsi BBM")
    st.markdown("Bagian ini otomatis mendeteksi tiket atau lokasi site yang memiliki pelaporan bensin tidak rasional / boros.")

    if not df_filtered.empty:
        # Duplikat data untuk kebutuhan audit
        df_audit = df_filtered.copy()
        
        # Hitung Rasio Konsumsi per baris tiket
        df_audit['Rasio (Ltr/Jam)'] = (df_audit['Jumlah Liter'] / df_audit['Delta RH']).round(2)
        # Tangani jika pembagian dengan nol (Delta RH = 0)
        df_audit.loc[df_audit['Delta RH'] == 0, 'Rasio (Ltr/Jam)'] = 0.0
        
        # Fungsi logika penentuan status kewajaran secara profesional
        def tentukan_kewajaran(row):
            rh = row['Delta RH']
            liter = row['Jumlah Liter']
            rasio = row['Rasio (Ltr/Jam)']
            
            if rh == 0 and liter > 0:
                return "❌ Tidak Wajar (BBM Terisi, Mesin Mati)"
            elif rh > 0 and liter == 0:
                return "⚠️ Atensi (Genset Jalan, BBM 0 Liter)"
            elif rh == 0 and liter == 0:
                return "🟢 Wajar (Tidak Ada Aktivitas)"
            elif rasio > 4.5:
                return "🚨 Indikasi Boros / Over-consumption"
            elif rasio < 1.0:
                return "📉 Terlalu Irit / Potensi Salah Input"
            else:
                return "🟢 Wajar"

        df_audit['Status Audit BBM'] = df_audit.apply(tentukan_kewajaran, axis=1)
        
        # Tampilkan Ringkasan Status Audit dalam bentuk angka total
        status_counts = df_audit['Status Audit BBM'].value_counts()
        
        c_aud1, c_aud2, c_aud3 = st.columns(3)
        with c_aud1:
            st.info(f"📊 Total Kasus Wajar: {status_counts.get('🟢 Wajar', 0) + status_counts.get('🟢 Wajar (Tidak Ada Aktivitas)', 0)} Tiket")
        with c_aud2:
            st.error(f"🚨 Total Kasus Indikasi Boros: {status_counts.get('🚨 Indikasi Boros / Over-consumption', 0)} Tiket")
        with c_aud3:
            st.warning(f"❌ Total Kasus Tidak Sinkron: {status_counts.get('❌ Tidak Wajar (BBM Terisi, Mesin Mati)', 0) + status_counts.get('⚠️ Atensi (Genset Jalan, BBM 0 Liter)', 0)} Tiket")
        
        st.markdown("#### Tabel Pemantauan Khusus (Urutan Kasus Paling Tidak Wajar / Boros)")
        
        # Tampilkan kolom audit khusus, urutkan dari rasio yang paling bengkak/boros
        kolom_audit_tampil = [
            'Ticket Number SWFM', 'Site Id', 'Site Name', 'NOP', 'PIC Take Over Ticket',
            'Delta RH', 'Jumlah Liter', 'Rasio (Ltr/Jam)', 'Status Audit BBM'
        ]
        
        df_audit_sorted = df_audit[kolom_audit_tampil].sort_values(by='Rasio (Ltr/Jam)', ascending=False)
        st.dataframe(df_audit_sorted, use_container_width=True)
        
    else:
        st.info("Pilih filter di atas untuk memunculkan laporan audit bbm.")

except Exception as e:
    st.error(f"⚠️ Terjadi kendala teknis saat memuat dashboard: {e}")
