import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse

st.set_page_config(page_title="Dashboard MBP Professional", layout="wide")

# Styling CSS untuk tampilan lebih bersih
st.markdown("""
    <style>
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #008080; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 MBP Quality Control Dashboard")
st.markdown("---")

# Data loading... (Logic sama dengan sebelumnya)
sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
@st.cache_data(ttl=300)
def load_data(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(sheet_name)}"
    return pd.read_csv(url).dropna(how='all')

df = load_data("Sheet1")

# --- DASHBOARD UI BERJENJANG ---

# 1. Row Ringkasan (KPI Cards)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Input", len(df))
with col2:
    st.metric("Rata-rata RH Awal", f"{df.iloc[:, 0].mean():.1f}")
with col3:
    st.metric("Rata-rata RH Akhir", f"{df.iloc[:, 1].mean():.1f}")

st.markdown("---")

# 2. Row Konten (Tabel vs Chart)
tab_data, tab_grafik = st.tabs(["📋 Tabel Data Detail", "📈 Visualisasi Tren"])

with tab_data:
    st.dataframe(df, use_container_width=True, height=400)

with tab_grafik:
    fig = px.line(df, title="Tren Perubahan Nilai dari Waktu ke Waktu")
    st.plotly_chart(fig, use_container_width=True)
