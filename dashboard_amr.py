
import streamlit as st
import pandas as pd

# Fungsi logika teknis
def cek_indikator(row):
    indikator = {}

    indikator['arus_hilang'] = all([row['CURRENT_L1'] == 0, row['CURRENT_L2'] == 0, row['CURRENT_L3'] == 0])
    indikator['over_current'] = any([row['CURRENT_L1'] > 100, row['CURRENT_L2'] > 100, row['CURRENT_L3'] > 100])
    indikator['over_voltage'] = any([row['VOLTAGE_L1'] > 240, row['VOLTAGE_L2'] > 240, row['VOLTAGE_L3'] > 240])
    v = [row['VOLTAGE_L1'], row['VOLTAGE_L2'], row['VOLTAGE_L3']]
    indikator['v_drop'] = max(v) - min(v) > 10
    indikator['cos_phi_kecil'] = any([row.get(f'POWER_FACTOR_L{i}', 1) < 0.85 for i in range(1, 4)])
    indikator['active_power_negative'] = any([row.get(f'ACTIVE_POWER_L{i}', 0) < 0 for i in range(1, 4)])
    indikator['arus_kecil_teg_kecil'] = all([
        all([row['CURRENT_L1'] < 1, row['CURRENT_L2'] < 1, row['CURRENT_L3'] < 1]),
        all([row['VOLTAGE_L1'] < 180, row['VOLTAGE_L2'] < 180, row['VOLTAGE_L3'] < 180]),
        any([row.get(f'ACTIVE_POWER_L{i}', 0) > 10 for i in range(1, 4)])
    ])
    arus = [row['CURRENT_L1'], row['CURRENT_L2'], row['CURRENT_L3']]
    max_i, min_i = max(arus), min(arus)
    indikator['unbalance_I'] = (max_i - min_i) / max_i > 0.15 if max_i > 0 else False

    indikator['v_lost'] = row.get('VOLTAGE_L1', 0) == 0 or row.get('VOLTAGE_L2', 0) == 0 or row.get('VOLTAGE_L3', 0) == 0
    indikator['In_more_Imax'] = any([row['CURRENT_L1'] > 120, row['CURRENT_L2'] > 120, row['CURRENT_L3'] > 120])
    indikator['active_power_negative_siang'] = row.get('ACTIVE_POWER_SIANG', 0) < 0
    indikator['active_power_negative_malam'] = row.get('ACTIVE_POWER_MALAM', 0) < 0
    indikator['active_p_lost'] = row.get('ACTIVE_POWER_L1', 0) == 0 and row.get('ACTIVE_POWER_L2', 0) == 0 and row.get('ACTIVE_POWER_L3', 0) == 0
    indikator['current_loop'] = row.get('CURRENT_LOOP', 0) == 1
    indikator['freeze'] = row.get('FREEZE', 0) == 1

    return indikator

st.title("Dashboard Target Operasi AMR - P2TL")

uploaded_file = st.file_uploader("Upload File Excel AMR", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name=0)
    df = df.dropna(subset=['LOCATION_CODE'])
    df = df.copy()

    num_cols = [
        'CURRENT_L1', 'CURRENT_L2', 'CURRENT_L3',
        'VOLTAGE_L1', 'VOLTAGE_L2', 'VOLTAGE_L3',
        'ACTIVE_POWER_L1', 'ACTIVE_POWER_L2', 'ACTIVE_POWER_L3',
        'POWER_FACTOR_L1', 'POWER_FACTOR_L2', 'POWER_FACTOR_L3',
        'ACTIVE_POWER_SIANG', 'ACTIVE_POWER_MALAM', 'CURRENT_LOOP', 'FREEZE'
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    indikator_list = df.apply(cek_indikator, axis=1)
    indikator_df = pd.DataFrame(indikator_list.tolist())
    result = pd.concat([df[['LOCATION_CODE']], indikator_df], axis=1)

    result['Jumlah Potensi TO'] = indikator_df.sum(axis=1)
    top50 = result.sort_values(by='Jumlah Potensi TO', ascending=False).head(50)

    st.metric("Total Data Berhasil di Analisis", len(df))
    st.metric("Total IDPEL di Analisis", df['LOCATION_CODE'].nunique())
    st.metric("Target Operasi Memenuhi Kriteria", sum(result['Jumlah Potensi TO'] > 0))

    st.subheader("Top 50 Rekomendasi Target Operasi")
    st.dataframe(top50, use_container_width=True)
else:
    st.info("Silakan upload file Excel terlebih dahulu.")
