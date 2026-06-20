import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard Validasi Data", layout="wide")

st.title("Dashboard Validasi Input Data Tim 🔍")
st.write("Memantau kewajaran dan ketepatan input data RH (Relative Humidity) dan Waktu.")

# --- MENGAMBIL DATA DARI GOOGLE SHEETS ---
# Menggunakan @st.cache_data agar Streamlit tidak perlu mengunduh ulang data setiap kali kita klik sesuatu
@st.cache_data(ttl=60) # Cache akan direfresh setiap 60 detik
def load_data():
    # Mengambil ID dari link yang kamu berikan
    sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
    # Mengubahnya menjadi format CSV
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        return None

df = load_data()

if df is None:
    st.error("🚨 Gagal mengambil data. Pastikan akses Google Sheets sudah disetel ke 'Anyone with the link can view'.")
else:
    # Menampilkan data mentah (opsional, disembunyikan dalam expander)
    with st.expander("Lihat Data Mentah dari Spreadsheet"):
        st.dataframe(df)

    # --- PENGECEKAN KOLOM FOKUS ---
    kolom_fokus = ['RH awal', 'RH akhir', 'Delta RH', 'Delta Time']
    
    # Cek apakah kolom yang kita butuhkan benar-benar ada di spreadsheet
    missing_cols = [col for col in kolom_fokus if col not in df.columns]
    
    if missing_cols:
        st.warning(f"⚠️ Kolom berikut tidak ditemukan di Spreadsheet: **{', '.join(missing_cols)}**.")
        st.info("Pastikan nama kolom di atas persis sama dengan yang ada di baris pertama Google Sheets kamu (perhatikan spasi dan huruf besar/kecil).")
    else:
        st.markdown("---")
        st.subheader("⚙️ Parameter Validasi Kewajaran")
        st.write("Tentukan batas maksimal agar sistem bisa mendeteksi inputan yang 'tidak wajar' atau dicurigai salah ketik.")
        
        # Input filter untuk menentukan batas wajar
        col_param1, col_param2 = st.columns(2)
        with col_param1:
            batas_delta_rh = st.number_input("Batas Maksimal Toleransi Delta RH", value=15.0)
        with col_param2:
            batas_delta_time = st.number_input("Batas Maksimal Toleransi Delta Time", value=60.0)

        # --- LOGIKA DETEKSI ANOMALI ---
        # 1. Mengecek apakah Delta RH melebihi batas, atau nilai RH awal/akhir di luar nalar (misal RH harus 0-100)
        # 2. Mengecek apakah Delta Time melebihi batas waktu normal
        
        # Buat kolom baru untuk menandai status
        df['Status Data'] = 'Wajar (Normal)'
        
        kondisi_anomali = (
            (df['Delta RH'].abs() > batas_delta_rh) | 
            (df['Delta Time'] > batas_delta_time) |
            (df['RH awal'] < 0) | (df['RH awal'] > 100) |
            (df['RH akhir'] < 0) | (df['RH akhir'] > 100)
        )
        
        df.loc[kondisi_anomali, 'Status Data'] = 'Tidak Wajar (Perlu Dicek)'

        # --- BARIS 1: KPI (Indikator Utama) ---
        total_data = len(df)
        total_anomali = len(df[df['Status Data'] == 'Tidak Wajar (Perlu Dicek)'])
        persen_anomali = (total_anomali / total_data * 100) if total_data > 0 else 0

        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Baris Data", total_data)
        kpi2.metric("Data Tidak Wajar (Anomali)", total_anomali, f"{persen_anomali:.1f}% error rate", delta_color="inverse")
        kpi3.metric("Rata-rata Delta RH", f"{df['Delta RH'].mean():.2f}")

        st.markdown("---")

        # --- BARIS 2: TABEL DATA YANG HARUS DICEK TIM ---
        st.subheader("🚩 Daftar Inputan yang Perlu Divalidasi Ulang")
        df_anomali = df[df['Status Data'] == 'Tidak Wajar (Perlu Dicek)']
        
        if not df_anomali.empty:
            # Menampilkan hanya kolom yang relevan
            st.dataframe(df_anomali[kolom_fokus + ['Status Data']], use_container_width=True)
        else:
            st.success("Bagus sekali! Semua data yang diinput oleh tim berada dalam batas wajar.")

        st.markdown("---")

        # --- BARIS 3: VISUALISASI GRAFIK ---
        st.subheader("📊 Analisis Visual")
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.markdown("**Distribusi Inputan Delta RH**")
            # Histogram untuk melihat sebaran nilai Delta RH
            fig_hist = px.histogram(
                df, x="Delta RH", color="Status Data", 
                color_discrete_map={"Wajar (Normal)": "teal", "Tidak Wajar (Perlu Dicek)": "red"}
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        with col_chart2:
            st.markdown("**Korelasi Delta Time vs Delta RH**")
            # Scatter plot untuk mendeteksi data yang melenceng jauh (outliers)
            fig_scatter = px.scatter(
                df, x="Delta Time", y="Delta RH", color="Status Data",
                hover_data=['RH awal', 'RH akhir'], # Info tambahan saat kursor diarahkan ke titik
                color_discrete_map={"Wajar (Normal)": "teal", "Tidak Wajar (Perlu Dicek)": "red"}
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
