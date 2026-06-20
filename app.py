
import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Data Validation", layout="wide", initial_sidebar_state="expanded")

# --- SIDEBAR UNTUK PENGATURAN (LEBIH PROFESIONAL) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2091/2091665.png", width=50) # Ikon opsional
    st.header("⚙️ Parameter Validasi")
    st.write("Atur batas toleransi kewajaran input data.")
    batas_delta_rh = st.number_input("Maksimal Delta RH", value=15.0, step=1.0)
    batas_delta_time = st.number_input("Maksimal Delta Time", value=60.0, step=1.0)
    st.markdown("---")
    st.caption("Dashboard v2.0 | Auto-sync dengan Google Sheets")

# --- JUDUL UTAMA ---
st.title("Dashboard Validasi Input Tim 🔍")
st.markdown("Memantau anomali dan ketepatan input data RH dan Waktu secara *real-time*.")
st.markdown("---")

# --- MENGAMBIL & MEMBERSIHKAN DATA ---
@st.cache_data(ttl=60)
def load_data():
    sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        df = pd.read_csv(csv_url)
        # PENTING: Membersihkan spasi di nama kolom agar tidak error
        df.columns = df.columns.str.strip()
        return df
    except Exception:
        return None

df = load_data()

# --- PENANGANAN ERROR (TAMPILAN LEBIH RAPI) ---
if df is None:
    st.error("🚨 Gagal memuat data dari sumber.")
elif "RH awal" not in df.columns:
    st.error("🚨 Akses ditolak atau Format Salah.")
    st.warning("Penyebab Paling Sering: Google Sheets masih 'Restricted'. Pastikan akses Share diubah menjadi 'Anyone with the link'.")
    with st.expander("Klik untuk melihat detail kolom yang terbaca oleh sistem saat ini"):
        st.write("Kolom yang ditemukan:", df.columns.tolist())
else:
    # --- LOGIKA VALIDASI ---
    kolom_fokus = ['RH awal', 'RH akhir', 'Delta RH', 'Delta Time']
    
    # Memastikan data terbaca sebagai angka (mengatasi salah ketik huruf)
    for col in kolom_fokus:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df['Status Data'] = 'Wajar (Normal)'
    kondisi_anomali = (
        (df['Delta RH'].abs() > batas_delta_rh) | 
        (df['Delta Time'] > batas_delta_time) |
        (df['RH awal'] < 0) | (df['RH awal'] > 100) |
        (df['RH akhir'] < 0) | (df['RH akhir'] > 100) |
        (df[kolom_fokus].isna().any(axis=1)) # Mendeteksi ada sel yang kosong/huruf
    )
    df.loc[kondisi_anomali, 'Status Data'] = 'Tidak Wajar (Perlu Dicek)'

    # --- LAYOUT MENGGUNAKAN TABS (AGAR TIDAK BERANTAKAN) ---
    tab1, tab2, tab3 = st.tabs(["📊 Ringkasan KPI", "🚩 Data Anomali (Wajib Cek)", "📈 Visualisasi Data"])

    # TAB 1: KPI
    with tab1:
        total_data = len(df)
        df_anomali = df[df['Status Data'] == 'Tidak Wajar (Perlu Dicek)']
        total_anomali = len(df_anomali)
        persen_anomali = (total_anomali / total_data * 100) if total_data > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Input Data", total_data)
        col2.metric("Data Anomali (Salah)", total_anomali, f"{persen_anomali:.1f}% error", delta_color="inverse")
        col3.metric("Rata-rata Delta RH", f"{df['Delta RH'].mean():.2f}")
        
        st.caption("Data mentah secara keseluruhan:")
        st.dataframe(df, use_container_width=True, height=250)

    # TAB 2: TABEL ANOMALI
    with tab2:
        if total_anomali > 0:
            st.error(f"Ditemukan {total_anomali} baris data yang melebihi batas toleransi atau formatnya salah!")
            st.dataframe(df_anomali, use_container_width=True)
        else:
            st.success("🎉 Luar biasa! Semua data saat ini berstatus wajar dan normal.")

    # TAB 3: VISUALISASI
    with tab3:
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            fig_hist = px.histogram(
                df, x="Delta RH", color="Status Data", 
                color_discrete_map={"Wajar (Normal)": "teal", "Tidak Wajar (Perlu Dicek)": "crimson"},
                title="Distribusi Sebaran Delta RH"
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            
        with chart_col2:
            fig_scatter = px.scatter(
                df, x="Delta Time", y="Delta RH", color="Status Data",
                color_discrete_map={"Wajar (Normal)": "teal", "Tidak Wajar (Perlu Dicek)": "crimson"},
                title="Korelasi Delta Time vs Delta RH"
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
