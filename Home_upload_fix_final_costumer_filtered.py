### pages/1_AMR.py
import streamlit as st
import pandas as pd
import io
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

st.set_page_config(page_title="Modul AMR", layout="wide")
st.title("📊 Dashboard Target Operasi P2TL AMR Periode June 2025")

# Validasi apakah file telah diunggah
data_valid = False
if "uploaded_file" in st.session_state:
    uploaded_file = st.session_state.uploaded_file
    try:
        if uploaded_file.name.endswith("csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        data_valid = True
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
else:
    st.warning("Silakan upload data dari halaman utama terlebih dahulu.")

if data_valid:
    st.success("✅ Data berhasil dimuat dan valid.")

    # =============================
    # Bagian 1: Pengaturan Threshold
    # =============================
    with st.expander("⚙️ Setting Parameter", expanded=True):
        st.markdown("""
        Operasi Logika yang digunakan di sini adalah **OR**. Dengan demikian, indikator yang sesuai dengan salah satu spesifikasi aturan akan dihitung sebagai indikasi.
        """)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("### Tegangan & Arus")
            tm_vdrop = st.number_input("Batas Tegangan Menengah Drop", value=56.0)
            tr_vdrop = st.number_input("Batas Tegangan Rendah Drop", value=180.0)
            tm_ovolt = st.number_input("Tegangan Maksimum TM", value=62.0)
            tr_ovolt = st.number_input("Tegangan Maksimum TR", value=241.0)

        with col2:
            st.markdown("### Cos Phi & Power")
            tm_cosphi = st.number_input("Cos Phi TM Maks", value=0.4)
            tr_cosphi = st.number_input("Cos Phi TR Maks", value=0.4)
            arus_p_lost = st.number_input("Batas Arus Active Power Lost", value=0.5)

        with col3:
            st.markdown("### Parameter Tambahan")
            unbalance_tol = st.number_input("Batas Toleransi Unbalance", value=0.5)
            netral_vs_fasa = st.number_input("Arus Netral > Fasa (x%)", value=1.3)
            kl_terbalik = st.checkbox("Deteksi K-L Terbalik")
            imp_gt_exp = st.checkbox("Import > Export")
            v_lost_ada_arus = st.checkbox("Tegangan Hilang saat Ada Arus")

        thresholds = {
            "v_drop_tm": tm_vdrop,
            "v_drop_tr": tr_vdrop,
            "cos_phi_tm": tm_cosphi,
            "cos_phi_tr": tr_cosphi,
            "v_max_tm": tm_ovolt,
            "v_max_tr": tr_ovolt,
            "i_lost_min": arus_p_lost,
            "unbalance_tol": unbalance_tol,
            "netral_vs_fasa": netral_vs_fasa,
            "kl_terbalik": kl_terbalik,
            "imp_gt_exp": imp_gt_exp,
            "v_lost_ada_arus": v_lost_ada_arus,
        }

    # =============================
    # Bagian 2: Deteksi Anomali
    # =============================
    df_result = df.copy()

    df_result["v_drop"] = df_result["VOLTAGE_L1"].lt(thresholds["v_drop_tm"])
    df_result["cos_phi_kecil"] = df_result["COS_PHI"].lt(thresholds["cos_phi_tm"])
    df_result["over_voltage"] = df_result["VOLTAGE_L1"].gt(thresholds["v_max_tm"])
    df_result["active_p_lost"] = (df_result["ACTIVE_POWER"] == 0) & (df_result["CURRENT_L1"] > thresholds["i_lost_min"])

    df_result["unbalance_I"] = abs(df_result["CURRENT_L1"] - df_result[["CURRENT_L2", "CURRENT_L3"]].mean(axis=1)) >= thresholds["unbalance_tol"]
    df_result["in_more_Imax"] = df_result["CURRENT_N"] > (df_result[["CURRENT_L1", "CURRENT_L2", "CURRENT_L3"]].max(axis=1) * thresholds["netral_vs_fasa"])
    df_result["reverse_phase"] = thresholds["kl_terbalik"]
    df_result["import_gt_export"] = (df_result["KWH_IMP"] > df_result["KWH_EXP"]) if thresholds["imp_gt_exp"] else False
    df_result["v_lost_ada_arus"] = (df_result["VOLTAGE_L1"] == 0) & (df_result["CURRENT_L1"] > 0) if thresholds["v_lost_ada_arus"] else False

    indikator_cols = ["v_drop", "cos_phi_kecil", "over_voltage", "active_p_lost",
                      "unbalance_I", "in_more_Imax", "reverse_phase", "import_gt_export", "v_lost_ada_arus"]

    df_result["jumlah_potensi"] = df_result[indikator_cols].sum(axis=1)
    df_result["bobot"] = df_result["jumlah_potensi"] * 5

    # =============================
    # Bagian 3: Kriteria TO
    # =============================
    with st.expander("📋 Kriteria TO", expanded=True):
        st.markdown("""Untuk menentukan Target Operasi (TO), tentukan jumlah minimal indikator dan bobot.
        """)
        min_indikator = st.number_input("Jumlah Indikator ≥", min_value=1, value=2)
        min_bobot = st.number_input("Jumlah Bobot ≥", min_value=1, value=10)
        top_n = st.number_input("Banyak Data yang Ditampilkan", min_value=1, value=50)

    df_result["status_TO"] = (df_result["jumlah_potensi"] >= min_indikator) & (df_result["bobot"] >= min_bobot)

    # =============================
    # Bagian 4: Visualisasi Hasil
    # =============================
    st.markdown("### 📈 Top Rekomendasi Target Operasi Pelanggan AMR")
    top = df_result[df_result["status_TO"]].sort_values(by="bobot", ascending=False).head(top_n)

    def render_checkbox(val):
        return "✅" if val else ""  # Visualisasi centang

    top_display = top[["IDPEL", "NAMA", "TARIF", "DAYA"] + indikator_cols + ["jumlah_potensi", "bobot"]].copy()
    for col in indikator_cols:
        top_display[col] = top_display[col].apply(render_checkbox)

    st.dataframe(top_display, use_container_width=True)

    # =============================
    # Bagian 5: Ekspor ke Excel
    # =============================
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        top_display.to_excel(writer, index=False, sheet_name="TO_Analysis")
    st.download_button(
        label="📤 Download Hasil Analisis",
        data=output.getvalue(),
        file_name="hasil_analisis_to_amr.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )