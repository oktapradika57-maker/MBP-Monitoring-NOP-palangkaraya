import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Halaman Dashboard Profesional
st.set_page_config(page_title="Dashboard Analisis RH & BBM Genset", layout="wide")
st.title("📊 Dashboard Eksekutif: Audit Delta RH, Delta Time & Kewajaran BBM")
st.markdown("---")

# 2. Memuat Data Menggunakan Metode CSV Cerdas
@st.cache_data(ttl=300)
def load_data_from_link():
    sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    
    df_header = pd.read_csv(sheet_url, nrows=1)
    semua_kolom = df_header.columns.tolist()
    
    # Menambahkan 'Delta Time' ke daftar kolom target utama
    kolom_target = [
        'Ticket Number SWFM', 'Type Ticket', 'Severity', 'Site Id', 'Site Name', 
        'Regional', 'Cluster TO', 'Site Class', 'RH Start Time', 'RH Stop Time', 
        'RH Awal', 'RH Akhir', 'Delta RH', 'Delta Time', 'Jumlah Liter', 'NOP', 'Month', 'PIC Take Over Ticket'
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

    if 'Delta Time' in df.columns:
        df['Delta Time'] = pd.to_numeric(df['Delta Time'], errors='coerce').fillna(0.0)
    else:
        df['Delta Time'] = 0.0

    if 'Jumlah Liter' in df.columns:
        df['Jumlah Liter'] = pd.to_numeric(df['Jumlah Liter'], errors='coerce').fillna(0.0)
    else:
        df['Jumlah Liter'] = 0.0
        
    return df

try:
    with st.spinner('Sedang menarik data dari Google Sheets... Mohon tunggu.'):
        df = load_data_from_link()

    # 3. TYPE FILTER PROFESIONAL (Grid Atas)
    st.markdown("### 🔍 Panel Filter Data")
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

    # --- SINKRONISASI LOGIKA AUDIT ---
    if not df_filtered.empty:
        df_filtered = df_filtered.copy()
        df_filtered['Rasio (Ltr/Jam)'] = (df_filtered['Jumlah Liter'] / df_filtered['Delta RH']).round(2)
        df_filtered.loc[df_filtered['Delta RH'] == 0, 'Rasio (Ltr/Jam)'] = 0.0
        
        def tentukan_kewajaran(row):
            rh = row['Delta RH']
            liter = row['Jumlah Liter']
            rasio = row['Rasio (Ltr/Jam)']
            
            if rh == 0 and liter == 0:
                return "🟢 Tidak Ada Backup Time"
            elif rh == 0 and liter > 0:
                return "❌ Tidak Wajar (BBM Terisi, Mesin Mati)"
            elif rh > 0 and liter == 0:
                return "⚠️ Atensi (Genset Jalan, BBM 0 Liter)"
            elif rasio > 4.5:
                return "🚨 Indikasi Boros / Over-consumption"
            elif rasio < 1.0:
                return "📉 Terlalu Irit / Potensi Salah Input"
            else:
                return "🟢 Wajar"

        df_filtered['Status Audit BBM'] = df_filtered.apply(tentukan_kewajaran, axis=1)

    # 4. RINGKASAN UTAMA (KPI Cards dengan tambahan Delta Time)
    total_delta_rh = df_filtered['Delta RH'].sum() if not df_filtered.empty else 0
    total_delta_time = df_filtered['Delta Time'].sum() if not df_filtered.empty else 0
    total_liter = df_filtered['Jumlah Liter'].sum() if not df_filtered.empty else 0
    total_records = len(df_filtered)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Data Terfilter", f"{total_records:,} Tiket")
    with col2:
        st.metric("Total Delta Time (Waktu Log)", f"{total_delta_time:,.2f} Jam")
    with col3:
        st.metric("Total Delta RH (Jam Mesin)", f"{total_delta_rh:,.2f} Jam")
    with col4:
        st.metric("Total Konsumsi BBM", f"{total_liter:,.2f} Liter")

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
            
        st.markdown("---")
        
        # DISTRIBUSI PROPORSI STATUS AUDIT BBM
        st.subheader("📌 Distribusi Proporsi Status Audit BBM")
        audit_summary = df_filtered['Status Audit BBM'].value_counts().reset_index()
        audit_summary.columns = ['Status Audit BBM', 'Jumlah Tiket']
        
        warna_status_map = {
            "🟢 Wajar": "#2ecc71",
            "🟢 Tidak Ada Backup Time": "#95a5a6",
            "🚨 Indikasi Boros / Over-consumption": "#e74c3c",
            "❌ Tidak Wajar (BBM Terisi, Mesin Mati)": "#c0392b",
            "⚠️ Atensi (Genset Jalan, BBM 0 Liter)": "#f1c40f",
            "📉 Terlalu Irit / Potensi Salah Input": "#34495e"
        }
        
        fig_audit_pie = px.pie(
            audit_summary, values='Jumlah Tiket', names='Status Audit BBM', hole=0.4,
            title="Persentase dan Total Tiket Berdasarkan Hasil Evaluasi Validasi BBM",
            color='Status Audit BBM', color_discrete_map=warna_status_map
        )
        fig_audit_pie.update_traces(textinfo='percent+value', textposition='inside')
        st.plotly_chart(fig_audit_pie, use_container_width=True)
            
    else:
        st.warning("Tidak ada data yang cocok dengan kombinasi filter Anda saat ini.")

    st.markdown("---")

    # 6. TABEL DETAIL DATA UTAMA
    st.subheader("📋 Tabel Detail Analisis Lapangan (Termasuk Delta Time)")
    kolom_tampilan = [
        'Ticket Number SWFM', 'NOP', 'Month', 'PIC Take Over Ticket', 'Site Id', 'Site Name', 
        'Regional', 'Cluster TO', 'Site Class', 'Delta Time', 'RH Awal', 'RH Akhir', 'Delta RH', 'Jumlah Liter'
    ]
    kolom_tersedia = [c for c in kolom_tampilan if c in df_filtered.columns]
    df_tabel_tampil = df_filtered[kolom_tersedia].copy()
    st.dataframe(df_tabel_tampil, use_container_width=True)

    st.markdown("---")

    # 7. ANALISA PERBANDINGAN KEWAJARAN KONSUMSI BBM
    st.subheader("🔍 Analisa Audit: Perbandingan & Kewajaran Konsumsi BBM (Semua Data)")
    if not df_filtered.empty:
        status_counts = df_filtered['Status Audit BBM'].value_counts()
        c_aud1, c_aud2, c_aud3 = st.columns(3)
        with c_aud1:
            st.info(f"📊 Total Kasus Normal/Wajar: {status_counts.get('🟢 Wajar', 0)} Tiket")
        with c_aud2:
            st.success(f"💤 Total Tidak Ada Backup Time: {status_counts.get('🟢 Tidak Ada Backup Time', 0)} Tiket")
        with c_aud3:
            st.error(f"🚨 Total Kasus Bermasalah/Boros: {status_counts.get('🚨 Indikasi Boros / Over-consumption', 0) + status_counts.get('❌ Tidak Wajar (BBM Terisi, Mesin Mati)', 0)} Tiket")

    st.markdown("---")

    # 8. PERMINTAAN BARU: ANALISIS AKHIR KHUSUS SITE DENGAN DELTA RH TIDAK SAMA DENGAN 0 (ACTIVE SITES ONLY)
    st.subheader("🔥 Analisis Akhir: Khusus Site dengan Pemakaian Riil (Delta RH > 0)")
    st.markdown("Bagian ini memisahkan dan merangkum performa dari seluruh infrastruktur site genset yang **aktif beroperasi** di lapangan.")

    # Melakukan filter hanya data yang Delta RH > 0
    df_active = df_filtered[df_filtered['Delta RH'] > 0].copy() if not df_filtered.empty else pd.DataFrame()

    if not df_active.empty:
        total_active_sites = df_active['Site Id'].nunique()
        total_active_tickets = len(df_active)
        avg_active_rh = df_active['Delta RH'].mean()
        avg_active_liter = df_active['Jumlah Liter'].mean()
        
        # Tampilan parameter khusus site aktif
        act_col1, act_col2, act_col3, act_col4 = st.columns(4)
        with act_col1:
            st.metric("Total Site Id Aktif", f"{total_active_sites} Site")
        with act_col2:
            st.metric("Total Tiket Pemakaian", f"{total_active_tickets:,} Tiket")
        with act_col3:
            st.metric("Rata-rata Running Genset", f"{avg_active_rh:.2f} Jam / Tiket")
        with act_col4:
            st.metric("Rata-rata Pengisian BBM", f"{avg_active_liter:.2f} Liter / Tiket")
            
        st.markdown("#### 📋 Tabel Detail Rekam Jejak Audit Khusus Site Aktif")
        kolom_active_tampil = [
            'Ticket Number SWFM', 'Site Id', 'Site Name', 'NOP', 'PIC Take Over Ticket',
            'Delta Time', 'Delta RH', 'Jumlah Liter', 'Rasio (Ltr/Jam)', 'Status Audit BBM'
        ]
        df_active_sorted = df_active[kolom_active_tampil].sort_values(by='Delta RH', ascending=False)
        st.dataframe(df_active_sorted, use_container_width=True)
    else:
        st.info("Tidak ada aktivitas pemakaian genset (Delta RH > 0) pada kombinasi filter terpilih.")

except Exception as e:
    st.error(f"⚠️ Terjadi kendala teknis saat memuat dashboard: {e}")
