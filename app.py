import streamlit as st
import pandas as pd
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v11.1", layout="wide")

# --- 1. FUNGSI PENYIMPANAN PERSISTEN (LOCAL STORAGE) ---
def load_data(file_name, columns):
    if os.path.exists(file_name):
        return pd.read_csv(file_name)
    return pd.DataFrame(columns=columns)

def save_data(df, file_name):
    df.to_csv(file_name, index=False)

# --- 2. INISIALISASI DATABASE ---
# Data Bahan Baku
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = load_data("database_bahan.csv", ["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"])

# Master Resep (Menu Tunggal)
if 'db_menu' not in st.session_state:
    st.session_state.db_menu = load_data("master_resep.csv", ["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

# Master Paket (Set Menu)
if 'db_master_paket' not in st.session_state:
    st.session_state.db_master_paket = load_data("master_paket.csv", ["nama_paket", "rincian_isi", "total_hpp", "total_kalori"])

# --- 3. SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Control v11.1")
nav = st.sidebar.radio("Navigasi", ["1. Database Bahan", "2. Upload Data", "3. Master Resep", "4. Master Paket"])

# --- MODUL 1: DATABASE BAHAN ---
if nav == "1. Database Bahan":
    st.title("📂 Database Bahan Baku")
    search = st.text_input("🔍 Cari Nama Bahan...")
    df_disp = st.session_state.db_bahan
    if search: df_disp = df_disp[df_disp['nama'].str.contains(search, case=False)]
    
    edited_df = st.data_editor(df_disp, use_container_width=True, num_rows="dynamic", key="editor_bahan")
    if st.button("💾 Simpan Perubahan Bahan"):
        st.session_state.db_bahan = edited_df.fillna(0)
        save_data(st.session_state.db_bahan, "database_bahan.csv")
        st.success("Database bahan berhasil disimpan ke lokal!")

# --- MODUL 3: MASTER RESEP ---
elif nav == "3. Master Resep":
    st.title("🍳 Recipe Builder & Master Resep")
    tab1, tab2 = st.tabs(["📝 Buat Resep Baru", "📋 Database Master Resep"])
    
    with tab1:
        if st.session_state.db_bahan.empty:
            st.warning("Silakan isi database bahan terlebih dahulu.")
        else:
            if "form_id" not in st.session_state: st.session_state.form_id = 0
            
            nama_resep = st.text_input("Nama Produk", key=f"n_{st.session_state.form_id}")
            items_pilih = st.multiselect("Pilih Komponen", st.session_state.db_bahan['nama'].tolist(), key=f"i_{st.session_state.form_id}")
            
            if items_pilih:
                res_calc = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0, 'total_gr': 0.0}
                for itm in items_pilih:
                    row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == itm].iloc[0]
                    qty = st.number_input(f"Qty {itm} ({row['uom']})", min_value=0.0, step=0.01, key=f"q_{itm}_{st.session_state.form_id}")
                    
                    # Logika Gizi Precision (v11.0)
                    gr_mentah = qty * float(row['berat'])
                    factor = (gr_mentah / 100) * (float(row['bdd']) / 100)
                    
                    res_calc['kal'] += float(row['kalori']) * factor
                    res_calc['pro'] += float(row['protein']) * factor
                    res_calc['lem'] += float(row['lemak']) * factor
                    res_calc['kar'] += float(row['karbo']) * factor
                    res_calc['cost'] += float(row['harga']) * qty
                    res_calc['total_gr'] += gr_mentah
                
                st.divider()
                berat_matang = st.number_input("Berat Yield Matang", min_value=0.1, value=max(res_calc['total_gr'], 1.0))
                jml_porsi = st.number_input("Jumlah Porsi", min_value=1, value=1)
                
                if st.button("💾 SIMPAN KE MASTER RESEP"):
                    new_entry = pd.DataFrame([{
                        "nama": nama_resep, "berat_porsi_gr": berat_matang/jml_porsi,
                        "kal_porsi": res_calc['kal']/jml_porsi, "pro_porsi": res_calc['pro']/jml_porsi,
                        "lem_porsi": res_calc['lem']/jml_porsi, "kar_porsi": res_calc['kar']/jml_porsi,
                        "hpp_porsi": res_calc['cost']/jml_porsi
                    }])
                    st.session_state.db_menu = pd.concat([st.session_state.db_menu, new_entry], ignore_index=True)
                    save_data(st.session_state.db_menu, "master_resep.csv")
                    st.session_state.form_id += 1 # Reset form
                    st.success("Resep tersimpan permanen di master_resep.csv!"); st.rerun()

    with tab2:
        edited_menu = st.data_editor(st.session_state.db_menu, use_container_width=True, num_rows="dynamic", key="edit_master_resep")
        if st.button("💾 Update Database Master Resep"):
            st.session_state.db_menu = edited_menu
            save_data(st.session_state.db_menu, "master_resep.csv")
            st.success("Master Resep diperbarui!")

# --- MODUL 4: MASTER PAKET ---
elif nav == "4. Master Paket":
    st.title("🍱 Master Set Menu & Paket")
    tab_a, tab_b = st.tabs(["🆕 Buat Paket", "🗄️ Database Paket"])
    
    with tab_a:
        if st.session_state.db_menu.empty:
            st.warning("Belum ada Master Resep.")
        else:
            nama_pkt = st.text_input("Nama Paket")
            items = st.multiselect("Pilih Menu", st.session_state.db_menu['nama'].tolist())
            
            if items:
                p_tot = {'k':0, 'h':0, 'b':0, 'isi':[]}
                for itm in items:
                    d = st.session_state.db_menu[st.session_state.db_menu['nama'] == itm].iloc[0]
                    custom_gr = st.number_input(f"Gramasi {itm} dalam paket", value=float(d['berat_porsi_gr']), key=f"p_{itm}")
                    ratio = custom_gr / d['berat_porsi_gr']
                    p_tot['k'] += d['kal_porsi'] * ratio
                    p_tot['h'] += d['hpp_porsi'] * ratio
                    p_tot['isi'].append(f"{itm}({custom_gr}g)")
                
                if st.button("💾 SIMPAN KE MASTER PAKET"):
                    new_pkt = pd.DataFrame([{
                        "nama_paket": nama_pkt, "rincian_isi": ", ".join(p_tot['isi']),
                        "total_hpp": p_tot['h'], "total_kalori": p_tot['k']
                    }])
                    st.session_state.db_master_paket = pd.concat([st.session_state.db_master_paket, new_pkt], ignore_index=True)
                    save_data(st.session_state.db_master_paket, "master_paket.csv")
                    st.success("Paket tersimpan permanen di master_paket.csv!"); st.rerun()

    with tab_b:
        edited_pkt = st.data_editor(st.session_state.db_master_paket, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Update Database Master Paket"):
            st.session_state.db_master_paket = edited_pkt
            save_data(st.session_state.db_master_paket, "master_paket.csv")
            st.success("Master Paket diperbarui!")
