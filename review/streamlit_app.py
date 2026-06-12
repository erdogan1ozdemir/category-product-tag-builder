"""Streamlit facet onay ekranı.

Çalıştırma: streamlit run review/streamlit_app.py
Lokal kullanım için hesap gerekmez. Online paylaşım: Streamlit Community Cloud
(GitHub hesabıyla giriş + repo bağlama yeterli).
"""
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state import Workspace
from facets.pool_builder import pool_values

st.set_page_config(page_title="Facet Onay", layout="wide")
st.title("Facet Havuz Onayı")

root = "workspace"
brands = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))) \
    if os.path.isdir(root) else []
if not brands:
    st.warning("workspace/ altında marka bulunamadı. Önce 'python run.py collect' çalıştırın.")
    st.stop()

brand = st.sidebar.selectbox("Marka", brands)
ws = Workspace(brand)
pools_dir = ws.path("pools")
pool_files = sorted(f for f in os.listdir(pools_dir)
                    if f.endswith(".json") and not f.startswith("_")) \
    if os.path.isdir(pools_dir) else []
if not pool_files:
    st.warning("Bu marka için havuz yok. Önce 'pools' aşamasını çalıştırın.")
    st.stop()

pool_file = st.sidebar.selectbox("Kategori havuzu", pool_files)
pool = ws.read_json(f"pools/{pool_file}")
st.subheader(pool.get("arama_kelimesi", pool_file))
if pool.get("reviewed"):
    st.success("Bu havuz onaylanmış.")

edited = {}
for group, values in pool_values(pool).items():
    keep = st.multiselect(f"{group} ({len(values)} değer)", values, default=values, key=f"{pool_file}:{group}")
    if keep:
        edited[group] = keep

col1, col2 = st.columns(2)
if col1.button("Kaydet"):
    pool["gap_analizi"]["birlesik_filtre_havuzu"] = edited
    pool.pop("reviewed", None)  # içerik değişti — onay düşer, yeniden onay gerekir
    ws.write_json(f"pools/{pool_file}", pool)
    st.success("Kaydedildi.")
if col2.button("Kaydet ve Onayla"):
    pool["gap_analizi"]["birlesik_filtre_havuzu"] = edited
    pool["reviewed"] = True
    ws.write_json(f"pools/{pool_file}", pool)
    st.success("Onaylandı.")
