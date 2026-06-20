import streamlit as st
import pandas as pd
import plotly.express as px

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Genset RH Analytics", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    [data-testid="stMetricSimplevalue"] { font-size: 24px; font-weight: bold; }
    .main-title { font-size: 28px; font-weight: 700; color: #1E293B; margin-bottom: 2px; }
    .sub-title { font-size: 14px; color: #64748B; margin-bottom: 20px; }
    .alert-box { padding: 12px; background-color: #FEF2F2; border-left: 5px solid #EF4444; color: #991B1B; border-radius: 4px; margin-bottom: 15px; font-size: 14px; }
    .section-title { font-size: 20px; font-weight: 600; color: #1E293B; margin-top: 15px; margin-bottom: 15px; border-bottom: 2px solid #E2E8F0; padding-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2. LOAD DATA BERDASARKAN URUTAN KOLOM (ANTI-GABAL BEDA NAMA)
@st.cache_data
def load_data():
    sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df_raw = pd.read_csv(url)
        if df_raw.shape[1] < 6:
            st.error(f"❌ Spreadsheet kurang kolom (Minimal 6). Terdeteksi: {df_raw.shape[1]}")
            return pd.DataFrame()
        df = pd.DataFrame()
        df['Ticket Number SWFM'] = df_raw.iloc[:, 0].astype(str)
        df['Site Name'] = df_raw.iloc[:, 1].astype(str)
        df['RH Start Time'] = pd.to_datetime(df_raw.iloc[:, 2], errors='coerce')
        df['RH Stop Time'] = pd.to_datetime(df_raw.iloc[:, 3], errors='coerce')
        df['RH Start'] = pd.to_numeric(df_raw.iloc[:, 4], errors='coerce').fillna(0)
        df['RH Stop'] = pd.to_numeric(df_raw.iloc[:, 5], errors='coerce').fillna(0)
        
        # Kalkulasi Delta Time & Delta RH
        df['Delta Time (Waktu Kalender)'] = ((df['RH Stop Time'] - df['RH Start Time']).dt.total_seconds() / 3600).round(2).fillna(0)
        df['Delta RH (Jam Mesin)'] = (df['RH Stop'] - df['RH Start']).round(2).fillna(0)
        df['Selisih Komparasi (Jam)'] = (df['Delta RH (Jam Mesin)'] - df['Delta Time (Waktu Kalender)']).round(2)
        df['Status Validasi'] = df['Selisih Komparasi (Jam)'].apply(lambda x: "Sesuai" if abs(x) <= 0.1 else ("Kelebihan RH" if x > 0.1 else "Kekurangan RH"))
        return df
    except Exception as e:
        st.error(f"Gagal memuat data Google Sheets. Detail: {e}")
        return pd.DataFrame()

df_master = load_data()

if not df_master.empty:
    # 3. SIDEBAR FILTER (Default menarik semua data)
    with st.sidebar:
        st.markdown("### **Panel Kontrol Analisis**")
        st.markdown("---")
        site_options = sorted(df_master["Site Name"].dropna().unique())
        selected_site = st.multiselect("📍 Pilih Area / Site Name:", options=site_options, default=None, help="Kosongkan untuk menampilkan semua site.")
        status_options = df_master["Status Validasi"].unique()
        selected_status = st.multiselect("🔍 Status Validasi:", options=status_options, default=status_options)

    df_filtered = df_master.copy()
    if selected_site: df_filtered = df_filtered[df_filtered["Site Name"].isin(selected_site)]
    if selected_status: df_filtered = df_filtered[df_filtered["Status Validasi"].isin(selected_status)]

    # 4. HEADER
    st.markdown('<p class="main-title">📊 Dashboard Analisis & Komparasi Jam Backup Genset</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Audit validasi otomatis performa durasi kerja genset lapangan (Delta Time vs Delta RH).</p>', unsafe_allow_html=True)

    # 5. ANALISA KHUSUS DEVIASI > 1 JAM
    df_deviasi_tinggi = df_filtered[df_filtered['Selisih Komparasi (Jam)'].abs() > 1.0]
    jumlah_site_deviasi = df_deviasi_tinggi['Site Name'].nunique()
    
    if jumlah_site_deviasi > 0:
        st.markdown(f'<div class="alert-box">⚠️ <b>Peringatan Laporan Audit:</b> Terdeteksi <b>{jumlah_site_deviasi} Site</b> memiliki selisih waktu ekstrem <b>> 1 Jam</b> antara Delta Waktu Kalender dan Delta Jam Mesin.</div>', unsafe_allow_html=True)
        with st.expander("🔍 Klik di sini untuk melihat daftar rincian Site dengan Deviasi > 1 Jam"):
            st.dataframe(df_deviasi_tinggi[['Site Name', 'Ticket Number SWFM', 'Delta Time (Waktu Kalender)', 'Delta RH (Jam Mesin)', 'Selisih Komparasi (Jam)']].reset_index(drop=True), use_container_width=True)
    else:
        st.success("✅ Aman! Tidak ditemukan deviasi waktu ekstrem (> 1 jam) pada data terpilih.")

    # 6. RINGKASAN METRIK KPI
    t_aktual = df_filtered['Delta Time (Waktu Kalender)'].sum()
    t_rh = df_filtered['Delta RH (Jam Mesin)'].sum()
    t_selisih = df_filtered['Selisih Komparasi (Jam)'].sum()
    t_tiket = len(df_filtered)

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1: st.metric("📋 Total Tiket", f"{t_tiket} Tkt")
    with kpi2: st.metric("⏱️ Total Delta Time", f"{t_aktual:,.2f} Jam")
    with kpi3: st.metric("⚙️ Total Delta RH", f"{t_rh:,.2f} Jam")
    with kpi4: st.metric("⚠️ Total Deviasi", f"{t_selisih:,.2f} Jam", delta_color="inverse")

    # 7. SEKSI GRAFIK KORELASI SCATTER (Dibuat pendek satu baris agar aman dari error terpotong)
    st.markdown('<p class="section-title"> Abbas Analisis Korelasi Delta Time vs Delta RH</p>', unsafe_allow_html=True)
    col_scatter, col_metrics_detail = st.columns([2, 1])
    
    with col_scatter:
        max_val = max(df_filtered['Delta Time (Waktu Kalender)'].max(), df_filtered['Delta RH (Jam Mesin)'].max()) if not df_filtered.empty else 10
        fig_scat = px.scatter(df_filtered, x='Delta Time (Waktu Kalender)', y='Delta RH (Jam Mesin)', color='Status Validasi', hover_data=['Ticket Number SWFM', 'Site Name', 'Selisih Komparasi (Jam)'], color_discrete_map={'Sesuai': '#10B981', 'Kelebihan RH': '#EF4444', 'Kekurangan RH': '#3B82F6'}, title="Peta Distribusi Tiket (Garis Diagonal = Ideal Sesuai)", template="plotly_white")
        fig_scat.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color="gray", width=1, dash="dash"))
        fig_scat.update_layout(margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_scat, use_container_width=True)
        
    with col_metrics_detail:
        st.markdown("**Evaluasi Pola Kerja:**")
        r_time = df_filtered['Delta Time (Waktu Kalender)'].mean() if t_tiket > 0 else 0
        r_rh = df_filtered['Delta RH (Jam Mesin)'].mean() if t_tiket > 0 else 0
        st.info(f"💡 **Rata-rata per Tiket:**\n* Delta Time: {r_time:.2f} Jam\n* Delta RH: {r_rh:.2f} Jam")
        j_ok = len(df_filtered[df_filtered['Status Validasi'] == 'Sesuai'])
        p_akurasi = (j_ok / t_tiket * 100) if t_tiket > 0 else 100
        st.metric("🎯 Akurasi Sinkronisasi Data", f"{p_akurasi:.1f} %")

    # 8. VISUALISASI GRAFIK BATANG & PIE (One-Liner Format Terproteksi)
    st.markdown('<p class="section-title">📊 Grafik Perbandingan & Komposisi</p>', unsafe_allow_html=True)
    c_bar, c_pie = st.columns([2.5, 1])
    
    with c_bar:
        if not df_filtered.empty:
            ch_df = df_filtered.reset_index().melt(id_vars=['Ticket Number SWFM', 'Site Name'], value_vars=['Delta Time (Waktu Kalender)', 'Delta RH (Jam Mesin)'], var_name='Metode', value_name='Jam')
            f_bar = px.bar(ch_df, x='Ticket Number SWFM', y='Jam', color='Metode', barmode='group', color_discrete_map={'Delta Time (Waktu Kalender)': '#3B82F6', 'Delta RH (Jam Mesin)': '#F59E0B'}, template="plotly_white")
            f_bar.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(f_bar, use_container_width=True)

    with c_pie:
        if not df_filtered.empty:
            f_pie = px.pie(df_filtered, names='Status Validasi', hole=0.5, color='Status Validasi', color_discrete_map={'Sesuai': '#10B981', 'Kelebihan RH': '#EF4444', 'Kekurangan RH': '#3B82F6'}, template="plotly_white")
            f_pie.update_layout(margin=dict(l=5, r=5, t=5, b=5))
            st.plotly_chart(f_pie, use_container_width=True)

    # 9. TABEL RINCIAN DATA
    st.markdown("---")
    st.subheader("📋 Tabel Detail Komparasi")
    k_tampil = ['Ticket Number SWFM', 'Site Name', 'RH Start Time', 'RH Stop Time', 'Delta Time (Waktu Kalender)', 'RH Start', 'RH Stop', 'Delta RH (Jam Mesin)', 'Selisih Komparasi (Jam)', 'Status Validasi']
    
    def c_style(v):
        if v == 'Sesuai': return 'background-color: #D1FAE5; color: #065F46;'
        return 'background-color: #FEE2E2; color: #991B1B;' if 'Kelebihan' in str(v) else 'background-color: #DBEAFE; color: #1E40AF;'

    if not df_filtered.empty:
        st.dataframe(df_filtered[k_tampil].style.map(c_style, subset=['Status Validasi']), use_container_width=True, height=350)
        st.download_button("📥 Download Laporan LENGKAP (.CSV)", data=df_filtered[k_tampil].to_csv(index=False).encode('utf-8'), file_name="Audit_Genset.csv", mime="text/csv")
