
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(layout="wide")

def apply_anomaly_detection(df):
    results = pd.DataFrame()
    results['IDPEL'] = df['LOCATION_CODE']

    results['v_drop'] = (
        ((df['VOLTAGE_L1'] < 56) & (df['CURRENT_L1'] > 0.5)) |
        ((df['VOLTAGE_L2'] < 56) & (df['CURRENT_L2'] > 0.5)) |
        ((df['VOLTAGE_L3'] < 56) & (df['CURRENT_L3'] > 0.5))
    )

    results['v_lost'] = (
        ((df['VOLTAGE_L1'] <= 0) & (df['CURRENT_L1'] > 0.5)) |
        ((df['VOLTAGE_L2'] <= 0) & (df['CURRENT_L2'] > 0.5)) |
        ((df['VOLTAGE_L3'] <= 0) & (df['CURRENT_L3'] > 0.5))
    )

    results['cos_phi_kecil'] = (
        ((df['POWER_FACTOR_L1'] <= 0.4) & (df['CURRENT_L1'] > 0.8)) |
        ((df['POWER_FACTOR_L2'] <= 0.4) & (df['CURRENT_L2'] > 0.8)) |
        ((df['POWER_FACTOR_L3'] <= 0.4) & (df['CURRENT_L3'] > 0.8))
    )

    results['arus_hilang'] = ((df['CURRENT_L1'] < 0.02) | (df['CURRENT_L2'] < 0.02) | (df['CURRENT_L3'] < 0.02)) & (
        df[['CURRENT_L1', 'CURRENT_L2', 'CURRENT_L3']].max(axis=1) > 0.5)

    results['in_more_Imax'] = (
        (df['CURRENT_N'] > 1) &
        (df['CURRENT_N'] > 1.3 * df[['CURRENT_L1', 'CURRENT_L2', 'CURRENT_L3']].max(axis=1))
    )

    results['over_current'] = df[['CURRENT_L1', 'CURRENT_L2', 'CURRENT_L3']].max(axis=1) > 5
    results['over_voltage'] = df[['VOLTAGE_L1', 'VOLTAGE_L2', 'VOLTAGE_L3']].max(axis=1) > 241

    results['reverse_power'] = (
        ((df['ACTIVE_POWER_L1'] < 0.1) & (df['CURRENT_L1'] > 0.5)) |
        ((df['ACTIVE_POWER_L2'] < 0.1) & (df['CURRENT_L2'] > 0.5)) |
        ((df['ACTIVE_POWER_L3'] < 0.1) & (df['CURRENT_L3'] > 0.5))
    )

    I_avg = (df['CURRENT_L1'] + df['CURRENT_L2'] + df['CURRENT_L3']) / 3
    results['unbalance_I'] = (
        ((abs(df['CURRENT_L1'] - I_avg) / I_avg > 0.5) & (df['CURRENT_L1'] > 0.5)) |
        ((abs(df['CURRENT_L2'] - I_avg) / I_avg > 0.5) & (df['CURRENT_L2'] > 0.5)) |
        ((abs(df['CURRENT_L3'] - I_avg) / I_avg > 0.5) & (df['CURRENT_L3'] > 0.5))
    )

    all_ap_0 = (df['ACTIVE_POWER_L1'] == 0) & (df['ACTIVE_POWER_L2'] == 0) & (df['ACTIVE_POWER_L3'] == 0)
    one_ap_0_i_high = (
        ((df['ACTIVE_POWER_L1'] == 0) & (df['CURRENT_L1'] > 0.5)) |
        ((df['ACTIVE_POWER_L2'] == 0) & (df['CURRENT_L2'] > 0.5)) |
        ((df['ACTIVE_POWER_L3'] == 0) & (df['CURRENT_L3'] > 0.5))
    )
    results['active_p_lost'] = one_ap_0_i_high & (~all_ap_0)

    indikator_cols = results.columns.drop(['IDPEL'])
    results['jml_indikator'] = results[indikator_cols].sum(axis=1)
    results['skor_total'] = results['jml_indikator']
    return results

def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Deteksi Anomali")
    return output.getvalue()

st.title("Dashboard Target Operasi P2TL AMR")

uploaded_file = st.file_uploader("📤 Upload File Excel Data AMR", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("File berhasil dimuat!")

    with st.expander("⚙️ Setting Threshold Parameter Anomali"):
        indikator_min = st.number_input("Jumlah Indikator Minimal", value=2)
        skor_min = st.number_input("Skor Minimal", value=2)
        top_n = st.number_input("Top N Ditampilkan", value=50)

    hasil = apply_anomaly_detection(df)
    hasil_full = pd.concat([df[['LOCATION_CODE', 'NAMAUP']], hasil], axis=1)
    hasil_filtered = hasil_full[
        (hasil_full['jml_indikator'] >= indikator_min) &
        (hasil_full['skor_total'] >= skor_min)
    ].sort_values(by="skor_total", ascending=False).head(top_n)

    st.subheader(f"Top {top_n} Rekomendasi Target Operasi")
    st.dataframe(hasil_filtered, use_container_width=True)

    excel_data = convert_df_to_excel(hasil_filtered)
    st.download_button("⬇️ Download Hasil ke Excel", data=excel_data, file_name="hasil_anomali.xlsx")
