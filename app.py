import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost ERP v12.0", layout="wide")

# --- 1. FUNGSI PERSISTENSI DATA ---
def load_data(file_name, columns):
    if os.path.exists(file_name):
        try:
            df = pd.read_csv(file_name)
            for col in columns:
                if col not in df.columns: df[col] = 0
            return df
        except: return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def save_data(df, file_name):
    df.to_csv(file_name, index=False)

# --- 2. INISIALISASI DATABASE ---
# Tier 1: Raw Material (Bahan Baku)
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = load_data("database_bahan.csv", ["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"])

# Tier 2: WIP/Resep (Sambal, Bumbu, dll)
if 'db_menu' not in st.session_state:
    st.session_state.db_menu = load_data("master_resep.csv", ["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

# Tier 3: Finished Goods (Produk Jadi: Ikan + Sambal)
if 'db_fg' not in st.session_state:
    st.session_state.db_fg = load_data("master_fg.csv", ["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

# Tier 4: Master Paket
if 'db_master_paket' not in st.session_state:
    st.session_state.db_master_paket = load_data("master_paket.csv", ["nama_paket", "rincian_isi", "total_hpp", "total_kalori"])

# --- 3. SIDEBAR ---
st.sidebar.title("NutriCost ERP v12.0")
nav = st.sidebar.radio("Alur Produksi", [
    "📦 1. Database Bahan (RM)", 
    "🍳 2. Master Resep (WIP)", 
    "🍱 3. Finished Goods (FG)",
    "🛒 4. Set Menu (Paket)"
])

# --- HELPER: KALKULASI GIZI ---
def calc_nutrisi(qty, row, is_raw=True):
    if is_raw:
        gr = qty * float(row['berat'])
        f = (gr/100) * (float(row['bdd'])/100)
        return {
            'k': float(row['kalori'])*f, 'p': float(row['protein'])*f,
            'l': float(row['lemak'])*f, 'ka': float(row['karbo'])*f,
            'h': float(row['harga'])*qty, 'g': gr
        }
    else:
        # Untuk Resep/FG yang sudah porsian
        ratio = qty # Qty di sini dianggap porsi
        return {
            'k': float(row['kal_porsi'])*ratio, 'p': float(row['pro_porsi'])*ratio,
            'l': float(row['lem_porsi'])*ratio, 'ka': float(row['kar_porsi'])*ratio,
            'h': float(row['hpp_porsi'])*ratio, 'g': float(row['berat_porsi_gr'])*ratio
        }

# --- MODUL 3: FINISHED GOODS (HYBRID RM + WIP) ---
if nav == "🍱 3. Finished Goods (FG)":
    st.title("🏭 Finished Goods Production (RM + WIP)")
    st.info("Gabungkan Bahan Mentah (RM) dan Resep Setengah Jadi (WIP) menjadi Produk Jadi.")
    
    tab_fg1, tab_fg2 = st.tabs(["🆕 Buat FG Baru", "📋 Database FG"])
    
    with tab_buat := tab_fg1:
        if "fg_id" not in st.session_state: st.session_state.fg_id = 0
        nm_fg = st.text_input("Nama Produk Jadi (FG)", key=f"fg_nm_{st.session_state.fg_id}")
        
        c1, c2 = st.columns(2)
        rm_pilih = c1.multiselect("Pilih Bahan Baku (RM)", st.session_state.db_bahan['nama'].tolist(), key=f"fg_rm_{st.session_state.fg_id}")
        wip_pilih = c2.multiselect("Pilih Resep Setengah Jadi (WIP)", st.session_state.db_menu['nama'].tolist(), key=f"fg_wip_{st.session_state.fg_id}")
        
        if rm_pilih or wip_pilih:
            res_fg = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0}
            
            # Input untuk RM
            for rm in rm_pilih:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == rm].iloc[0]
                q = st.number_input(f"Qty RM: {rm} ({row['uom']})", min_value=0.0, key=f"qrm_{rm}_{st.session_state.fg_id}")
                d = calc_nutrisi(q, row, True)
                for k in res_fg: res_fg[k] += d[k]
                
            # Input untuk WIP
            for wip in wip_pilih:
                row = st.session_state.db_menu[st.session_state.db_menu['nama'] == wip].iloc[0]
                q = st.number_input(f"Berapa Porsi WIP: {wip}?", min_value=0.0, key=f"qwip_{wip}_{st.session_state.fg_id}")
                d = calc_nutrisi(q, row, False)
                for k in res_fg: res_fg[k] += d[k]
            
            st.divider()
            y_fg = st.number_input("Yield Berat FG (gr)", value=max(res_fg['g'], 1.0))
            if st.button("💾 Simpan Finished Good"):
                new_fg = pd.DataFrame([{"nama":nm_fg, "berat_porsi_gr":y_fg, "kal_porsi":res_fg['k'], "pro_porsi":res_fg['p'], "lem_porsi":res_fg['l'], "kar_porsi":res_fg['ka'], "hpp_porsi":res_fg['h']}])
                st.session_state.db_fg = pd.concat([st.session_state.db_fg, new_fg], ignore_index=True)
                save_data(st.session_state.db_fg, "master_fg.csv")
                st.session_state.fg_id += 1; st.rerun()

    with tab_fg2:
        st.data_editor(st.session_state.db_fg, use_container_width=True, num_rows="dynamic")

# --- MODUL 4: SET MENU (HYBRID RM + WIP + FG) ---
elif nav == "🛒 4. Set Menu (Paket)":
    st.title("🍱 Master Set Menu (Ultimate Aggregator)")
    st.info("Kombinasikan RM, WIP, dan FG menjadi Paket Penjualan.")
    
    if "pkt_id" not in st.session_state: st.session_state.pkt_id = 0
    nm_pkt = st.text_input("Nama Paket", key=f"pkt_nm_{st.session_state.pkt_id}")
    
    c1, c2, c3 = st.columns(3)
    p_rm = c1.multiselect("Tambah RM", st.session_state.db_bahan['nama'].tolist(), key=f"prm_{st.session_state.pkt_id}")
    p_wip = c2.multiselect("Tambah WIP", st.session_state.db_menu['nama'].tolist(), key=f"pwip_{st.session_state.pkt_id}")
    p_fg = c3.multiselect("Tambah FG", st.session_state.db_fg['nama'].tolist(), key=f"pfg_{st.session_state.pkt_id}")
    
    # Logika kalkulasi gabungan (RM + WIP + FG)
    # ... (Proses akumulasi mirip dengan Modul 3 namun mencakup 3 tier data)
    st.warning("Pilih item untuk melihat analisis gizi paket.")

# --- MODUL 4: MASTER PAKET ---
elif nav == "4. Master Paket (Set Menu)":
    st.title("🍱 Master Paket & Analisis Gizi")
    if "pkt_id" not in st.session_state: st.session_state.pkt_id = 0
    
    tab_a, tab_b = st.tabs(["🆕 Buat Paket", "🗄️ Database Paket"])
    
    with tab_a:
        if st.session_state.db_menu.empty:
            st.warning("Master Resep kosong. Selesaikan Modul 3 dulu.")
        else:
            if st.button("🧹 Clear Form Paket"):
                st.session_state.pkt_id += 1; st.rerun()
            
            c1, c2 = st.columns([2,1])
            nama_pkt = c1.text_input("Nama Paket", key=f"pnm_{st.session_state.pkt_id}")
            margin = c2.slider("Food Cost (%)", 10, 50, 30, key=f"pm_{st.session_state.pkt_id}")
            items_pkt = st.multiselect("Pilih Item", st.session_state.db_menu['nama'].tolist(), key=f"pit_{st.session_state.pkt_id}")

            if items_pkt:
                p_res = {'k':0,'p':0,'l':0,'ka':0,'h':0,'b':0,'isi':[]}
                detail_rows = []
                
                for itm in items_pkt:
                    d = st.session_state.db_menu[st.session_state.db_menu['nama'] == itm].iloc[0]
                    c_gr = st.number_input(f"Gramasi {itm} (gr)", value=float(d['berat_porsi_gr']), key=f"gr_{itm}_{st.session_state.pkt_id}")
                    ratio = c_gr / d['berat_porsi_gr'] if d['berat_porsi_gr'] > 0 else 0
                    
                    nk, np, nl, nka, nh = d['kal_porsi']*ratio, d['pro_porsi']*ratio, d['lem_porsi']*ratio, d['kar_porsi']*ratio, d['hpp_porsi']*ratio
                    detail_rows.append({"Menu": itm, "Gram": c_gr, "Kalori": round(nk,1), "Pro": round(np,1), "Lem": round(nl,1), "Kar": round(nka,1), "HPP": round(nh,0)})
                    
                    p_res['k']+=nk; p_res['p']+=np; p_res['l']+=nl; p_res['ka']+=nka; p_res['h']+=nh; p_res['b']+=c_gr
                    p_res['isi'].append(f"{itm}({c_gr}g)")

                st.table(pd.DataFrame(detail_rows))

                st.divider()
                m1, m2, m3 = st.columns([1,1,2])
                m1.metric("Total Kalori", f"{p_res['k']:,.1f}")
                m1.metric("Total HPP", f"Rp {p_res['h']:,.0f}")
                m2.metric("Saran Jual", f"Rp {p_res['h']/(margin/100):,.0f}")
                m2.metric("Total Berat", f"{p_res['b']:,.0f} g")
                
                with m3:
                    fig = px.pie(values=[p_res['p'], p_res['l'], p_res['ka']], names=['Protein','Lemak','Karbo'], title="Macro Ratio Paket", hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)

                if st.button("💾 Simpan Paket"):
                    new_p = pd.DataFrame([{"nama_paket":nama_pkt, "rincian_isi":", ".join(p_res['isi']), "total_hpp":p_res['h'], "total_kalori":p_res['k'], "pro_total":p_res['p'], "lem_total":p_res['l'], "kar_total":p_res['ka']}])
                    st.session_state.db_master_paket = pd.concat([st.session_state.db_master_paket, new_p], ignore_index=True)
                    save_data(st.session_state.db_master_paket, "master_paket.csv"); st.success("Paket Tersimpan!"); st.rerun()

    with tab_b:
        edited_pkt = st.data_editor(st.session_state.db_master_paket, use_container_width=True, num_rows="dynamic", key="edit_paket_v114")
        if st.button("💾 Simpan Perubahan Paket"):
            st.session_state.db_master_paket = edited_pkt
            save_data(st.session_state.db_master_paket, "master_paket.csv")
            st.success("Database paket diperbarui!")
