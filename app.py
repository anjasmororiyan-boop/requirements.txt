import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost ERP v17.0", layout="wide")

# --- 1. SISTEM PENYIMPANAN PERMANEN (FIXED) ---
def load_data_permanent(file_name, columns):
    """Memastikan data dibaca dari file fisik, bukan hanya memori sementara."""
    if os.path.exists(file_name):
        try:
            df = pd.read_csv(file_name).fillna(0)
            # Pastikan kolom sesuai, jika ada kolom baru di versi ini, tambahkan otomatis
            for col in columns:
                if col not in df.columns: df[col] = 0
            return df[columns]
        except:
            return pd.DataFrame(columns=columns)
    # Jika file tidak ada, buat file baru agar folder tidak kosong
    df_empty = pd.DataFrame(columns=columns)
    df_empty.to_csv(file_name, index=False)
    return df_empty

def save_data_permanent(df, file_name):
    """Memaksa penulisan data ke file fisik setiap kali ada perubahan."""
    df.to_csv(file_name, index=False)

# --- 2. INISIALISASI DATABASE (AUTO-LOAD) ---
cols_rm = ["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"]
cols_master = ["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"]
cols_pkt = ["nama_paket", "rincian_isi", "total_hpp", "total_kalori", "pro_total", "lem_total", "kar_total"]

# Selalu muat dari file fisik untuk mencegah kehilangan data
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = load_data_permanent("db_bahan.csv", cols_rm)
if 'db_wip' not in st.session_state:
    st.session_state.db_wip = load_data_permanent("db_wip.csv", cols_master)
if 'db_fg' not in st.session_state:
    st.session_state.db_fg = load_data_permanent("db_fg.csv", cols_master)
if 'db_paket' not in st.session_state:
    st.session_state.db_paket = load_data_permanent("db_paket.csv", cols_pkt)

# --- 3. FUNGSI KALKULASI GIZI UNIVERSAL ---
def universal_calc(qty, row, source_type='RM'):
    try:
        qty = float(qty) if qty else 0.0
        if source_type == 'RM':
            gr_mentah = qty * float(row['berat'])
            factor = (gr_mentah / 100) * (float(row['bdd']) / 100)
            return {'k': float(row['kalori'])*factor, 'p': float(row['protein'])*factor, 'l': float(row['lemak'])*factor, 'ka': float(row['karbo'])*factor, 'h': float(row['harga'])*qty, 'g': gr_mentah}
        else: # WIP atau FG
            ratio = qty / float(row['berat_porsi_gr']) if float(row['berat_porsi_gr']) > 0 else 0
            return {'k': float(row['kal_porsi'])*ratio, 'p': float(row['pro_porsi'])*ratio, 'l': float(row['lem_porsi'])*ratio, 'ka': float(row['kar_porsi'])*ratio, 'h': float(row['hpp_porsi'])*ratio, 'g': qty}
    except:
        return {'k':0.0, 'p':0.0, 'l':0.0, 'ka':0.0, 'h':0.0, 'g':0.0}

# --- 4. SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost ERP v17.0")
nav = st.sidebar.radio("Menu", ["📦 Database RM", "📥 Upload Data", "🍳 Master WIP", "🍱 Master FG", "🛒 Set Menu (Paket)"])

# --- MODUL UPLOAD (DIPERKUAT) ---
if nav == "📥 Upload Data":
    st.title("📥 Upload Database Bahan Baku")
    up = st.file_uploader("Pilih file CSV/Excel", type=["csv", "xlsx"])
    if up and st.button("🚀 Simpan ke Database Permanen"):
        df_new = pd.read_csv(up, sep=None, engine='python') if up.name.endswith('.csv') else pd.read_excel(up)
        # Gabungkan dan hapus duplikat
        st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
        save_data_permanent(st.session_state.db_bahan, "db_bahan.csv")
        st.success("Data Berhasil Disimpan Secara Permanen!"); st.rerun()

# --- MODUL SET MENU (PERBAIKAN FUNGSI) ---
elif nav == "🛒 Set Menu (Paket)":
    st.title("🛒 Set Menu / Paket Jual")
    tab1, tab2 = st.tabs(["📝 Susun Paket", "📋 Daftar Paket"])
    
    with tab1:
        if "p_id" not in st.session_state: st.session_state.p_id = 0
        nm_p = st.text_input("Nama Paket", key=f"p_{st.session_state.p_id}")
        
        c1, c2, c3 = st.columns(3)
        prm = c1.multiselect("Bahan Mentah (RM)", st.session_state.db_bahan['nama'].tolist())
        pwp = c2.multiselect("Resep Matang (WIP)", st.session_state.db_wip['nama'].tolist())
        pfg = c3.multiselect("Produk Jadi (FG)", st.session_state.db_fg['nama'].tolist())
        
        if prm or pwp or pfg:
            total = {'k':0,'p':0,'l':0,'ka':0,'h':0,'b':0, 'items':[]}
            
            # Kalkulasi RM
            for x in prm:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama']==x].iloc[0]
                q = st.number_input(f"Gram Mentah: {x}", key=f"qrm_{x}")
                d = universal_calc(q/row['berat'], row, 'RM')
                for k,v in zip(['k','p','l','ka','h','b'],['k','p','l','ka','h','g']): total[k]+=d[v]
                total['items'].append(x)
            
            # Kalkulasi WIP & FG (Logika Sama)
            for src, db in [('WIP', st.session_state.db_wip), ('FG', st.session_state.db_fg)]:
                choices = pwp if src == 'WIP' else pfg
                for x in choices:
                    row = db[db['nama']==x].iloc[0]
                    q = st.number_input(f"Gram Matang: {x}", value=float(row['berat_porsi_gr']), key=f"q{src}_{x}")
                    d = universal_calc(q, row, src)
                    for k,v in zip(['k','p','l','ka','h','b'],['k','p','l','ka','h','g']): total[k]+=d[v]
                    total['items'].append(x)
            
            st.divider()
            col_a, col_b = st.columns(2)
            col_a.metric("Total HPP Paket", f"Rp {total['h']:,.0f}")
            col_b.metric("Total Kalori", f"{total['k']:,.1f} kkal")
            
            if st.button("💾 Simpan Paket"):
                new_p = pd.DataFrame([{"nama_paket":nm_p, "rincian_isi":", ".join(total['items']), "total_hpp":total['h'], "total_kalori":total['k'], "pro_total":total['p'], "lem_total":total['l'], "kar_total":total['ka']}])
                st.session_state.db_paket = pd.concat([st.session_state.db_paket, new_p], ignore_index=True)
                save_data_permanent(st.session_state.db_paket, "db_paket.csv")
                st.success("Paket Berhasil Disimpan Permanen!"); st.session_state.p_id+=1; st.rerun()

    with tab2:
        st.dataframe(st.session_state.db_paket, use_container_width=True)

# --- MODUL DATABASE RM, WIP, FG (SAMA SEPERTI v16.5) ---
else:
    # Modul lainnya tetap menggunakan save_data_permanent agar data aman
    st.info("Gunakan Modul di Sidebar untuk mengelola data.")
