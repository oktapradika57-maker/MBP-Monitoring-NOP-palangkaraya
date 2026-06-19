import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# =========================================================================
# ⚙️ KONFIGURASI HALAMAN UTAMA DASHBOARD
# =========================================================================
st.set_page_config(
    page_title="MBP & Fuel Operations Analytics Dashboard",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ID Spreadsheet Baru Anda (DATABASE MBP)
SPREADSHEET_ID = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
csv_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv"

# Custom CSS untuk tampilan kartu metrik dan performa profesional
st.markdown("""
    <style>
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        text-align: center;
    }
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        color: #0f172a;
        margin-top: 5px;
    }
    .metric-label {
        font-size: 13px;
        color: #64748b;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⛽ MBP & Fuel Operations Analytics Dashboard")
st.caption("Live Analytical System Synchronized with Google Sheets (DATABASE MBP)")
st.markdown("---")

# =========================================================================
# 💾 DATA SINKRONISASI & PEMBERSIHAN
# =========================================================================
@st.cache_data(ttl=5)
def load_mbp_data(url):
    try:
        df = pd.read_csv(url)
        # Standarisasi nama kolom hapus spasi gaib
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        return str(e)

with st.spinner("🔄 Sedang menyinkronkan data operasional MBP..."):
    df_raw = load_mbp_data(csv_url)

if isinstance(df_raw, str):
    st.error("⚠️ Gagal memuat data dari link Google Sheets yang diberikan.")
    st.markdown(f"**Detail Error:** `{df_raw}`")
    st.stop()
elif df_raw is None or df_raw.empty:
    st.warning("⚠️ Data di dalam spreadsheet kosong atau tidak terbaca.")
    st.stop()
else:
    df = df_raw.dropna(how='all', axis=0).copy()

    # =========================================================================
    # 🔍 DETEKSI KOLOM SECARA DYNAMIC & OTOMATIS (Mencegah Typo/Case Sensitive)
    # =========================================================================
    def find_col(keywords, default_idx=0):
        for c in df.columns:
            if any(k in c.upper() for k in keywords):
                return c
        return df.columns[default_idx] if default_idx < len(df.columns) else df.columns[0]

    KOLOM_MONTH = find_col(['MONTH', 'BULAN'])
    KOLOM_PIC = find_col(['PIC', 'TAKEOVER', 'PETUGAS', 'NAMA'])
    KOLOM_LITER = find_col(['LITER', 'DELTA JUMLAH LITER', 'DELTA_LITER'])
    KOLOM_RH_AWAL = find_col(['RH AWAL', 'RH_AWAL'])
    KOLOM_RH_AKHIR = find_col(['RH AKHIR', 'RH_AKHIR'])
    KOLOM_DELTA_RH = find_col(['DELTA RH', 'DELTA_RH', 'RUNNING HOUR'])
    KOLOM_SUMMARY = find_col(['SUMMARY', 'KETERANGAN', 'STATUS'])

    # Bersihkan tipe data numerik agar kalkulasi grafik akurat dan anti-error
    for col_num in [KOLOM_LITER, KOLOM_RH_AWAL, KOLOM_RH_AKHIR, KOLOM_DELTA_RH]:
        if col_num in df.columns:
            df[col_num] = pd.to_numeric(df[col_num].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)

    # Pastikan data bulan dan PIC bersih dari nilai Kosong/NaN
    df[KOLOM_MONTH] = df[KOLOM_MONTH].fillna("Unknown-Month").astype(str)
    df[KOLOM_PIC] = df[KOLOM_PIC].fillna("Tanpa PIC").astype(str)

    # Hitung Rasio Konsumsi BBM Rasional (Liter per Jam) -> Delta Liter / Delta RH
    df['Liter_Per_Jam'] = np.where(df[KOLOM_DELTA_RH] > 0, df[KOLOM_LITER] / df[KOLOM_DELTA_RH], 0)
    df['Liter_Per_Jam'] = df['Liter_Per_Jam'].round(2)

    # =========================================================================
    # ⚙️ PANEL FILTER UTAMA (BULAN & PIC TAKEOVER)
    # =========================================================================
    st.sidebar.header("🔍 Filter Operasional")
    
    # Filter 1: Bulan (Month)
    list_bulan = ["Semua Bulan"] + sorted(list(df[KOLOM_MONTH].unique()))
    selected_month = st.sidebar.selectbox("Pilih Bulan Analisis:", list_bulan)
    
    # Filter 2: PIC Takeover
    list_pic = ["Semua PIC"] + sorted(list(df[KOLOM_PIC].unique()))
    selected_pic = st.sidebar.selectbox("Pilih PIC Takeover:", list_pic)

    # Proses Penyaringan Data Berdasarkan Pilihan User
    df_filtered = df.copy()
    if selected_month != "Semua Bulan":
        df_filtered = df_filtered[df_filtered[KOLOM_MONTH] == selected_month]
    if selected_pic != "Semua PIC":
        df_filtered = df_filtered[df_filtered[KOLOM_PIC] == selected_pic]

    if st.sidebar.button("🔄 Refresh Data & Clear Cache", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # =========================================================================
    # 📌 RINGKASAN METRIK EXECUTIVE (KPI KINERJA REFUELING & ENGINE)
    # =========================================================================
    total_liter = df_filtered[KOLOM_LITER].sum()
    total_rh = df_filtered[KOLOM_DELTA_RH].sum()
    avg_efficiency = total_liter / total_rh if total_rh > 0 else 0
    total_ops = len(df_filtered)

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">⛽ TOTAL BBM KELUAR</div><div class="metric-value">{total_liter:,.1f} L</div></div>', unsafe_allow_html=True)
    with m_col2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">⏱️ TOTAL RUNNING HOURS (RH)</div><div class="metric-value">{total_rh:,.1f} Jam</div></div>', unsafe_allow_html=True)
    with m_col3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">📊 RATA-RATA KONSUMSI</div><div class="metric-value">{avg_efficiency:.2f} L/Jam</div></div>', unsafe_allow_html=True)
    with m_col4:
        st.markdown(f'<div class="metric-card"><div class="metric-label">📋 TOTAL AKTIVITAS/TRIP</div><div class="metric-value">{total_ops} Rit</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # =========================================================================
    # 📊 GRAFIK VISUALISASI ANALISA DAN AKURASI DATA
    # =========================================================================
    g_col1, g_col2 = st.columns([1.6, 1.4])

    with g_col1:
        st.markdown("### 📈 Tren Konsumsi BBM & Running Hours per Data Point")
        if not df_filtered.empty:
            fig_tren = go.Figure()
            # Bar Chart untuk Volume Liter
            fig_tren.add_trace(go.Bar(
                x=df_filtered.index, y=df_filtered[KOLOM_LITER],
                name="Pengisian BBM (Liter)", marker_color='#10b981', opacity=0.75
            ))
            # Line Chart untuk Delta Running Hours (Sumbu Y Kedua)
            fig_tren.add_trace(go.Scatter(
                x=df_filtered.index, y=df_filtered[KOLOM_DELTA_RH],
                name="Durasi Kerja (Hours)", mode='lines+markers', line=dict(color='#ef4444', width=2),
                yaxis='y2'
            ))
            # Set Layout Dual Sumbu
            fig_tren.update_layout(
                title="Pola Korelasi Jumlah Liter Terhadap Durasi Kerja Genset",
                xaxis=dict(title="Data Entri Index"),
                yaxis=dict(title="Volume BBM (Liter)", titlefont=dict(color="#10b981"), tickfont=dict(color="#10b981")),
                yaxis2=dict(title="Durasi Running Hours", titlefont=dict(color="#ef4444"), tickfont=dict(color="#ef4444"), overlaying='y', side='right'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=40, r=40, t=60, b=40),
                height=350, template="plotly_white"
            )
            st.plotly_chart(fig_tren, use_container_width=True)
        else:
            st.info("Tidak ada data untuk memuat grafik tren.")

    with g_col2:
        st.markdown("### 👥 Produktivitas Pengisian BBM berdasarkan PIC Takeover")
        if not df_filtered.empty:
            # Mengelompokkan total liter berdasarkan PIC yang bertugas
            df_pic_summary = df_filtered.groupby(KOLOM_PIC)[KOLOM_LITER].sum().reset_index()
            fig_pic = px.pie(
                df_pic_summary, names=KOLOM_PIC, values=KOLOM_LITER,
                title="Proporsi Distribusi BBM per PIC Takeover",
                hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_pic.update_layout(height=350, margin=dict(l=20, r=20, t=60, b=20))
            st.plotly_chart(fig_pic, use_container_width=True)

    st.markdown("---")

    # =========================================================================
    # 📋 LAYOUT TABEL DATA DETAILS & SUMMARY ANALYTICS
    # =========================================================================
    st.subheader("📋 Rincian Log Aktivitas MBP")
    
    # Menata susunan kolom yang krusial agar mudah dibaca oleh tim operasional
    kolom_tampil = [KOLOM_MONTH, KOLOM_PIC, KOLOM_RH_AWAL, KOLOM_RH_AKHIR, KOLOM_DELTA_RH, KOLOM_LITER, 'Liter_Per_Jam']
    # Masukkan kolom Summary jika memang ada di dalam sheet
    if KOLOM_SUMMARY in df_filtered.columns:
        kolom_tampil.append(KOLOM_SUMMARY)
        
    st.dataframe(
        df_filtered[kolom_tampil],
        use_container_width=True,
        hide_index=True
    )

    # =========================================================================
    # 💡 SEKSI INSIGHT & ANALISA OPERASIONAL (AUTOMATED INSIGHT)
    # =========================================================================
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("💡 LIHAT ANALISA & REKOMENDASI OPERASIONAL (EXECUTIVE SUMMARY)", expanded=True):
        if not df_filtered.empty:
            # Mencari data entri dengan tingkat konsumsi pemborosan bbm tertinggi
            idx_boros = df_filtered['Liter_Per_Jam'].idxmax()
            pic_boros = df_filtered.loc[idx_boros, KOLOM_PIC]
            max_ratio = df_filtered.loc[idx_boros, 'Liter_Per_Jam']
            
            st.markdown(f"""
            1. **Analisis Efisiensi Sistem**: Saat ini nilai rata-rata konsumsi berada di angka **{avg_efficiency:.2f} Liter/Jam**. Jika angka ini melebihi spesifikasi standar pabrikan genset MBP, disarankan untuk melakukan pengecekan berkala terhadap kebocoran tangki atau ketepatan kalibrasi meteran pengisian.
            2. **Anomali Konsumsi Tertinggi**: Konsumsi tertinggi terdeteksi menyentuh rasio **{max_ratio:.2f} Liter/Jam**, yang dicatat pada saat penanganan operasional oleh **PIC {pic_boros}**. Direkomendasikan melakukan audit silang (*cross-check*) log teknis khusus pada entri tersebut.
            3. **Kontribusi Pengisian**: Filter saat ini mendeteksi aktivitas sebanyak **{total_ops} pengisian** yang sukses terekam. Monitoring berkelanjutan diperlukan untuk memastikan keakuratan input data pada parameter *RH Awal* dan *RH Akhir*.
            """)
        else:
            st.caption("Pilih filter data untuk memunculkan ringkasan analisa otomatis.")
