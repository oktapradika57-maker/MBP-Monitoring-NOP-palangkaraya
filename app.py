import streamlit as st
import pandas as pd
import plotly.express as px

# 1. KONFIGURASI HALAMAN UTAMA (KEMBALI KE TEMPLATE AWAL)
st.set_page_config(
    page_title="Genset RH Analytics", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Kustomisasi UI & Estetika Dashboard
st.markdown("""
    <style>
    [data-testid="stMetricSimplevalue"] { font-size: 24px; font-weight: bold; }
    .main-title { font-size: 28px; font-weight: 700; color: #1E293B; margin-bottom: 2px; }
    .sub-title { font-size: 14px; color: #64748B; margin-bottom: 20px; }
    .alert-box { padding: 12px; background-color: #FEF2F2; border-left: 5px solid #EF4444; color: #991B1B; border-radius: 4px; margin-bottom: 15px; font-size: 14px; }
    .section-title { font-size: 20px; font-weight: 600; color: #1E293B; margin-top: 20px; margin-bottom: 15px; border-bottom: 2px solid #E2E8F0; padding-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2. MEMUAT & MEMPROSES DATA (Berdasarkan Posisi Kolom Spreadsheet)
@st.cache_data
def load_data():
    sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        df_raw = pd.read_csv(url)
        if df_raw.shape[1] < 6:
            st.error(f"❌ Urutan kolom di Google Sheets tidak sesuai. Butuh minimal 6 kolom.")
            return pd.DataFrame()
            
        df = pd.DataFrame()
        df['Ticket Number SWFM'] = df_raw.iloc[:, 0].astype(str)
        df['Site Name'] = df_raw.iloc[:, 1].astype(str)
        df['RH Start Time'] = pd.to_datetime(df_raw.iloc[:, 2], errors='coerce')
        df['RH Stop Time'] = pd.to_datetime(df_raw.iloc[:, 3], errors='coerce')
        df['RH Start'] = pd.to_numeric(df_raw.iloc[:, 4], errors='coerce').fillna(0)
        df['RH Stop'] = pd.to_numeric(df_raw.iloc[:, 5], errors='coerce').fillna(0)
        
        # LOGIKA ANALISIS DELTA TIME & DELTA RH
        df['Delta Time (Waktu Kalender)'] = ((df['RH Stop Time'] - df['RH Start Time']).dt.total_seconds() / 3600).round(2).fillna(0)
        df['Delta RH (Jam Mesin)'] = (df['RH Stop'] - df['RH Start']).round(2).fillna(0)
        df['Selisih Komparasi (Jam)'] = (df['Delta RH (Jam Mesin)'] - df['Delta Time (Waktu Kalender)']).round(2)
        
        # Klasifikasi Status Validasi
        df['Status Validasi'] = df['Selisih Komparasi (Jam)'].apply(
            lambda x: "Sesuai" if abs(x) <= 0.1 else ("Kelebihan RH" if x > 0.1 else "Kekurangan RH")
        )
        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari Google Sheets. Detail Error: {e}")
        return pd.DataFrame()

# Eksekusi Pembacaan Sumber Data
df_master = load_data()

if not df_master.empty:
    
    # 3. SIDEBAR PANEL KONTROL (Menarik Seluruh Data secara Otomatis)
    with st.sidebar:
        st.markdown("### **Panel Kontrol Analisis**")
        st.markdown("---")
        
        site_options = sorted(df_master["Site Name"].dropna().unique())
        selected_site = st.multiselect(
            "📍 Pilih Area / Site Name:", 
            options=site_options, 
            default=None,
            help="Biarkan kosong untuk langsung menarik seluruh data site."
        )
        
        status_options = df_master["Status Validasi"].unique()
        selected_status = st.multiselect(
            "🔍 Status Validasi:",
            options=status_options,
            default=status_options
        )

    # Implementasi Filter Pilihan Data
    df_filtered = df_master.copy()
    if selected_site:
        df_filtered = df_filtered[df_filtered["Site Name"].isin(selected_site)]
    if selected_status:
        df_filtered = df_filtered[df_filtered["Status Validasi"].isin(selected_status)]

    # 4. HEADER UTAMA DASHBOARD
    st.markdown('<p class="main-title">📊 Dashboard Analisis & Komparasi Jam Backup Genset</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Membandingkan validasi durasi kerja log kalender (Delta Time) terhadap perputaran Hour Meter mesin (Delta RH).</p>', unsafe_allow_html=True)

    # ─── BARU: SEKSI AUDIT DEVIASI EKSTREM (> 1 JAM) ───
    df_deviasi_tinggi = df_filtered[df_filtered['Selisih Komparasi (Jam)'].abs() > 1.0]
    jumlah_site_deviasi = df_deviasi_tinggi['Site Name'].nunique()
    
    if jumlah_site_deviasi > 0:
        st.markdown(f"""
        <div class="alert-box">
            ⚠️ <b>Peringatan Audit Akurasi:</b> Terdeteksi <b>{jumlah_site_deviasi} Site</b> memiliki selisih hitung (Delta) tidak wajar yang bernilai <b>&gt; 1 Jam</b>.
        </div>
        """, unsafe_allow_html=True)
        with st.expander("🔍 Klik di sini untuk melihat daftar rincian tiket dengan deviasi > 1 jam"):
            st.dataframe(df_deviasi_tinggi[['Ticket Number SWFM', 'Site Name', 'Delta Time (Waktu Kalender)', 'Delta RH (Jam Mesin)', 'Selisih Komparasi (Jam)']].reset_index(drop=True), use_container_width=True)
    else:
        st.success("✅ Sinkronisasi Aman! Tidak ditemukan log delta dengan deviasi di atas 1 jam.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 5. RINGKASAN RINGKAS METRIK KPI UTAMA
    total_aktual = df_filtered['Delta Time (Waktu Kalender)'].sum()
    total_rh = df_filtered['Delta RH (Jam Mesin)'].sum()
    total_selisih = df_filtered['Selisih Komparasi (Jam)'].sum()
    total_tiket = len(df_filtered)

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric(label="📋 Total Tiket", value=f"{total_tiket} Laporan")
    with kpi2:
        st.metric(label="⏱️ Total Delta Time (Kalender)", value=f"{total_aktual:,.2f} Jam")
    with kpi3:
        st.metric(label="⚙️ Total Delta RH (HM Mesin)", value=f"{total_rh:,.2f} Jam")
    with kpi4:
        st.metric(label="⚠️ Total Selisih Deviasi", value=f"{total_selisih:,.2f} Jam", delta_color="inverse")

    # 6. SEKSI GRAFIK ANALISIS KORELASI DELTA TIME VS DELTA RH
    st.markdown('<p class="section-title">📈 Analisis Hubungan Delta Time vs Delta RH</p>', unsafe_allow_html=True)
    col_scatter, col_insight_box = st.columns([2, 1])
    
    with col_scatter:
        max_val = max(df_filtered['Delta Time (Waktu Kalender)'].max(), df_filtered['Delta RH (Jam Mesin)'].max()) if not df_filtered.empty else 10
        fig_scatter = px.scatter(
            df_filtered, x='Delta Time (Waktu Kalender)', y='Delta RH (Jam Mesin)', color='Status Validasi',
            hover_data=['Ticket Number SWFM', 'Site Name', 'Selisih Komparasi (Jam)'],
            color_discrete_map={'Sesuai': '#10B981', 'Kelebihan RH': '#EF4444', 'Kekurangan RH': '#3B82F6'},
            title="Peta Sebaran Tiket (Garis Putus-Putus Menunjukkan Batas Linear Sesuai / Ideal)", template="plotly_white"
        )
        fig_scatter.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color="gray", width=1, dash="dash"))
        fig_scatter.update_layout(margin=dict(l=10, r=10, t=35, b=10))
        st.plotly_chart(fig_scatter, use_container_width=True)
        
    with col_insight_box:
        st.markdown("**Metrik Pola Log Lapangan:**")
        rata_time = df_filtered['Delta Time (Waktu Kalender)'].mean() if total_tiket > 0 else 0
        rata_rh = df_filtered['Delta RH (Jam Mesin)'].mean() if total_tiket > 0 else 0
        st.info(f"💡 **Rata-rata per Tiket:**\n* Delta Time: {rata_time:.2f} Jam\n* Delta RH: {rata_rh:.2f} Jam")
        
        jumlah_sesuai = len(df_filtered[df_filtered['Status Validasi'] == 'Sesuai'])
        persen_akurasi = (jumlah_sesuai / total_tiket * 100) if total_tiket > 0 else 100
        st.metric(label="🎯 Tingkat Akurasi Validasi Data", value=f"{persen_akurasi:.1f} %")

    # 7. BAGIAN GRAFIK BATANG & GRAFIK PIE (KEMBALI KE TAMPILAN AWAL YANG RAPI)
    st.markdown('<p class="section-title">📊 Visualisasi Perbandingan Komponen Data</p>', unsafe_allow_html=True)
    col_chart, col_insight = st.columns([2.5, 1])
    
    with col_chart:
        st.subheader("📌 Grafik Batang Komparasi per Tiket")
        if not df_filtered.empty:
            chart_df = df_filtered.reset_index().melt(
                id_vars=['Ticket Number SWFM', 'Site Name'], 
                value_vars=['Delta Time (Waktu Kalender)', 'Delta RH (Jam Mesin)'],
                var_name='Metode Hitung', value_name='Total Jam'
            )
            fig_compare = px.bar(
                chart_df, x='Ticket Number SWFM', y='Total Jam', color='Metode Hitung', barmode='group',
                color_discrete_map={'Delta Time (Waktu Kalender)': '#3B82F6', 'Delta RH (Jam Mesin)': '#F59E0B'},
                template="plotly_white"
            )
            fig_compare.update_layout(margin=dict(l=20, r=20, t=20, b=20), hovermode="x unified")
            st.plotly_chart(fig_compare, use_container_width=True)

    with col_insight:
        st.subheader("💡 Komposisi Validasi")
        if not df_filtered.empty:
            fig_pie = px.pie(
                df_filtered, names='Status Validasi', hole=0.5, color='Status Validasi',
                color_discrete_map={'Sesuai': '#10B981', 'Kelebihan RH': '#EF4444', 'Kekurangan RH': '#3B82F6'},
                template="plotly_white"
            )
            fig_pie.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # 8. TABEL RINCIAN DETAIL DATA & DOWNLOAD LAPORAN (Perbaikan Versi Stabil Tanpa Styler Crash)
    st.subheader("📋 Tabel Detail Komparasi & Validasi Laporan")
    kolom_tampilan = [
        'Ticket Number SWFM', 'Site Name', 'RH Start Time', 'RH Stop Time', 
        'Delta Time (Waktu Kalender)', 'RH Start', 'RH Stop', 'Delta RH (Jam Mesin)', 
        'Selisih Komparasi (Jam)', 'Status Validasi'
    ]
    
    if not df_filtered.empty:
        # Menampilkan dataframe standar agar responsif, rapi, dan bebas error Library Styler
        st.dataframe(df_filtered[kolom_tampilan], use_container_width=True, height=380)
        
        # Tombol Download Data Berformat CSV
        csv_data = df_filtered[kolom_tampilan].to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Unduh Laporan LENGKAP (.CSV)", data=csv_data, file_name="Laporan_Audit_Genset.csv", mime="text/csv")
